#!/usr/bin/env python3
"""
BALANCED TANGENT METHOD TEST
=============================
Balance between speed and accuracy.
Should complete in 2-4 minutes with decent results.
"""

import numpy as np
import matplotlib.pyplot as plt
import time
from mpm_optimized import MPM2D_Optimized
from tangent_method import tangent_intersection_method

print("="*70)
print("BALANCED TANGENT METHOD TEST")
print("="*70)
print("Balanced parameters for reasonable speed + accuracy\n")

# Balanced parameters - Prandtl test
su = 6000   # 6 kPa
B = 5.0     # 5m foundation
E = 100 * su
nu = 0.495
rho = 1600
rate = 0.05  # Moderate speed, still quasi-static
target = 0.08  # 80mm - enough to see failure

# Expected
Nc = 2 + np.pi
Q_expected = su * B * Nc / 1000

print(f"Test parameters:")
print(f"  Foundation: {B}m wide")
print(f"  Soil: su = {su/1000}kPa")
print(f"  Expected (Prandtl): {Q_expected:.0f} kN/m")
print(f"  Rate: {rate} m/s")
print(f"  Target: {target*1000:.0f}mm")
print(f"  Mesh: 50x25 (balanced)")

# QS check
inertial_ratio = (rho * rate**2) / su
print(f"  Inertial/Strength: {inertial_ratio:.6f} ({'✅ QS' if inertial_ratio < 0.01 else '⚠️ Dynamic'})")

# Estimate
dt = 0.0006
time_real = target / rate
num_steps = int(time_real / dt)
print(f"  Expected steps: ~{num_steps:,}")
print(f"  Expected time: ~2-4 minutes\n")

# Create balanced MPM
print("Creating MPM simulation...")
start_total = time.time()

mpm = MPM2D_Optimized(
    domain_x=[0, 30],
    domain_y=[0, 15],
    nx=50,  # Balanced mesh
    ny=25,  # Balanced mesh
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
print("\nRunning balanced simulation...")
start_sim = time.time()

dt = mpm.timestep()
mpm.foundation_velocity = -rate

settlements = []
loads = []
step = 0
record_every = 75  # Record every 75 steps for good curve resolution

while step < num_steps + 1000:
    mpm.mpm_step(dt)
    step += 1

    current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])
    settlement = mpm.foundation_y0 - current_y

    if step % record_every == 0:
        q = mpm.calculate_bearing_capacity() / 1000
        settlements.append(settlement)
        loads.append(q)

        if step % 300 == 0:
            print(f"  Step {step:4d} | s={settlement*1000:4.1f}mm | q={q:5.0f} kN/m")

    if settlement >= target:
        print(f"  Reached target at step {step}!")
        # Record final
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
try:
    result = tangent_intersection_method(settlements, loads, plot=False)
    Q_tangent = result['Q_ult']
    s_tangent = result['s_ult']
    method = result['method']
    error_tangent = abs(Q_tangent - Q_expected) / Q_expected * 100

    print(f"\n2. TANGENT METHOD (new):")
    print(f"   Ultimate load: {Q_tangent:.0f} kN/m")
    print(f"   At settlement: {s_tangent*1000:.1f} mm")
    print(f"   Method used: {method}")
    print(f"   Error vs Prandtl: {error_tangent:.1f}%")

    if method == 'tangent_intersection':
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

    if method == 'tangent_intersection':
        if improvement > 5:
            print("\n✅ SIGNIFICANT IMPROVEMENT!")
            print("   Tangent intersection method successfully reduces error")
            status = "success"
        elif improvement > 2:
            print("\n✅ MODERATE IMPROVEMENT")
            print("   Tangent method shows benefit")
            status = "moderate"
        elif improvement > -2:
            print("\n⚠️  MINIMAL CHANGE")
            print("   Tangent method similar to max")
            status = "similar"
        else:
            print("\n⚠️  WORSE PERFORMANCE")
            print("   Max method more accurate for this case")
            status = "worse"
    else:
        print(f"\n⚠️  Tangent method fell back to '{method}'")
        print("   Need more data points or better curve shape")
        status = "fallback"

except Exception as e:
    print(f"\n❌ Tangent method failed: {e}")
    import traceback
    traceback.print_exc()
    status = "failed"
    improvement = 0

# Visualization
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

