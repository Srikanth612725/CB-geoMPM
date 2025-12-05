"""
DIAGNOSTIC: Why calculate_bearing_capacity() is 4× too high
=============================================================

ANALYSIS OF THE BUG IN mpm_optimized.py::calculate_bearing_capacity()
"""

print("="*70)
print("BEARING CAPACITY CALCULATION ANALYSIS")
print("="*70)

# User's simulation parameters
domain_height = 20.0  # m
ny = 30
dy = domain_height / ny
print(f"\nGrid parameters:")
print(f"  dy = {dy:.3f} m")

soil_depth = 15.0  # m
foundation_base = soil_depth
foundation_width = 5.0  # m

# Interface parameters (from code line 532-533)
interface_thickness = 1.5 * dy
print(f"\nInterface zone:")
print(f"  Thickness = 1.5 × dy = {interface_thickness:.3f} m")
print(f"  Foundation base: y = {foundation_base:.1f} m")
print(f"  Interface zone: {foundation_base - interface_thickness:.1f} < y < {foundation_base:.1f} m")
print(f"  Zone captures: {(foundation_base - (foundation_base - interface_thickness)):.1f} m of soil below foundation")

# Stress in this zone
rho = 1600  # kg/m³
g = 9.81    # m/s²
su = 6000   # Pa

print(f"\n{'='*70}")
print("STRESS ANALYSIS")
print("="*70)

# Initial geostatic stress (line 313-314 of mpm_optimized.py)
# depth is measured from soil surface (y_max = 15m)
# At y=15m (surface): depth=0, syy=0
# At y=14m: depth=1m, syy = -rho*g*1

print(f"\nInitial geostatic stress (before foundation):")
for y in [15.0, 14.5, 14.0]:
    depth_from_surface = soil_depth - y
    syy_init = -rho * g * depth_from_surface
    print(f"  At y={y:.1f}m: depth={depth_from_surface:.1f}m, σ_v = {syy_init/1000:.1f} kPa")

print(f"\n{'='*70}")
print("THE BUG")
print("="*70)

print(f"""
The calculate_bearing_capacity() method (lines 519-555):

1. Captures soil particles in zone: 14.0 < y < 15.0 m (1m thick!)
2. For each particle: pressure = -mp.syy (current vertical stress)
3. Weights by: exp(-distance/thickness)
4. Returns: avg_pressure × foundation_width

PROBLEM #1: INTERFACE ZONE TOO THICK
-------------------------------------
The interface thickness is 1.5 × dy = {interface_thickness:.3f} m = 1 meter!

This captures stresses over a 1m thick zone below the foundation.
But stress varies significantly with depth due to:
  - Stress concentration directly under foundation
  - Stress spreading with depth (Boussinesq distribution)

A 1m zone is TOO LARGE - it should be ~0.1-0.2 m (2-3 particle layers).

PROBLEM #2: MEASURING AT WRONG LOCATION
----------------------------------------
The method measures stress in SOIL BELOW the foundation, not
AT THE INTERFACE (contact pressure).

For a rigid foundation on elastic soil:
  - Contact pressure is NON-UNIFORM (higher at edges)
  - Stress in soil at depth z below foundation is DIFFERENT
    from contact pressure

Measuring stress 0.5m below foundation captures a DIFFERENT
stress state than the actual bearing pressure.

PROBLEM #3: PARTICLE AVERAGING
-------------------------------
Grid: 60×30, dy = {dy:.3f} m
Particles per cell: 4 (2×2)
Particle spacing: dy/2 = {dy/2:.3f} m

Interface zone thickness: {interface_thickness:.3f} m
Number of particle LAYERS captured: ~{interface_thickness/(dy/2):.0f} layers

The exponential weighting gives more weight to particles closer
to foundation base, but still averages over {interface_thickness/(dy/2):.0f} layers of particles.

This over-samples the stress field and may give artificially
high values due to stress concentrations.

EXPECTED vs ACTUAL
------------------
Expected (Prandtl):  q = 6 kPa × 5.14 = 30.8 kPa
                     Q = 30.8 × 5m = 154 kN/m

User got: 582 kN/m (3.78× too high!)

Implied pressure: 582 / 5 = 116 kPa
Error: (116 - 30.8) / 30.8 = 277% !!

HYPOTHESIS
----------
The 1m thick interface zone is capturing stress from a region
where stress magnitude is amplified due to:
  1. Proximity to foundation (stress concentration)
  2. Multiple particle layers being averaged
  3. Possibly measuring peak stresses rather than average

The method should instead:
  1. Reduce interface thickness to 0.2-0.3 m (just 1-2 particle layers)
  2. Or: Integrate reaction forces on foundation particles from grid
  3. Or: Use a proper contact mechanics approach
""")

print(f"\n{'='*70}")
print("RECOMMENDED FIX")
print("="*70)

print(f"""
Option A: Reduce interface thickness
-------------------------------------
Change line 532 from:
    interface_thickness = 1.5 * self.dy

To:
    interface_thickness = 0.25 * self.dy  # Just 1 particle layer

This samples stress much closer to the actual contact interface.

Option B: Use foundation particle forces (BETTER)
--------------------------------------------------
Instead of measuring soil stress, calculate reaction force
from the forces acting ON the foundation particles:

def calculate_bearing_capacity(self):
    if not self.foundation_indices:
        return 0.0

    # Sum vertical forces on foundation particles
    total_force = 0.0
    for idx in self.foundation_indices:
        mp = self.particles[idx]
        # Get vertical force from grid nodes
        nodes, N, _, _ = self.get_shape_functions(mp)
        for k, node in enumerate(nodes):
            total_force += N[k] * self.grid_fy[node]

    # Normalize by foundation width
    foundation_width = ...  # calculate from foundation particles
    return total_force / foundation_width

This directly measures the REACTION FORCE on the foundation,
which is the TRUE bearing capacity.

Option C: Further diagnose current method
-----------------------------------------
Add debug output to see what stresses are actually being measured:
  - Print avg_pressure value
  - Print number of particles in interface zone
  - Plot stress distribution in interface zone
""")

print(f"\n{'='*70}")
print("IMMEDIATE ACTION")
print("="*70)
print(f"""
1. Try changing interface_thickness to 0.25 × dy
2. Re-run ONE simulation to see if capacity is closer to 154 kN/m
3. If still wrong, implement Option B (use foundation reaction forces)
""")
