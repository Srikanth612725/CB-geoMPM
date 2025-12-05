# ROOT CAUSE: Why All Bearing Capacity Methods Failed

## Discovery from Code Analysis

### Current MPM Implementation (mpm_optimized.py, lines 472-510):

```python
# G2P - Update particle state
for mp in self.particles:
    if mp.material_id == 0:  # ← ONLY SOIL!
        # Update velocity from grid
        # Calculate strain increment
        # Update volume
        # Update stress (elastic + plasticity)

    # Position update for ALL particles
    mp.x += dt * mp.vx
    mp.y += dt * mp.vy
```

**KEY FINDING**: Foundation particles (material_id=1) are **purely kinematic** - they:
- ✅ Have prescribed velocity (line 468-469)
- ✅ Update position
- ❌ Do NOT update velocity from grid
- ❌ Do NOT calculate strain
- ❌ Do NOT update stress

---

## What This Means

### Foundation Particles:
- `stress_xx`, `stress_yy`, `stress_xy` remain at initial values (probably 0)
- They are "ghost" particles that just mark the foundation position
- They have NO physical stress state

### Soil Particles:
- Update stress based on deformation
- Develop compression under foundation
- This is where the bearing capacity information lives

---

## Why Each Method Failed

### v1: `calculate_bearing_capacity()` - Measure stress in soil zone
```python
# Define zone 1.0m below foundation
interface_thickness = 1.5 * self.dy  # = 1.0m
# Find soil particles in this zone
# Average their stress_yy
```

**Why it failed**:
- ❌ As foundation settles, it PUSHES SOIL AWAY
- ❌ The measurement zone (1.0m thick) becomes EMPTY of soil particles
- ❌ No particles in zone → stress_yy = 0 → capacity = 0 kN/m

**Even at v3 (thinner zone)**:
- `interface_thickness = 0.1 * dy = 0.067m`
- Still measures SOIL stress in fixed zone
- Soil still gets pushed away
- Result: Still 0 kN/m

---

### v2: `calculate_bearing_capacity_v2()` - Sum grid forces on foundation
```python
for idx in self.foundation_indices:
    mp = self.particles[idx]
    nodes, N, _, _ = self.get_shape_functions(mp)
    for k, node in enumerate(nodes):
        total_reaction += abs(N[k] * self.grid_fy[node])
```

**What is `grid_fy[node]`?** (from lines 438-449):

1. **Internal forces from particle stress** (line 438-442):
   ```python
   for mp in self.particles:  # ALL particles
       self.grid_fy[n] -= mp.volume * (mp.sxy * dNdx[k] + mp.syy * dNdy[k])
   ```
   - Includes soil stress (good!)
   - Includes foundation stress (but it's ~0, so doesn't matter)

2. **Gravity on soil** (line 445-449):
   ```python
   if mp.material_id == 0:  # Only soil
       self.grid_fy[n] -= N[k] * mp.mass * 9.81
   ```

**Why it failed**:
- ❌ `grid_fy` is net force AFTER internal forces + gravity
- ❌ Includes forces from ALL directions (not just soil-foundation interface)
- ❌ Includes computational artifacts from grid updates
- ❌ Taking `abs()` adds up forces regardless of direction
- ❌ Result: Overestimation (742 kN/m vs 154 kN/m)

The grid forces are intermediate computational values, not physical contact forces!

---

## The Correct Approach

Based on Liu et al. (2022) FEM methodology:
- Bearing capacity = **Reaction force at foundation**
- In FEM: Measured at Load Reference Point (LRP)
- In MPM: Must calculate from soil-foundation interaction

### Option 1: Integrate Soil Contact Stress (Most Physical)

**Concept**: Find soil particles currently in contact with foundation, sum their stress contribution

