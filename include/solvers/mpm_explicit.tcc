//! Constructor
template <unsigned Tdim>
mpm::MPMExplicit<Tdim>::MPMExplicit(const std::shared_ptr<IO>& io)
    : mpm::MPMBase<Tdim>(io) {
  //! Logger
  console_ = spdlog::get("MPMExplicit");
  //! Stress update
  if (this->stress_update_ == "usl")
    mpm_scheme_ = std::make_shared<mpm::MPMSchemeUSL<Tdim>>(mesh_, dt_);
  else
    mpm_scheme_ = std::make_shared<mpm::MPMSchemeUSF<Tdim>>(mesh_, dt_);

  //! Interface scheme
  if (this->interface_)
    contact_ = std::make_shared<mpm::ContactFriction<Tdim>>(mesh_);
  else
    contact_ = std::make_shared<mpm::Contact<Tdim>>(mesh_);
}

//! MPM Explicit compute stress strain
template <unsigned Tdim>
void mpm::MPMExplicit<Tdim>::compute_stress_strain(unsigned phase) {
  // Iterate over each particle to calculate strain
  mesh_->iterate_over_particles(std::bind(
      &mpm::ParticleBase<Tdim>::compute_strain, std::placeholders::_1, dt_));

  // Iterate over each particle to update particle volume
  mesh_->iterate_over_particles(std::bind(
      &mpm::ParticleBase<Tdim>::update_volume, std::placeholders::_1));

  // Pressure smoothing
  if (pressure_smoothing_) this->pressure_smoothing(phase);

  // Iterate over each particle to compute stress
  mesh_->iterate_over_particles(std::bind(
      &mpm::ParticleBase<Tdim>::compute_stress, std::placeholders::_1));
}

