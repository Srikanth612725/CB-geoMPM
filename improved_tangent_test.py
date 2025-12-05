#!/usr/bin/env python3
"""
IMPROVED TANGENT METHOD TEST
=============================
Enhanced parameters to ensure tangent method can be applied:
- More settlement (120mm instead of 80mm)
- More data points (record every 50 steps instead of 75)
- Fine mesh (60x30 instead of 50x25)
"""

import numpy as np
import matplotlib.pyplot as plt
import time
from mpm_optimized import MPM2D_Optimized
from tangent_method import tangent_intersection_method

print("="*70)
print("IMPROVED TANGENT METHOD TEST")
print("="*70)
print("Enhanced parameters for successful tangent intersection\n")

# Improved parameters
su = 6000   # 6 kPa
B = 5.0     # 5m foundation
E = 100 * su
nu = 0.495
rho = 1600
rate = 0.05  # Good quasi-static rate
target = 0.12  # 120mm - MORE settlement for better curve

print(f"Test parameters:")
print(f"  Foundation: {B}m wide")
print(f"  Soil: su = {su/1000}kPa")
print(f"  Expected (Prandtl): {su * B * (2 + np.pi) / 1000:.0f} kN/m")
print(f"  Rate: {rate} m/s")
print(f"  Target: {target*1000:.0f}mm (INCREASED for better curve)")
print(f"  Mesh: 60x30 (FINER for accuracy)")
print(f"  Data points: Record every 50 steps (MORE data)")

# QS check
inertial_ratio = (rho * rate**2) / su
print(f"  Inertial/Strength: {inertial_ratio:.6f} ({'✅ QS' if inertial_ratio < 0.01 else '⚠️ Dynamic'})")

print(f"\n  Expected runtime: ~4-5 minutes")
print(f"  Expected data points: ~30-40\n")

# Create finer mesh MPM
print("Creating MPM simulation...")
start_total = time.time()

mpm = MPM2D_Optimized(
    domain_x=[0, 30],
    domain_y=[0, 15],
    nx=60,  # FINER mesh
    ny=30,  # FINER mesh
    su=su,
    E=E,
    nu=nu,
    rho=rho,
    use_gimp=False
)

mpm.add_soil_block([0, 30], [0, 10], ppc=4)
mpm.add_strip_foundation(center_x=15, y_base=10, width=B, thickness=0.5, density=2500)

print(f"  Particles: {len(mpm.particles)} (soil: {len(mpm.particles)-len(mpm.foundation_indices)}, foundation: {len(mpm.foundation_indices)})")

# Run simulation
print("\nRunning improved simulation...")
start_sim = time.time()

dt = mpm.timestep()
mpm.foundation_velocity = -rate

settlements = []
loads = []
step = 0
record_every = 50  # RECORD MORE (was 75)

max_steps = int(target / rate / dt) + 1000

while step < max_steps:
    mpm.mpm_step(dt)
    step += 1

    current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])
    settlement = mpm.foundation_y0 - current_y

    if step % record_every == 0:
        q = mpm.calculate_bearing_capacity() / 1000
        settlements.append(settlement)
        loads.append(q)

        if step % 400 == 0:
            print(f"  Step {step:4d} | s={settlement*1000:5.1f}mm | q={q:5.0f} kN/m | points={len(loads)}")

    if settlement >= target:
        print(f"  Reached target at step {step}!")
        q = mpm.calculate_bearing_capacity() / 1000
        settlements.append(settlement)
        loads.append(q)
        break

elapsed_sim = time.time() - start_sim
print(f"\nSimulation complete in {elapsed_sim/60:.1f} minutes ({elapsed_sim:.1f}s)")

settlements = np.array(settlements)
loads = np.array(loads)

print(f"Data points collected: {len(loads)}")

if len(loads) == 0 or np.max(loads) == 0:
    print("\n❌ ERROR: No valid load data!")
    exit(1)

# Expected capacity
Q_expected = su * B * (2 + np.pi) / 1000

# Compare methods
print(f"\n{'='*70}")
print("COMPARING MAX vs TANGENT METHODS")
print(f"{'='*70}")