# 1. Load-settlement curve
ax1.plot(settlements*1000, loads, 'b-o', linewidth=2, markersize=4, label='MPM simulation')
ax1.axhline(Q_expected, color='g', linestyle='--', linewidth=2, label=f'Expected: {Q_expected:.0f} kN/m')
if 'Q_tangent' in locals():
    ax1.axhline(Q_max, color='r', linestyle=':', linewidth=2, label=f'Max: {Q_max:.0f} kN/m')
    if method == 'tangent_intersection':
        ax1.axhline(Q_tangent, color='orange', linestyle='-.', linewidth=2, label=f'Tangent: {Q_tangent:.0f} kN/m')
ax1.set_xlabel('Settlement (mm)', fontsize=11)
ax1.set_ylabel('Load (kN/m)', fontsize=11)
ax1.set_title('Load-Settlement Curve', fontsize=12, fontweight='bold')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 2. Bar comparison
if 'Q_tangent' in locals():
    methods = ['Expected', 'MAX', 'TANGENT']
    values = [Q_expected, Q_max, Q_tangent]
    errors = [0, error_max, error_tangent]
    colors = ['green', 'red', 'orange']

    bars = ax2.bar(methods, values, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax2.axhline(Q_expected, color='g', linestyle='--', alpha=0.5)
    ax2.set_ylabel('Ultimate Load (kN/m)', fontsize=11)
    ax2.set_title(f'Method Comparison\nImprovement: {improvement:+.1f}pp', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')

    for bar, val, err in zip(bars, values, errors):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.0f} kN\n({err:.1f}%)', ha='center', va='bottom', fontsize=10)

# 3. Error comparison
if 'Q_tangent' in locals():
    error_methods = ['MAX', 'TANGENT']
    error_vals = [error_max, error_tangent]
    error_colors = ['red', 'orange']

    bars = ax3.bar(error_methods, error_vals, color=error_colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax3.axhline(0, color='g', linestyle='--', linewidth=2)
    ax3.set_ylabel('Error (%)', fontsize=11)
    ax3.set_title(f'Error Analysis\nTarget: <20%', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')

    for bar, val in zip(bars, error_vals):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

# 4. Settlement comparison
if 'Q_tangent' in locals():
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

plt.tight_layout()
plt.savefig('balanced_tangent_test_results.png', dpi=150)
print(f"\n📊 Plot saved: balanced_tangent_test_results.png")

elapsed_total = time.time() - start_total
print(f"\n⏱️  Total time: {elapsed_total/60:.1f} minutes ({elapsed_total:.1f}s)")

# Guidance
print(f"\n{'='*70}")
print("INTERPRETATION & NEXT STEPS")
print(f"{'='*70}")

if status == "success":
    print("\n🎯 EXCELLENT RESULTS!")
    print(f"   ✅ Tangent method reduces error by {improvement:.1f} percentage points")
    print(f"   ✅ Accuracy: {error_tangent:.1f}% (vs {error_max:.1f}% with max method)")
    print("\nRecommendations:")
    print("1. ✅ USE tangent method for all future analyses")
    print("2. Test with Liu case (6.84m, 30kPa) to validate on complex geometry")
    print("3. Use these parameters for parametric study:")
    print(f"   - Mesh: 50x25 or finer (60x30)")
    print(f"   - Rate: 0.05 m/s (good quasi-static performance)")
    print(f"   - Target settlement: 80-100mm")
    print("4. Expected parametric study time: ~2-4 min per run")

elif status == "moderate":
    print(f"\n✅ GOOD RESULTS")
    print(f"   Tangent method improves accuracy by {improvement:.1f}pp")
    print("\nRecommendations:")
    print("1. Use tangent method (modest but consistent improvement)")
    print("2. Validate with Liu case")
    print("3. Consider finer mesh (60x30) for better accuracy")

elif status == "fallback":
    print(f"\n⚠️  TANGENT METHOD NOT APPLIED")
    print(f"   Method fell back to '{method}' - insufficient data for tangent")
    print("\nRecommendations:")
    print("1. INCREASE settlement target (try 100-120mm)")
    print("2. RECORD MORE DATA (reduce record_every from 75 to 50)")
    print("3. REFINE MESH (try 60x30 instead of 50x25)")
    print("4. Rerun test with these adjustments")

else:
    print(f"\n⚠️  INCONCLUSIVE")
    print(f"   Error with max method: {error_max:.1f}%")
    print("\nThe high baseline error suggests:")
    print("1. Mesh resolution may be insufficient")
    print("2. Settlement target may be too small")
    print("3. Need to validate simulation setup")
    print("\nRecommendations:")
    print("1. Run with FINER mesh (60x30 or 80x40)")
    print("2. Increase settlement target (100-150mm)")
    print("3. Check against documented 1957 kN result with exact parameters")

print(f"\n{'='*70}")
print("✅ BALANCED TEST COMPLETE")
print(f"{'='*70}")