//! MPM Explicit solver
template <unsigned Tdim>
bool mpm::MPMExplicit<Tdim>::solve() {
  bool status = true;

  console_->info("MPM analysis type {}", io_->analysis_type());

  // Initialise MPI rank and size
  int mpi_rank = 0;
  int mpi_size = 1;

#ifdef USE_MPI
  // Get MPI rank
  MPI_Comm_rank(MPI_COMM_WORLD, &mpi_rank);
  // Get number of MPI ranks
  MPI_Comm_size(MPI_COMM_WORLD, &mpi_size);
#endif

  // Phase
  const unsigned phase = 0;

  // Test if checkpoint resume is needed
  bool resume = false;
  if (analysis_.find("resume") != analysis_.end())
    resume = analysis_["resume"]["resume"].template get<bool>();

  // Enable repartitioning if resume is done with particles generated outside
  // the MPM code.
  bool repartition = false;
  if (analysis_.find("resume") != analysis_.end() &&
      analysis_["resume"].find("repartition") != analysis_["resume"].end())
    repartition = analysis_["resume"]["repartition"].template get<bool>();

  // Pressure smoothing
  pressure_smoothing_ = io_->analysis_bool("pressure_smoothing");

  // Interface
  interface_ = io_->analysis_bool("interface");

  // Initialise material
  this->initialise_materials();

  // Initialise mesh
  this->initialise_mesh();

  // Initialise particles
  if (!resume) this->initialise_particles();

  // Create nodal properties
  if (interface_) mesh_->create_nodal_properties();

  // Compute mass
  if (!resume)
    mesh_->iterate_over_particles(std::bind(
        &mpm::ParticleBase<Tdim>::compute_mass, std::placeholders::_1));

  bool initial_step = (resume == true) ? false : true;
  // Check point resume
  if (resume) {
    this->checkpoint_resume();
    if (repartition) {
      this->mpi_domain_decompose(initial_step);
    } else {
      mesh_->resume_domain_cell_ranks();
#ifdef USE_MPI
#ifdef USE_GRAPH_PARTITIONING
      MPI_Barrier(MPI_COMM_WORLD);
#endif
#endif
    }
  } else {
    // Domain decompose
    this->mpi_domain_decompose(initial_step);
  }

  //! Particle entity sets and velocity constraints
  if (resume) {
    this->particle_entity_sets(false);
    this->particle_velocity_constraints();
  }

  // Initialise loading conditions
  this->initialise_loads();

  auto solver_begin = std::chrono::steady_clock::now();
  // Main loop
  for (; step_ < nsteps_; ++step_) {

    if (mpi_rank == 0) console_->info("Step: {} of {}.\n", step_, nsteps_);

#ifdef USE_MPI
#ifdef USE_GRAPH_PARTITIONING
    // Run load balancer at a specified frequency
    if (step_ % nload_balance_steps_ == 0 && step_ != 0)
      this->mpi_domain_decompose(false);
#endif
#endif

    // Inject particles
    mesh_->inject_particles(step_ * dt_);

    // Initialise nodes, cells and shape functions
    mpm_scheme_->initialise();

    // Initialise nodal properties and append material ids to node
    contact_->initialise();

    // Mass momentum and compute velocity at nodes
    mpm_scheme_->compute_nodal_kinematics(phase);

    // Map material properties to nodes
    contact_->compute_contact_forces();

    // Compute bearing capacity from contact forces (if interface mode enabled)
    if (interface_ && mpi_rank == 0) {
      double bearing_capacity = 0.0;
      double settlement = 0.0;
      unsigned contact_nodes = 0;

      // Get nodal properties handle from mesh
      auto nodal_properties = mesh_->nodal_properties();

      if (nodal_properties != nullptr) {
        // Iterate over all nodes to find interface nodes
        auto nodes = mesh_->nodes(-1);  // -1 = all nodes
        for (const auto& node : nodes) {
          // Get material IDs at this node
          auto material_ids = node->material_ids();

          // Check if node has both soil (material_id=0) and foundation (material_id=1)
          if (material_ids.size() >= 2 &&
              material_ids.find(0) != material_ids.end() &&
              material_ids.find(1) != material_ids.end()) {

            contact_nodes++;

            // Get node ID and property ID
            auto node_id = node->id();

            // For 2D: Tdim=2, vertical direction is index 1 (y-direction)
            // For 3D: Tdim=3, vertical direction is index 2 (z-direction)
            const unsigned vertical_dir = (Tdim == 2) ? 1 : 2;

            // Get change_in_momenta for both materials at this node
            // Material 0 (soil) - we want the reaction from soil onto foundation
            auto delta_p_soil = nodal_properties->property("change_in_momenta",
                                                            node_id, 0, Tdim);

            // Extract vertical component and convert impulse to force
            // Force = impulse / dt
            double force_from_soil = delta_p_soil(vertical_dir, 0) / dt_;

            // Accumulate bearing capacity (absolute value, upward reaction)
            bearing_capacity += std::abs(force_from_soil);

            // Calculate average settlement from nodal displacements
            auto displacement = nodal_properties->property("displacements",
                                                            node_id, 1, Tdim);
            settlement += std::abs(displacement(vertical_dir, 0));
          }
        }

        // Calculate average settlement
        if (contact_nodes > 0) {
          settlement /= contact_nodes;
        }

        // Print bearing capacity and settlement
        console_->info("Step: {}, Time: {:.6f}s, Contact nodes: {}, "
                       "Bearing capacity: {:.2f} kN/m, Settlement: {:.6f} m",
                       step_, step_ * dt_, contact_nodes,
                       bearing_capacity / 1000.0,  // Convert N to kN
                       settlement);

        // Optional: Write to CSV file for post-processing
        if (step_ == 0) {
          std::ofstream bc_file("bearing_capacity.csv");
          bc_file << "step,time,settlement,bearing_capacity,contact_nodes\n";
          bc_file.close();
        }
        std::ofstream bc_file("bearing_capacity.csv", std::ios::app);
        bc_file << step_ << "," << step_ * dt_ << "," << settlement << ","
                << bearing_capacity / 1000.0 << "," << contact_nodes << "\n";
        bc_file.close();
      }
    }

    // Update stress first
    mpm_scheme_->precompute_stress_strain(phase, pressure_smoothing_);

    // Compute forces
    mpm_scheme_->compute_forces(gravity_, phase, step_,
                                set_node_concentrated_force_);

    // Particle kinematics
    mpm_scheme_->compute_particle_kinematics(velocity_update_, phase, "Cundall",
                                             damping_factor_);

    // Update Stress Last
    mpm_scheme_->postcompute_stress_strain(phase, pressure_smoothing_);

    // Locate particles
    mpm_scheme_->locate_particles(this->locate_particles_);

#ifdef USE_MPI
#ifdef USE_GRAPH_PARTITIONING
    mesh_->transfer_halo_particles();
    MPI_Barrier(MPI_COMM_WORLD);
#endif
#endif

    if (step_ % output_steps_ == 0) {
      // HDF5 outputs
      this->write_hdf5(this->step_, this->nsteps_);
#ifdef USE_VTK
      // VTK outputs
      this->write_vtk(this->step_, this->nsteps_);
#endif
#ifdef USE_PARTIO
      // Partio outputs
      this->write_partio(this->step_, this->nsteps_);
#endif
    }
  }
  auto solver_end = std::chrono::steady_clock::now();
  console_->info("Rank {}, Explicit {} solver duration: {} ms", mpi_rank,
                 mpm_scheme_->scheme(),
                 std::chrono::duration_cast<std::chrono::milliseconds>(
                     solver_end - solver_begin)
                     .count());

  return status;
}
