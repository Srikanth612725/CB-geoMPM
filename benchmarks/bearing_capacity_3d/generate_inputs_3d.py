#!/usr/bin/env python3
"""
Generate 3D mesh and particles for A-shaped mat foundation bearing capacity test

Based on Liu et al. (2022):
- Foundation: 7.2m × 8.0m A-shaped mat
- Soil: Undrained clay, su = 6 kPa  
- Expected bearing capacity: 2522 kN total
"""


# ============================================================================
# Domain Parameters
# ============================================================================
# Domain size (larger than 2D for 3D effects)
domain_length = 30.0  # x-direction (m)
domain_width = 30.0   # y-direction (m)
domain_height = 20.0  # z-direction (m)

# Grid resolution
dx = 0.5  # Cell size in x (m)
dy = 0.5  # Cell size in y (m)
dz = 0.5  # Cell size in z (m)

nx_cells = int(domain_length / dx)
ny_cells = int(domain_width / dy)
nz_cells = int(domain_height / dz)

# Particles per cell (2x2x2 = 8 particles per cell in 3D)
particles_per_cell = 8

print("Domain: {:.1f}m × {:.1f}m × {:.1f}m".format(domain_length, domain_width, domain_height))
print("Grid: {} × {} × {} cells".format(nx_cells, ny_cells, nz_cells))
print("Cell size: {:.2f}m × {:.2f}m × {:.2f}m".format(dx, dy, dz))
print("Particles per cell: {}".format(particles_per_cell))

# ============================================================================
# Foundation Parameters (A-shaped mat)
# ============================================================================
foundation_length = 7.2  # x-direction (m)
foundation_width = 8.0   # y-direction (m)
foundation_thickness = 0.5  # z-direction (m)

# Center foundation in domain
foundation_center_x = domain_length / 2.0
foundation_center_y = domain_width / 2.0

# Soil height (foundation sits on top)
soil_height = 15.0  # m
foundation_z_bottom = soil_height
foundation_z_top = soil_height + foundation_thickness

print("\nFoundation:")
print("  - Dimensions: {:.1f}m × {:.1f}m × {:.1f}m".format(
    foundation_length, foundation_width, foundation_thickness))
print("  - Center: x={:.1f}m, y={:.1f}m".format(foundation_center_x, foundation_center_y))
print("  - Z range: {:.1f} - {:.1f}m".format(foundation_z_bottom, foundation_z_top))

# ============================================================================
# 1. Generate 3D Mesh (Hexahedral cells)
# ============================================================================
print("\nGenerating 3D mesh...")

nodes = []
node_id = 0

# Generate nodes
nx_nodes = nx_cells + 1
ny_nodes = ny_cells + 1
nz_nodes = nz_cells + 1

for k in range(nz_nodes):
    for j in range(ny_nodes):
        for i in range(nx_nodes):
            x = i * dx
            y = j * dy
            z = k * dz
            nodes.append([node_id, x, y, z])
            node_id += 1

nnodes = len(nodes)
print("Generated {} nodes".format(nnodes))

# Generate cells (hexahedra)
cells = []
cell_id = 0

for k in range(nz_cells):
    for j in range(ny_cells):
        for i in range(nx_cells):
            # Node IDs for hexahedron (ED3H8)
            # Bottom face (z=k)
            n0 = k * nx_nodes * ny_nodes + j * nx_nodes + i
            n1 = k * nx_nodes * ny_nodes + j * nx_nodes + (i + 1)
            n2 = k * nx_nodes * ny_nodes + (j + 1) * nx_nodes + (i + 1)
            n3 = k * nx_nodes * ny_nodes + (j + 1) * nx_nodes + i
            # Top face (z=k+1)
            n4 = (k + 1) * nx_nodes * ny_nodes + j * nx_nodes + i
            n5 = (k + 1) * nx_nodes * ny_nodes + j * nx_nodes + (i + 1)
            n6 = (k + 1) * nx_nodes * ny_nodes + (j + 1) * nx_nodes + (i + 1)
            n7 = (k + 1) * nx_nodes * ny_nodes + (j + 1) * nx_nodes + i
            
            cells.append([n0, n1, n2, n3, n4, n5, n6, n7])
            cell_id += 1

ncells = len(cells)
print("Generated {} cells".format(ncells))

# Write mesh file (3D format)
mesh_file = "mesh-3d.txt"
with open(mesh_file, 'w') as f:
    # Header: nnodes ncells
    f.write("{} {}\n".format(nnodes, ncells))
    
    # Nodes: x y z (no IDs in 3D format)
    for node in nodes:
        f.write("{:.6f} {:.6f} {:.6f}\n".format(node[1], node[2], node[3]))
    
    # Cells: node_ids (8 nodes for hexahedron)
    for cell in cells:
        f.write("{} {} {} {} {} {} {} {}\n".format(
            cell[0], cell[1], cell[2], cell[3],
            cell[4], cell[5], cell[6], cell[7]))

