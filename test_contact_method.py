"""
Test Contact-Based Bearing Capacity Method
===========================================

This script tests all 4 bearing capacity methods:
- v1: Original (stress in fixed zone below foundation)
- v2: Grid forces on foundation
- v3: Thinner fixed zone
- contact: NEW contact detection method

Expected result: ~154 kN/m for B=5m, su=6kPa

Test parameters:
- Small domain: 30m × 20m
- Grid: 60 × 30
- Foundation: 5m width
- Settlement: 100mm (to see plateau)
- Fast rate: 0.10 m/s
"""

import numpy as np
import matplotlib.pyplot as plt
from mpm_optimized import MPM2D_Optimized
import time

print("="*70)
print("CONTACT-BASED BEARING CAPACITY TEST")
print("="*70)
print()

# Setup
print("[1/5] Creating MPM solver...")
mpm = MPM2D_Optimized(
    domain_x=(0, 30),
    domain_y=(0, 20),
    nx=60,
    ny=30,
    su=6000,  # 6 kPa
    E=3e6,
    nu=0.495,
    rho=1600,
    use_gimp=False
)

# Add soil
mpm.add_soil_block(
    x_range=(0, 30),
    y_range=(0, 15),
    ppc=4
)

# Add foundation
mpm.add_strip_foundation(
    center_x=15.0,
    y_base=15.0,
    width=5.0,
    thickness=0.5,
    density=2500
)

print(f"   Soil particles: {len([p for p in mpm.particles if p.material_id == 0])}")
print(f"   Foundation particles: {len(mpm.foundation_indices)}")
print(f"   Grid: {mpm.nnx} × {mpm.nny} nodes")
print()

# Run simulation
print("[2/5] Running simulation...")
dt = 0.0001
target = 0.10  # 100mm
rate = 0.10  # m/s
max_steps = 50000

settlements = []
q_v1 = []  # Original method
q_v2 = []  # Grid forces
q_v3 = []  # Thin zone
q_contact = []  # NEW contact method

mpm.foundation_velocity = -rate
step = 0
start_time = time.time()

while step < max_steps:
    mpm.mpm_step(dt)
    step += 1

    # Calculate settlement
    current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])
    if mpm.foundation_y0 is None:
        mpm.foundation_y0 = current_y
    settlement = mpm.foundation_y0 - current_y

    # Record every 1000 steps
    if step % 1000 == 0:
        # Test all 4 methods
        q1 = mpm.calculate_bearing_capacity() / 1000  # v1
        q2 = mpm.calculate_bearing_capacity_v2() / 1000  # v2
        q3 = mpm.calculate_bearing_capacity_v3() / 1000  # v3
        qc = mpm.calculate_bearing_capacity_contact() / 1000  # contact

        settlements.append(settlement)
        q_v1.append(q1)
        q_v2.append(q2)
        q_v3.append(q3)
        q_contact.append(qc)

        elapsed = time.time() - start_time
        print(f"   Step {step:5d} | s={settlement*1000:5.1f}mm | " +
              f"v1={q1:4.0f} | v2={q2:4.0f} | v3={q3:4.0f} | contact={qc:4.0f} kN/m | {elapsed:.0f}s")

    if settlement >= target:
        print(f"   Target {target*1000:.0f}mm reached!")
        break

runtime = time.time() - start_time
print(f"   Runtime: {runtime:.1f}s ({runtime/60:.1f} min)")
print()

# Analysis
print("[3/5] Analyzing results...")
print()

# Expected value
Nc = 5.14  # Prandtl
qu_expected = 6000 * Nc  # Pa
Q_expected = qu_expected * 5.0 / 1000  # kN/m
print(f"Expected capacity (Prandtl): {Q_expected:.0f} kN/m")
print()

