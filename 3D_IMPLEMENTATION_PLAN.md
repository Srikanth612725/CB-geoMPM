# 3D A-Shaped Mat Implementation Plan

## 📋 Objective
Implement full 3D MPM simulation of A-shaped mat foundation to validate against Liu et al. (2022) experimental data: **2522 kN total capacity**

---

## 📐 Geometry from Liu et al. (2022) Paper

### Key Dimensions (Prototype Scale):
- **Overall dimensions**: 10m × 10m (approximate)
- **Foundation basal area**: 68.40 m²
- **Moments of inertia**:
  - Ix = 534.66 m⁴
  - Iy = 650.21 m⁴
- **Idealized rectangular dimensions**:
  - Bx' = 10.68 m
  - By' = 7.06 m

### Geometric Features:
1. **Bow (front)**: Triangular/boat-shaped with perforation
   - Bow angle α (kept constant)
   - Perforation size: ~2.5m triangular opening

2. **Stern (back)**: Wellhead groove
   - Groove size: ~2.0m rectangular notch

3. **Cross-member**: Connects left and right sides
   - Position parameter J = 0.5 (middle of foundation)
   - Width: ~1-2m beam

### Soil Properties (Centrifuge Test):
- **Undrained shear strength**: su = 6 kPa
- **Unit weight**: γ' = 6 kN/m³
- **Poisson's ratio**: ν = 0.49 (undrained)
- **Young's modulus**: E = 500 × su = 3000 kPa
- **Material model**: Tresca yield criterion (von Mises equivalent)

### Target Results:
- **Ultimate bearing capacity**: 2522 kN (total)
- **Expected Nc**: ~6.1 (includes 3D shape effects)
- **Bearing pressure**: 2522 / 68.4 = 36.87 kPa

---

## 🔧 Implementation Approach

### Phase 1: 3D MPM Framework (1-2 days)
**File**: `mpm_3d_optimized.py`

**Core Components**:
1. **3D Grid Setup**
   - Domain: 60m × 60m × 20m (6× foundation width)
   - Grid cells: nx × ny × nz (e.g., 60 × 60 × 30)
   - Node indexing: `node_id = i + j*nx + k*nx*ny`

2. **3D Particle Class**
   ```python
   class Particle3D:
       x, y, z          # Position
       vx, vy, vz       # Velocity
       mass             # Mass
       volume           # Volume
       F                # Deformation gradient (3×3)
       stress           # Cauchy stress tensor (3×3)
       material_id      # 0=soil, 1=foundation
   ```

3. **3D Shape Functions** (Trilinear interpolation)
   - 8 nodes per cell (cube)
   - Weights: Ni = Nix × Niy × Niz
   - Gradients: ∂Ni/∂x, ∂Ni/∂y, ∂Ni/∂z

4. **3D Constitutive Model**
   - Tresca yield: τmax = su
   - Or von Mises: √(3J2) = su (equivalent for undrained)
   - Elastic: σ = 2G εdev + K εvol I
   - Plastic: Return mapping to yield surface

### Phase 2: A-Shaped Geometry Generation (1 day)
**File**: `geometry_a_shaped.py`

**Function**: `generate_a_shaped_mat_particles()`

**Algorithm**:
```python
def generate_a_shaped_mat(center_x, center_y, z_base):
    """
    Generate 3D A-shaped mat with:
    - Total area: 68.4 m²
    - Bow perforation
    - Stern wellhead groove
    - Cross-member at J=0.5
    """

    # 1. Define base rectangular region (10m × 10m)
    base_width = 10.0
    base_length = 10.0

    # 2. Add bow (triangular front) - increases Iy
    bow_length = 2.5  # Extends forward
    bow_perforation_area = 2.5  # Triangular hole

    # 3. Add stern groove (rectangular notch) - decreases area
    stern_groove_width = 2.0
    stern_groove_depth = 1.0

    # 4. Add cross-member
    cross_member_width = 1.5
    cross_member_position = base_length / 2  # J=0.5

    # 5. Generate particles with 4-8 ppc
    # Check each particle (x,y,z) if inside A-shape
    particles = []
    for x, y, z in particle_positions:
        if is_inside_a_shape(x, y, z):
            particles.append(create_foundation_particle(x, y, z))

    return particles

def is_inside_a_shape(x, y, z):
    """Check if point is inside A-shaped footprint"""
    # Check base rectangle
    # Subtract bow perforation
    # Subtract stern groove
    # Include cross-member
    return in_base and not in_perforation and not in_groove
```

**Verification**:
- Calculate actual area: should be 68.4 ± 0.5 m²
- Calculate Ix, Iy: should match 534.66, 650.21 ± 5%
- Visualize in 3D (matplotlib or mayavi)

### Phase 3: 3D Bearing Capacity Calculation (0.5 day)
**Method**: Sum vertical reaction forces on foundation

```python
def calculate_bearing_capacity_3d(self):
    """Calculate total bearing force on 3D foundation"""
    total_force_z = 0.0

    for idx in self.foundation_indices:
        mp = self.particles[idx]
        nodes, N, _, _, _ = self.get_shape_functions_3d(mp)

        for k, node in enumerate(nodes):
            # Sum vertical grid forces weighted by shape functions
            total_force_z += abs(N[k] * self.grid_fz[node])

    return total_force_z  # Should be ~2522 kN
```