print("Wrote mesh to {}".format(mesh_file))

# ============================================================================
# 2. Generate Soil Particles
# ============================================================================
print("\nGenerating soil particles...")

soil_particles = []
particle_id = 0

# Particle offsets within cell (2x2x2 grid)
px_offset = dx / 4.0
py_offset = dy / 4.0
pz_offset = dz / 4.0

for k in range(nz_cells):
    for j in range(ny_cells):
        for i in range(nx_cells):
            cell_center_x = (i + 0.5) * dx
            cell_center_y = (j + 0.5) * dy
            cell_center_z = (k + 0.5) * dz
            
            # Check if cell is in soil region (z < soil_height)
            if cell_center_z < soil_height:
                # Generate 8 particles in this cell (2x2x2)
                for pz_idx in range(2):
                    for py_idx in range(2):
                        for px_idx in range(2):
                            px = cell_center_x - px_offset + px_idx * 2 * px_offset
                            py = cell_center_y - py_offset + py_idx * 2 * py_offset
                            pz = cell_center_z - pz_offset + pz_idx * 2 * pz_offset
                            soil_particles.append([particle_id, px, py, pz])
                            particle_id += 1

nsoil = len(soil_particles)
print("Generated {} soil particles".format(nsoil))

# Write soil particles file (3D format: x y z)
soil_file = "particles-soil.txt"
with open(soil_file, 'w') as f:
    f.write("{}\n".format(nsoil))
    for p in soil_particles:
        f.write("{:.6f} {:.6f} {:.6f}\n".format(p[1], p[2], p[3]))

print("Wrote soil particles to {}".format(soil_file))

# ============================================================================
# 3. Generate Foundation Particles (A-shaped mat)
# ============================================================================
print("\nGenerating foundation particles...")

foundation_particles = []
foundation_particle_id = 0

foundation_xmin = foundation_center_x - foundation_length / 2.0
foundation_xmax = foundation_center_x + foundation_length / 2.0
foundation_ymin = foundation_center_y - foundation_width / 2.0
foundation_ymax = foundation_center_y + foundation_width / 2.0

for k in range(nz_cells):
    for j in range(ny_cells):
        for i in range(nx_cells):
            cell_center_x = (i + 0.5) * dx
            cell_center_y = (j + 0.5) * dy
            cell_center_z = (k + 0.5) * dz
            
            # Check if cell is in foundation region
            if (foundation_xmin <= cell_center_x <= foundation_xmax and
                foundation_ymin <= cell_center_y <= foundation_ymax and
                foundation_z_bottom <= cell_center_z <= foundation_z_top):
                
                # Generate 8 particles in this cell
                for pz_idx in range(2):
                    for py_idx in range(2):
                        for px_idx in range(2):
                            px = cell_center_x - px_offset + px_idx * 2 * px_offset
                            py = cell_center_y - py_offset + py_idx * 2 * py_offset
                            pz = cell_center_z - pz_offset + pz_idx * 2 * pz_offset
                            foundation_particles.append([foundation_particle_id, px, py, pz])
                            foundation_particle_id += 1

nfoundation = len(foundation_particles)
print("Generated {} foundation particles".format(nfoundation))

# Write foundation particles file
foundation_file = "particles-foundation.txt"
with open(foundation_file, 'w') as f:
    f.write("{}\n".format(nfoundation))
    for p in foundation_particles:
        f.write("{:.6f} {:.6f} {:.6f}\n".format(p[1], p[2], p[3]))

print("Wrote foundation particles to {}".format(foundation_file))

# ============================================================================
# Summary
# ============================================================================
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print("Mesh:")
print("  - Nodes: {}".format(nnodes))
print("  - Cells: {}".format(ncells))
print("  - Domain: {:.1f}m × {:.1f}m × {:.1f}m".format(domain_length, domain_width, domain_height))
print("  - Cell size: {:.2f}m × {:.2f}m × {:.2f}m".format(dx, dy, dz))

print("\nParticles:")
print("  - Soil (material_id=0): {}".format(nsoil))
print("  - Foundation (material_id=1): {}".format(nfoundation))
print("  - Total: {}".format(nsoil + nfoundation))

print("\nFoundation:")
print("  - Dimensions: {:.1f}m × {:.1f}m × {:.1f}m".format(
    foundation_length, foundation_width, foundation_thickness))
print("  - Area: {:.1f} m²".format(foundation_length * foundation_width))

print("\nExpected bearing capacity (Liu et al. 2022):")
print("  - Undrained shear strength: su = 6.0 kPa")
print("  - Bearing capacity factor: Nc = 5.14")
print("  - Ultimate bearing pressure: qu = 30.8 kPa")
print("  - Foundation area: {:.1f} m²".format(foundation_length * foundation_width))
print("  - Ultimate bearing capacity: Q = {:.1f} kN".format(
    30.84 * foundation_length * foundation_width))
print("  - Target from Liu et al.: 2522 kN")
print("="*60)