# Check last values (plateau)
if len(q_v1) > 5:
    plateau_v1 = np.mean(q_v1[-5:])
    plateau_v2 = np.mean(q_v2[-5:])
    plateau_v3 = np.mean(q_v3[-5:])
    plateau_contact = np.mean(q_contact[-5:])

    print("Plateau values (last 5 points):")
    print(f"   v1 (original):    {plateau_v1:6.1f} kN/m  |  Error: {abs(plateau_v1-Q_expected)/Q_expected*100:5.1f}%")
    print(f"   v2 (grid forces): {plateau_v2:6.1f} kN/m  |  Error: {abs(plateau_v2-Q_expected)/Q_expected*100:5.1f}%")
    print(f"   v3 (thin zone):   {plateau_v3:6.1f} kN/m  |  Error: {abs(plateau_v3-Q_expected)/Q_expected*100:5.1f}%")
    print(f"   contact (NEW):    {plateau_contact:6.1f} kN/m  |  Error: {abs(plateau_contact-Q_expected)/Q_expected*100:5.1f}%")
    print()

    # Verdict
    print("VERDICT:")
    error_contact = abs(plateau_contact - Q_expected) / Q_expected * 100

    if error_contact < 20:
        print(f"   ✅ CONTACT METHOD WORKS! Error = {error_contact:.1f}% (< 20%)")
    elif error_contact < 50:
        print(f"   ⚠️  ACCEPTABLE: Error = {error_contact:.1f}% (20-50%)")
    else:
        print(f"   ❌ CONTACT METHOD FAILED: Error = {error_contact:.1f}% (> 50%)")

    print()

# Plot
print("[4/5] Plotting results...")
settlements_mm = [s*1000 for s in settlements]

plt.figure(figsize=(14, 5))

# Plot 1: All methods
plt.subplot(1, 2, 1)
plt.plot(settlements_mm, q_v1, 'o-', label='v1 (original)', alpha=0.7)
plt.plot(settlements_mm, q_v2, 's-', label='v2 (grid forces)', alpha=0.7)
plt.plot(settlements_mm, q_v3, '^-', label='v3 (thin zone)', alpha=0.7)
plt.plot(settlements_mm, q_contact, 'D-', label='contact (NEW)', linewidth=2, markersize=6)
plt.axhline(Q_expected, color='k', linestyle='--', label=f'Expected ({Q_expected:.0f} kN/m)')
plt.xlabel('Settlement (mm)')
plt.ylabel('Bearing Capacity (kN/m)')
plt.title('Comparison of All Methods')
plt.legend()
plt.grid(True, alpha=0.3)

# Plot 2: Focus on contact method
plt.subplot(1, 2, 2)
plt.plot(settlements_mm, q_contact, 'D-', color='C3', linewidth=2, label='Contact method')
plt.axhline(Q_expected, color='k', linestyle='--', label=f'Expected ({Q_expected:.0f} kN/m)')
plt.axhline(Q_expected * 0.8, color='r', linestyle=':', alpha=0.5, label='±20% bounds')
plt.axhline(Q_expected * 1.2, color='r', linestyle=':', alpha=0.5)
plt.xlabel('Settlement (mm)')
plt.ylabel('Bearing Capacity (kN/m)')
plt.title('Contact Method (Detailed)')
plt.legend()
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('/home/user/A-mat-Journal/contact_method_test.png', dpi=150)
print(f"   Plot saved: contact_method_test.png")
print()

# Summary
print("[5/5] FINAL SUMMARY")
print("="*70)

if error_contact < 20:
    print("✅ SUCCESS: Contact method gives correct bearing capacity!")
    print()
    print("RECOMMENDATION: Update all COLAB scripts to use:")
    print("   q = mpm.calculate_bearing_capacity_contact() / 1000")
    print()
    print("This should give ~154 kN/m for your simulations.")
elif error_contact < 50:
    print("⚠️  PARTIAL SUCCESS: Contact method is better but still has errors.")
    print()
    print(f"Got {plateau_contact:.0f} kN/m, expected {Q_expected:.0f} kN/m")
    print("May need further refinement or consider 3D approach.")
else:
    print("❌ FAILED: Contact method does not work.")
    print()
    print("RECOMMENDATION: Abandon 2D approach, move to 3D implementation")
    print("based on Liu et al. (2022) full geometry.")

print("="*70)