# Method 1: MAX
Q_max = np.max(loads)
idx_max = np.argmax(loads)
s_max = settlements[idx_max]
error_max = abs(Q_max - Q_expected) / Q_expected * 100

print(f"\n1. MAX METHOD (baseline):")
print(f"   Ultimate load: {Q_max:.0f} kN/m")
print(f"   At settlement: {s_max*1000:.1f} mm")
print(f"   Error vs Prandtl: {error_max:.1f}%")

# Method 2: TANGENT
result = tangent_intersection_method(settlements, loads, plot=False)
Q_tangent = result['Q_ult']
s_tangent = result['s_ult']
method = result['method']
error_tangent = abs(Q_tangent - Q_expected) / Q_expected * 100

print(f"\n2. TANGENT METHOD:")
print(f"   Ultimate load: {Q_tangent:.0f} kN/m")
print(f"   At settlement: {s_tangent*1000:.1f} mm")
print(f"   Method used: {method}")
print(f"   Error vs Prandtl: {error_tangent:.1f}%")

if method == 'tangent_intersection':
    print(f"   ✅ TANGENT SUCCESSFULLY APPLIED!")
    print(f"   Initial slope: {result['initial_slope']:.0f} kN/m²")
    print(f"   Final slope: {result['final_slope']:.0f} kN/m²")
    print(f"   R² initial: {result['r_initial']**2:.3f}")
    print(f"   R² final: {result['r_final']**2:.3f}")

improvement = error_max - error_tangent

print(f"\n{'='*70}")
print("RESULTS SUMMARY")
print(f"{'='*70}")
print(f"Expected (Prandtl theory): {Q_expected:.0f} kN/m")
print(f"MAX method result:         {Q_max:.0f} kN/m  ({error_max:.1f}% error)")
print(f"TANGENT method result:     {Q_tangent:.0f} kN/m  ({error_tangent:.1f}% error)")
print(f"\nImprovement: {improvement:+.1f} percentage points")

# Comprehensive visualization
fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)

# 1. Full load-settlement curve
ax1 = fig.add_subplot(gs[0, :2])
ax1.plot(settlements*1000, loads, 'b-o', linewidth=2, markersize=4, label='MPM simulation')
ax1.axhline(Q_expected, color='g', linestyle='--', linewidth=2, label=f'Expected: {Q_expected:.0f} kN/m')
ax1.axhline(Q_max, color='r', linestyle=':', linewidth=2, alpha=0.7, label=f'Max: {Q_max:.0f} kN/m')
if method == 'tangent_intersection':
    ax1.axhline(Q_tangent, color='orange', linestyle='-.', linewidth=2, label=f'Tangent: {Q_tangent:.0f} kN/m')
ax1.set_xlabel('Settlement (mm)', fontsize=11)
ax1.set_ylabel('Load (kN/m)', fontsize=11)
ax1.set_title('Load-Settlement Curve with Method Comparison', fontsize=12, fontweight='bold')
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3)

# 2. Method comparison bars
ax2 = fig.add_subplot(gs[0, 2])
methods_list = ['Expected', 'MAX', 'TANGENT']
values = [Q_expected, Q_max, Q_tangent]
errors = [0, error_max, error_tangent]
colors = ['green', 'red', 'orange']

