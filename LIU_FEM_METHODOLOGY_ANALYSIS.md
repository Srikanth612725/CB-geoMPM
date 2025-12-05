# Analysis of Liu et al. (2022) FEM Methodology for Bearing Capacity

## From the Paper

### Section 3.2 - Finite Element Method:

**Key Quote 1**:
> "The FE software ABAQUS is used to analyze the bearing capacity of the A-shaped mats... **A load reference point (LRP) is set at the centroid of the interface of the mat and soil**, as shown in Figure 8. **The LRP is coupled to the foundation surface** to control the three-dimensional motion of the mat."

**Key Quote 2**:
> "The stiffness of the mat is significantly greater than that of the soil, so **the foundation is set as a rigid body**."

**Key Quote 3** (Section 2.3 - Test Results):
> "The vertical displacement of the mat and the **soil reaction force were measured during the test**."

### Figure 8: Loading Condition
Shows:
- Load Reference Point (LRP) at center of foundation base
- Vertical load V applied at LRP
- Horizontal load H and Moment M also at LRP
- Foundation is coupled to LRP (rigid body constraint)

### Figure 10: FEM Results
- X-axis: S (settlement) in meters, 0 to 0.5m
- Y-axis: V (vertical load) in kN, 0 to ~2500 kN
- This is the **REACTION FORCE** at the LRP as foundation is pushed down

---

## The FEM Approach (ABAQUS)

1. **Foundation Modeling**:
   - Rigid body (infinitely stiff)
   - All foundation surface nodes coupled to single LRP
   - LRP located at centroid of foundation base

2. **Loading Method**:
   - **Displacement-controlled** (not force-controlled!)
   - Prescribe vertical displacement at LRP
   - LRP moves down, foundation follows (rigid coupling)

3. **Bearing Capacity Measurement**:
   - ABAQUS automatically calculates **REACTION FORCE** at LRP
   - Reaction force = force needed to maintain prescribed displacement
   - Reaction force = resistance from soil = **bearing capacity**

4. **Why This Works**:
   - When you push foundation down (prescribed displacement)
   - Soil resists this motion
   - To maintain the displacement, a force must be applied
   - This force = soil reaction = bearing capacity

---

## Translation to MPM

### What We Have in MPM:
1. Foundation represented by particles (not rigid body + LRP)
2. Prescribed velocity on foundation particles (displacement-control equivalent)
3. No automatic "reaction force" calculation

### What We Need to Calculate:
**Bearing capacity = Total vertical force exerted by soil on foundation**

This is equivalent to the "reaction force" in FEM.

### Options for Calculating This:

#### Option A: Force Balance on Foundation (Correct Approach)
```python
def calculate_bearing_capacity_force_balance(self):
    """
    Calculate total force on foundation from Newton's 2nd law:
    F_total = m × a

    For prescribed velocity foundation:
    - Acceleration = (v_new - v_old) / dt
    - If velocity is constant (prescribed), a ≈ 0
    - BUT there are forces acting: F_soil (resistance) and F_prescribed (to maintain velocity)
    - F_soil = bearing capacity (upward)
    - F_prescribed = force needed to maintain downward velocity
    - F_soil = F_prescribed
    """

    # Total mass of foundation
    foundation_mass = sum(self.particles[i].mass for i in self.foundation_indices)

    # Total force on foundation from soil (from grid)
    total_force_y = 0.0
    for idx in self.foundation_indices:
        mp = self.particles[idx]
        nodes, N, _, _ = self.get_shape_functions(mp)

        for k, node in enumerate(nodes):
            # Grid force on this particle
            total_force_y += N[k] * self.grid_fy[node]

    # Subtract body force (gravity on foundation)
    gravity_force = foundation_mass * self.gravity

    # Bearing capacity = upward resistance from soil
    bearing_capacity = -(total_force_y - gravity_force)  # Negative because compression

    return abs(bearing_capacity)
```

**Problem with this**: `grid_fy` includes internal forces, boundary forces, everything.

#### Option B: Stress in Foundation Particles (Most Direct)
```python
def calculate_bearing_capacity_foundation_stress(self):
    """
    Measure bearing capacity from stress in foundation particles themselves.

    Foundation particles are in compression due to soil resistance.
    σyy in foundation × foundation area = bearing capacity
    """

    # Foundation dimensions
    found_x = [self.particles[i].x for i in self.foundation_indices]
    found_y = [self.particles[i].y for i in self.foundation_indices]

    foundation_width = max(found_x) - min(found_x)
    foundation_thickness = max(found_y) - min(found_y)

    # Sum vertical stress × volume in foundation particles
    total_stress_volume = 0.0
    for idx in self.foundation_indices:
        mp = self.particles[idx]
        # Vertical stress (compression = negative)
        total_stress_volume += abs(mp.stress_yy) * mp.volume

    # Convert to force per unit length (2D)
    # stress × volume = stress × (area × thickness) = force × thickness
    total_force = total_stress_volume / foundation_thickness

    return total_force
```

**Key Question**: Are foundation particles updating their stress? Need to check the code.

#### Option C: Interface Traction (Complex)
Calculate traction (stress) at the exact soil-foundation interface and integrate.

---

## Critical Issue to Investigate

**Do foundation particles update their stress in current MPM code?**

Check in `mpm_step()`:
1. Are foundation particles (material_id=1) included in stress update?
2. If yes, their stress should reflect compression from soil contact
3. If no, they're purely kinematic (no stress) - then Option B won't work

---

## My Hypothesis on Why Previous Methods Failed

### v1 (Stress in soil below foundation):
- ❌ Soil gets pushed away, zone becomes empty → 0 kN/m

### v2 (Grid forces on foundation):
- ❌ grid_fy includes ALL forces (internal, gravity, BC enforcement, numerical artifacts)
- ❌ Taking abs() adds everything together regardless of direction
- ❌ Not isolating soil resistance specifically

### v3 (Thinner soil zone):
- ❌ Same problem as v1, just with thinner zone
- ❌ Still measures soil that moves away

---

## Next Steps (Option D - Get Clarity)

1. **Read MPM source code** to understand:
   - How are foundation particles treated?
   - Do they update stress?
   - What does `grid_fy` actually contain?

2. **Check if foundation stress is available**:
   - Print `mp.stress_yy` for foundation particles during simulation
   - See if it develops compression (negative values increasing)

3. **Understand grid force components**:
   - What contributes to `grid_fy`?
   - Can we isolate soil-foundation contact force?

4. **Look for MPM bearing capacity references**:
   - How do other MPM studies calculate bearing capacity?
   - What's the standard method?

5. **Consider alternative approach**:
   - Maybe need to track contact forces explicitly
   - Or use a thin "sensor" layer that doesn't move

Would you like me to investigate the current MPM code to understand how forces and stresses are actually calculated?
