#!/usr/bin/env python3
"""
SIMPLE VALIDATION TEST
======================

Quick test to validate tangent method improves accuracy.
Uses minimal parameters for fast execution (~1-2 minutes).
"""

import numpy as np
import matplotlib.pyplot as plt

# ============================================================================
# STEP 1: Run a quick MPM simulation
# ============================================================================

print("="*70)
print("SIMPLE VALIDATION TEST - Tangent Method")
print("="*70)

from mpm_optimized import MPM2D_Optimized

# Quick Prandtl test (small, fast)
su = 6000  # 6 kPa
B = 5.0    # 5m foundation
E = 100 * su
rho = 1600

print("\nTest case: Prandtl strip foundation")
print(f"  Foundation: {B}m wide")
print(f"  Soil: su = {su/1000}kPa")

# Expected capacity
Nc_prandtl = 2 + np.pi
Q_expected = su * B * Nc_prandtl / 1000  # kN/m
print(f"  Expected (Prandtl): {Q_expected:.0f} kN/m (Nc = {Nc_prandtl:.2f})")

# Create MPM solver (SMALL for speed)
print("\nSetting up MPM simulation (small/fast)...")
mpm = MPM2D_Optimized(
    domain_x=[0, 30],
    domain_y=[0, 15],
    nx=40,  # COARSE for speed
    ny=20,  # COARSE for speed
    su=su,
    E=E,
    nu=0.495,
    rho=rho,
    use_gimp=False  # Standard MPM (verified correct)
)

# Add soil
mpm.add_soil_block([0, 30], [0, 10], ppc=4)

# Add foundation
mpm.add_strip_foundation(
    center_x=15,
    y_base=10,
    width=B,
    thickness=0.5,
    density=2500
)

print(f"  Particles: {len(mpm.particles)}")

# Run simulation (FAST parameters)
print("\nRunning simulation (1-2 minutes)...")
dt = mpm.timestep()
mpm.foundation_velocity = -0.10  # FAST rate (10x faster than before)

settlements = []
loads = []
step = 0
max_steps = 2000  # Less steps needed with fast rate
target_settlement = 0.05  # 50mm (less than before)

while step < max_steps:
    mpm.mpm_step(dt)
    step += 1

    current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])
    settlement = mpm.foundation_y0 - current_y

    if step % 200 == 0:
        q = mpm.calculate_bearing_capacity() / 1000
        settlements.append(settlement)
        loads.append(q)
        print(f"  Step {step:4d} | s={settlement*1000:.1f}mm | q={q:.0f} kN/m")

    if settlement >= target_settlement:
        print(f"  Reached target settlement!")
        break

settlements = np.array(settlements)
loads = np.array(loads)

# ============================================================================
# STEP 2: Compare MAX method vs TANGENT method
# ============================================================================

print("\n" + "="*70)
print("COMPARING METHODS")
print("="*70)

# Method 1: MAX (old method)
Q_max = np.max(loads)
error_max = abs(Q_max - Q_expected) / Q_expected * 100

print(f"\n1. MAX METHOD (old):")
print(f"   Q_ultimate: {Q_max:.0f} kN/m")
print(f"   Error: {error_max:.1f}%")

# Method 2: TANGENT INTERSECTION (new method)
from tangent_method import tangent_intersection_method

result = tangent_intersection_method(settlements, loads, plot=False)
Q_tangent = result['Q_ult']
error_tangent = abs(Q_tangent - Q_expected) / Q_expected * 100

print(f"\n2. TANGENT METHOD (new):")
print(f"   Q_ultimate: {Q_tangent:.0f} kN/m")
print(f"   Error: {error_tangent:.1f}%")
print(f"   Method used: {result['method']}")

# ============================================================================
# STEP 3: Results and Visualization
# ============================================================================

print("\n" + "="*70)
print("VALIDATION RESULTS")
print("="*70)

improvement = error_max - error_tangent

print(f"\nExpected (Prandtl):   {Q_expected:.0f} kN/m")
print(f"MAX method:           {Q_max:.0f} kN/m ({error_max:.1f}% error)")
print(f"TANGENT method:       {Q_tangent:.0f} kN/m ({error_tangent:.1f}% error)")
print(f"\nImprovement: {improvement:.1f} percentage points")

if error_tangent < 10:
    print("\n✅ SUCCESS! Tangent method achieves <10% error")
elif error_tangent < error_max * 0.8:
    print("\n✅ IMPROVEMENT! Tangent method reduces error by >20%")
elif error_tangent < error_max:
    print("\n✅ BETTER! Tangent method is more accurate")
else:
    print("\n⚠️  No significant improvement")

# Plot
fig, ax = plt.subplots(figsize=(10, 6))

ax.plot(settlements * 1000, loads, 'b-', linewidth=2, label='MPM simulation')
ax.axhline(Q_expected, color='g', linestyle='--', linewidth=2,
           label=f'Expected (Prandtl): {Q_expected:.0f} kN/m')
ax.axhline(Q_max, color='r', linestyle=':', linewidth=2,
           label=f'MAX method: {Q_max:.0f} kN/m ({error_max:.1f}% error)')
ax.axhline(Q_tangent, color='orange', linestyle='-.', linewidth=2,
           label=f'TANGENT method: {Q_tangent:.0f} kN/m ({error_tangent:.1f}% error)')

ax.set_xlabel('Settlement (mm)', fontsize=12)
ax.set_ylabel('Load (kN/m)', fontsize=12)
ax.set_title('Tangent Method Validation - Prandtl Test', fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('tangent_validation_results.png', dpi=150)
print(f"\n📊 Plot saved: tangent_validation_results.png")
plt.show()

print("\n" + "="*70)
print("✅ VALIDATION COMPLETE!")
print("="*70)

if error_tangent < 15:
    print("\n🎯 Tangent method is VALIDATED and ready for parametric study!")
else:
    print("\n⚠️  Consider additional calibration for better accuracy")