```python
def calculate_bearing_capacity_CORRECT(self):
    """
    Measure bearing capacity from soil contact stress

    Method:
    1. Find soil particles in contact with foundation
    2. Calculate their contribution to vertical force
    3. Sum = bearing capacity
    """

    # Foundation boundaries
    found_x = [self.particles[i].x for i in self.foundation_indices]
    found_y = [self.particles[i].y for i in self.foundation_indices]

    x_min = min(found_x)
    x_max = max(found_x)
    y_bottom = min(found_y)  # Bottom of foundation

    foundation_width = x_max - x_min

    # Contact detection parameters
    contact_distance = 0.5 * self.dy  # Half cell size

    # Find soil particles in contact with foundation bottom
    contact_particles = []
    for i, mp in enumerate(self.particles):
        if mp.material_id == 0:  # Soil only
            # Horizontal: under foundation
            if x_min <= mp.x <= x_max:
                # Vertical: close to foundation bottom
                if y_bottom - contact_distance <= mp.y <= y_bottom + contact_distance:
                    contact_particles.append(i)

    if len(contact_particles) == 0:
        return 0.0

    # Calculate total vertical force from contact particles
    total_force = 0.0
    for idx in contact_particles:
        mp = self.particles[idx]

        # Method A: Use particle stress directly
        # Vertical stress in soil (compression = negative)
        stress_contribution = abs(mp.syy) * mp.volume / contact_distance
        total_force += stress_contribution

    return total_force
```

**Key Differences**:
1. ✅ Contact detection: Find particles CURRENTLY near foundation (not fixed zone)
2. ✅ Uses SOIL particle stress (where physics actually happens)
3. ✅ Adapts as foundation moves (particles in contact change)

---

### Option 2: Force Balance on Foundation (Physics-Based)

**Concept**: Foundation has prescribed velocity against soil resistance.
The force needed to maintain this velocity = bearing capacity.

```python
def calculate_bearing_capacity_force_balance(self):
    """
    Calculate bearing capacity from force balance

    For foundation with prescribed velocity v_prescribed:
    - Soil exerts upward force F_soil (resistance)
    - We apply downward force F_applied to maintain velocity
    - At equilibrium: F_applied = F_soil = bearing capacity

    In MPM:
    - Calculate what velocity foundation WOULD have from soil forces alone
    - Actual velocity is prescribed
    - Difference gives constraint force = bearing capacity
    """

    # This requires tracking grid forces before BC application
    # Complex to implement in current framework
    pass
```

**Challenge**: Current code applies prescribed velocity directly to particles, not through grid constraint forces.

---

### Option 3: Measure Total Vertical Stress Under Foundation

**Concept**: Integrate vertical stress over foundation area

```python
def calculate_bearing_capacity_integration(self):
    """
    Integrate vertical stress over foundation footprint

    Similar to FEM where you integrate traction over surface
    """

    found_x = [self.particles[i].x for i in self.foundation_indices]
    x_min, x_max = min(found_x), max(found_x)
    foundation_width = x_max - x_min

    # Sample stress field at foundation base
    y_base = min(self.particles[i].y for i in self.foundation_indices)
    n_samples = 50
    dx_sample = foundation_width / n_samples

    total_stress = 0.0
    for i in range(n_samples):
        x_sample = x_min + (i + 0.5) * dx_sample

        # Find nearest soil particle
        min_dist = 1e10
        nearest_stress = 0.0
        for mp in self.particles:
            if mp.material_id == 0:
                dist = sqrt((mp.x - x_sample)**2 + (mp.y - y_base)**2)
                if dist < min_dist:
                    min_dist = dist
                    nearest_stress = abs(mp.syy)

        total_stress += nearest_stress * dx_sample

    return total_stress
```

---

## Recommendation

**Option 1 (Contact-based)** is most physical and robust:
- Detects which soil particles are actually in contact
- Uses their stress (where the physics happens)
- Adapts as foundation settles
- Similar to FEM interface integration

**Test this first** before implementing 3D.

---

## Action Items

1. Implement Option 1 (contact-based method)
2. Test with small case
3. Check if results are reasonable (~154 kN/m)
4. If successful, update all COLAB scripts
5. Only then proceed with 3D implementation

**No more guessing. Test this properly.**