bars = ax2.bar(methods_list, values, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
ax2.axhline(Q_expected, color='g', linestyle='--', alpha=0.5)
ax2.set_ylabel('Ultimate Load (kN/m)', fontsize=11)
ax2.set_title(f'Method Comparison\nImprovement: {improvement:+.1f}pp', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')

for bar, val, err in zip(bars, values, errors):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
            f'{val:.0f} kN\n({err:.1f}%)', ha='center', va='bottom', fontsize=9)

# 3. Error comparison
ax3 = fig.add_subplot(gs[1, 0])
error_methods = ['MAX\nMethod', 'TANGENT\nMethod']
error_vals = [error_max, error_tangent]
error_colors = ['red', 'orange']

bars = ax3.bar(error_methods, error_vals, color=error_colors, alpha=0.7, edgecolor='black', linewidth=2)
ax3.axhline(22, color='purple', linestyle='--', linewidth=2, label='Original baseline: 22%')
ax3.axhline(0, color='g', linestyle='--', linewidth=1)
ax3.set_ylabel('Error (%)', fontsize=11)
ax3.set_title('Error Analysis', fontsize=12, fontweight='bold')
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')

for bar, val in zip(bars, error_vals):
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
            f'{val:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

# 4. Settlement comparison
ax4 = fig.add_subplot(gs[1, 1])
settlement_methods = ['MAX', 'TANGENT']
settlement_vals = [s_max*1000, s_tangent*1000]

bars = ax4.bar(settlement_methods, settlement_vals, color=['red', 'orange'],
               alpha=0.7, edgecolor='black', linewidth=2)
ax4.set_ylabel('Settlement at Ultimate (mm)', fontsize=11)
ax4.set_title('Settlement Comparison', fontsize=12, fontweight='bold')
ax4.grid(True, alpha=0.3, axis='y')

for bar, val in zip(bars, settlement_vals):
    height = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2., height,
            f'{val:.1f}mm', ha='center', va='bottom', fontsize=11, fontweight='bold')

# 5. Load development over time
ax5 = fig.add_subplot(gs[1, 2])
ax5.plot(settlements*1000, loads, 'b-o', markersize=3, label='Load progression')
ax5.fill_between(settlements*1000, 0, loads, alpha=0.3)
ax5.set_xlabel('Settlement (mm)', fontsize=10)
ax5.set_ylabel('Load (kN/m)', fontsize=10)
ax5.set_title('Load Development', fontsize=12, fontweight='bold')
ax5.grid(True, alpha=0.3)

plt.suptitle(f'Improved Tangent Method Test Results\nMethod: {method} | Data points: {len(loads)} | Runtime: {elapsed_sim/60:.1f}min',
             fontsize=14, fontweight='bold')

plt.savefig('improved_tangent_test_results.png', dpi=150, bbox_inches='tight')
print(f"\n📊 Plot saved: improved_tangent_test_results.png")

elapsed_total = time.time() - start_total
print(f"\n⏱️  Total time: {elapsed_total/60:.1f} minutes ({elapsed_total:.1f}s)")

# Guidance
print(f"\n{'='*70}")
print("FINAL ASSESSMENT")
print(f"{'='*70}")

if method == 'tangent_intersection':
    if improvement > 5:
        print(f"\n🎯 EXCELLENT! Tangent method SIGNIFICANTLY improves accuracy")
        print(f"   ✅ Error reduced from {error_max:.1f}% → {error_tangent:.1f}%")
        print(f"   ✅ Improvement: {improvement:.1f} percentage points")
        print(f"\n✅ RECOMMENDATION: USE tangent method for all future work")

    elif improvement > 2:
        print(f"\n✅ GOOD! Tangent method provides moderate improvement")
        print(f"   Error reduced from {error_max:.1f}% → {error_tangent:.1f}%")
        print(f"\n✅ RECOMMENDATION: Use tangent method (consistent improvement)")

    elif improvement > -2:
        print(f"\n⚠️  MARGINAL: Tangent method similar to max method")
        print(f"   Error: {error_max:.1f}% (max) vs {error_tangent:.1f}% (tangent)")
        print(f"\n   May use either method - results are similar")

    else:
        print(f"\n⚠️  Max method more accurate for this case")
        print(f"   Error: {error_max:.1f}% (max) vs {error_tangent:.1f}% (tangent)")
        print(f"\n   Tangent method may not suit this load-settlement curve shape")

else:
    print(f"\n❌ Tangent method still fell back to '{method}'")
    print(f"   Despite {len(loads)} data points and {target*1000:.0f}mm settlement")
    print(f"\n   This suggests:")
    print(f"   1. Load-settlement curve doesn't have clear elastic/plastic regions")
    print(f"   2. Prandtl test may not need tangent method")
    print(f"   3. Try with Liu case (more complex geometry)")

print(f"\n✅ IMPROVED TEST COMPLETE")
print(f"{'='*70}")