### Phase 4: Simulation Setup and Validation (1 day)
**File**: `run_3d_validation.py`

**Simulation Parameters**:
```python
# Domain
domain = (0, 60), (0, 60), (0, 20)  # m
grid = 60, 60, 30  # cells

# Soil
su = 6000  # Pa
E = 3e6    # Pa
nu = 0.495
rho = 1600  # kg/m³

# Foundation
center = (30, 30, 15)  # m
velocity = -0.10  # m/s (downward)

# Simulation
dt = 0.0001  # s
max_steps = 50000
target_settlement = 0.30  # m (10% of Bx)
record_interval = 200
```

**Expected Output**:
```
Step     0: s=  0.0mm, F=    0 kN
Step  1000: s= 50.0mm, F= 1200 kN
Step  2000: s=100.0mm, F= 2000 kN
Step  3000: s=150.0mm, F= 2400 kN
Step  4000: s=200.0mm, F= 2550 kN (PEAK)
Step  5000: s=250.0mm, F= 2520 kN (PLATEAU)

✅ Ultimate capacity: 2522 kN
   Expected (Liu): 2522 kN
   Error: 0.0%
```

---

## 📊 Validation Metrics

### Primary Metric:
| Parameter | Liu (2022) | 3D MPM Target | Acceptable Range |
|-----------|-----------|---------------|------------------|
| Ultimate capacity | 2522 kN | 2522 kN | 2400-2600 kN (±5%) |
| Nc,V | 6.1 | 6.1 | 5.8-6.4 |
| Bearing pressure | 36.87 kPa | 36.87 kPa | 35-39 kPa |

### Secondary Checks:
- Load-settlement curve shape should match Figure 6 in paper
- Soil failure mechanism: plastic zone should extend ~2-3× foundation width
- Foundation should settle uniformly (no excessive tilt)

---

## ⚠️ Challenges and Solutions

### Challenge 1: 3D MPM is Computationally Expensive
**Problem**: 60×60×30 grid with 4 ppc = ~400,000 particles!

**Solutions**:
1. **Start coarse**: 40×40×20 grid (~100,000 particles)
2. **Use Numba JIT**: 10-100× speedup for particle loops
3. **Reduce domain**: 4× foundation width instead of 6×
4. **Larger timestep**: dt = 0.0002s (2× faster)

### Challenge 2: Complex A-Shape Geometry
**Problem**: Hard to define mathematically

**Solutions**:
1. **Approximate**: Start with simplified bow (circular arc)
2. **Iterative refinement**: Match area first, then Ix/Iy
3. **Visual verification**: Plot 2D footprint before running

### Challenge 3: 3D Constitutive Model
**Problem**: Full 3D stress tensor (6 components)

**Solutions**:
1. **Use Tresca** (simpler than Mohr-Coulomb)
2. **Borrow from 2D**: Extend plane strain formulation
3. **Check literature**: Many open-source implementations available

---

## 📁 File Structure

```
A-mat-Journal/
├── mpm_3d_optimized.py          # 3D MPM solver
├── geometry_a_shaped.py          # A-shape geometry generator
├── constitutive_3d.py            # 3D Tresca/von Mises models
├── run_3d_validation.py          # Validation script
├── visualize_3d.py               # 3D plotting utilities
├── 3D_IMPLEMENTATION_PLAN.md     # This file
└── 3D_VALIDATION_RESULTS.md      # Results (TBD)
```

---

## 🎯 Success Criteria

✅ **MINIMUM**:
- 3D simulation runs without crashing
- Bearing capacity in range 2400-2600 kN (±5% error)

✅ **GOOD**:
- Bearing capacity = 2522 ± 50 kN (<2% error)
- Load-settlement curve shape matches Liu's Figure 6

✅ **EXCELLENT**:
- Bearing capacity = 2522 ± 20 kN (<1% error)
- Soil failure mechanism matches expected pattern
- Can simulate full V-H-M envelope

---

## ⏱️ Timeline

| Phase | Description | Time | Status |
|-------|-------------|------|--------|
| 1 | 3D MPM Framework | 1-2 days | 🔄 Next |
| 2 | A-Shaped Geometry | 1 day | ⏳ Pending |
| 3 | Bearing Capacity Method | 0.5 day | ⏳ Pending |
| 4 | Validation Simulation | 1 day | ⏳ Pending |
| **Total** | | **3-4 days** | |

---

## 🚀 Next Steps

1. ✅ **DONE**: Fix 2D bearing capacity (use v2 method) → User will test in Colab
2. 🔄 **NOW**: Create 3D MPM framework (`mpm_3d_optimized.py`)
3. ⏭️ **NEXT**: Implement A-shaped geometry generator
4. ⏭️ **THEN**: Run validation test and compare with Liu (2022)

---

## 📚 References

Liu, R., Cai, R., Chen, G., & Liang, C. (2022). The bearing capacity of A-shaped mat foundations on cohesive soil. *Ships and Offshore Structures*. DOI: 10.1080/17445302.2022.2116208

**Key findings**:
- Centrifuge test: 2522 kN capacity
- FEM validation: 2524 kN (0.08% error)
- ECM: 2337-2386 kN (7.4% error)
- Our goal: <5% error with 3D MPM
