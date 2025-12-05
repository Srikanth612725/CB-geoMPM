#!/usr/bin/env python3
"""
QUICK TANGENT METHOD VALIDATION (1-2 minutes)
==============================================

Fast test to validate if tangent method improves accuracy before running
the full comprehensive suite.

Uses highly optimized parameters:
- Fast settlement rate (0.20 m/s, still quasi-static)
- Small target settlement (80mm)
- Coarse mesh (50x25)
- Prandtl case (simpler, faster)
"""

import numpy as np
import matplotlib.pyplot as plt
import time
from mpm_optimized import MPM2D_Optimized
from tangent_method import tangent_intersection_method

print("="*70)
print("QUICK TANGENT METHOD VALIDATION")
print("="*70)

# Test parameters
su = 6000  # 6 kPa (Prandtl test)
B = 5.0    # 5m foundation
E = 100 * su
nu = 0.495
rho = 1600
rate = 0.05  # Fast but quasi-static settlement rate
target = 0.08  # 80mm

# Expected capacity (Prandtl)
Nc = 2 + np.pi
Q_expected = su * B * Nc / 1000  # kN/m

print(f"\nTest parameters:")
print(f"  Foundation: {B}m wide")
print(f"  Soil: su = {su/1000}kPa")
print(f"  Expected (Prandtl): {Q_expected:.0f} kN/m")
print(f"  Settlement rate: {rate} m/s")
print(f"  Target: {target*1000:.0f}mm")

# Quasi-static check
inertial_ratio = (rho * rate**2) / su
print(f"  Inertial/Strength: {inertial_ratio:.6f} ({'✅ QS' if inertial_ratio < 0.01 else '⚠️ Dynamic'})")

# Create MPM
print(f"\nCreating MPM simulation (coarse mesh for speed)...")
mpm = MPM2D_Optimized(
    domain_x=[0, 30],
    domain_y=[0, 15],
    nx=50,  # Coarse
    ny=25,  # Coarse
    su=su,
    E=E,
    nu=nu,
    rho=rho,
    use_gimp=False
)

mpm.add_soil_block([0, 30], [0, 10], ppc=4)
mpm.add_strip_foundation(center_x=15, y_base=10, width=B, thickness=0.5, density=2500)

print(f"  Particles: {len(mpm.particles)}")
print(f"  Foundation: {len(mpm.foundation_indices)}")

# Run simulation
print(f"\nRunning simulation (expected ~1-2 minutes)...")
start = time.time()

dt = mpm.timestep()
mpm.foundation_velocity = -rate

settlements = []
loads = []
step = 0
record_interval = 100  # Record every 100 steps

while step < 5000:
    mpm.mpm_step(dt)
    step += 1

    current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])
    settlement = mpm.foundation_y0 - current_y

    # Record data every N steps
    if step % record_interval == 0:
        q = mpm.calculate_bearing_capacity() / 1000
        settlements.append(settlement)
        loads.append(q)

        if step % 300 == 0:
            print(f"  Step {step:4d} | s={settlement*1000:4.1f}mm | q={q:5.0f} kN/m")

    if settlement >= target:
        print(f"  Reached target at step {step}!")
        # Record final point
        q = mpm.calculate_bearing_capacity() / 1000
        settlements.append(settlement)
        loads.append(q)
        break

elapsed = time.time() - start
print(f"\nSimulation complete in {elapsed:.1f}s")

settlements = np.array(settlements)
loads = np.array(loads)

# Compare methods
print(f"\n{'='*70}")
print("COMPARING METHODS")
print(f"{'='*70}")

# Method 1: MAX
Q_max = np.max(loads)
error_max = abs(Q_max - Q_expected) / Q_expected * 100

print(f"\n1. MAX METHOD (original):")
print(f"   Q_ult: {Q_max:.0f} kN/m")
print(f"   Error: {error_max:.1f}%")

# Method 2: TANGENT
result = tangent_intersection_method(settlements, loads, plot=False)
Q_tangent = result['Q_ult']
error_tangent = abs(Q_tangent - Q_expected) / Q_expected * 100

print(f"\n2. TANGENT METHOD (new):")
print(f"   Q_ult: {Q_tangent:.0f} kN/m")
print(f"   Error: {error_tangent:.1f}%")
print(f"   Method: {result['method']}")

improvement = error_max - error_tangent

print(f"\n{'='*70}")
print("RESULTS")
print(f"{'='*70}")
print(f"Expected (Prandtl):  {Q_expected:.0f} kN/m")
print(f"MAX method:          {Q_max:.0f} kN/m ({error_max:.1f}% error)")
print(f"TANGENT method:      {Q_tangent:.0f} kN/m ({error_tangent:.1f}% error)")
print(f"\nImprovement: {improvement:.1f} percentage points")

if improvement > 5:
    print("✅ SIGNIFICANT IMPROVEMENT! Tangent method is effective!")
    print("   Proceed with full validation suite.")
elif improvement > 0:
    print("✅ Modest improvement. Tangent method helps.")
else:
    print("⚠️ No improvement. Tangent method may not be applicable here.")

# Plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Load-settlement curve
ax1.plot(settlements*1000, loads, 'b-', linewidth=2, label='MPM simulation')
ax1.axhline(Q_expected, color='g', linestyle='--', linewidth=2, label=f'Prandtl: {Q_expected:.0f} kN/m')
ax1.axhline(Q_max, color='r', linestyle=':', linewidth=2, label=f'Max: {Q_max:.0f} kN/m ({error_max:.1f}%)')
ax1.axhline(Q_tangent, color='orange', linestyle='-.', linewidth=2, label=f'Tangent: {Q_tangent:.0f} kN/m ({error_tangent:.1f}%)')
ax1.set_xlabel('Settlement (mm)')
ax1.set_ylabel('Load (kN/m)')
ax1.set_title('Quick Tangent Method Validation')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Error comparison
methods = ['Expected\n(Prandtl)', 'MAX\nMethod', 'TANGENT\nMethod']
values = [Q_expected, Q_max, Q_tangent]
colors = ['green', 'red', 'orange']
bars = ax2.bar(methods, values, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
ax2.axhline(Q_expected, color='g', linestyle='--', linewidth=1, alpha=0.5)
ax2.set_ylabel('Ultimate Load (kN/m)')
ax2.set_title('Method Comparison')
ax2.grid(True, alpha=0.3, axis='y')

for bar, val in zip(bars, values):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
            f'{val:.0f} kN', ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig('quick_tangent_validation.png', dpi=150)
print(f"\n📊 Plot saved: quick_tangent_validation.png")
plt.show()

print(f"\n{'='*70}")
print("NEXT STEPS")
print(f"{'='*70}")
if improvement > 3:
    print("✅ Tangent method shows promise!")
    print("   Run full validation suite:")
    print("   $ python3 validate_tangent_method_comprehensive.py")
else:
    print("⚠️ Tangent method doesn't show significant improvement on Prandtl case.")
    print("   This could be because:")
    print("   1. Load-settlement curve is already well-behaved")
    print("   2. Max method works well for this simple case")
    print("   3. Tangent method more useful for complex geometries (like Liu A-shape)")
    print("\n   Recommendation: Test on Liu case specifically")

print(f"\n⏱️  Total runtime: {elapsed:.1f}s")
