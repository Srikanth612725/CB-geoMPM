#!/usr/bin/env python3
"""
ULTRA-FAST TANGENT TEST
=======================
Absolute minimum parameters for fastest possible test
to at least validate if tangent method helps at all.
"""

import numpy as np
import matplotlib.pyplot as plt
import time
from mpm_optimized import MPM2D_Optimized
from tangent_method import tangent_intersection_method

print("="*70)
print("ULTRA-FAST TANGENT METHOD TEST")
print("="*70)
print("Using minimal parameters for 30-60 second completion\n")

# Minimal Prandtl test parameters
su = 10000  # 10 kPa (easier than 30 kPa)
B = 3.0     # 3m foundation (smaller)
E = 100 * su
nu = 0.495
rho = 1600
rate = 0.08  # Fast but still quasi-static
target = 0.04  # Only 40mm settlement

# Expected
Nc = 2 + np.pi
Q_expected = su * B * Nc / 1000
print(f"Test parameters:")
print(f"  Foundation: {B}m wide")
print(f"  Soil: su = {su/1000}kPa")
print(f"  Expected (Prandtl): {Q_expected:.0f} kN/m")
print(f"  Rate: {rate} m/s")
print(f"  Target: {target*1000:.0f}mm")

# QS check
inertial_ratio = (rho * rate**2) / su
print(f"  Inertial/Strength: {inertial_ratio:.6f} ({'✅ QS' if inertial_ratio < 0.01 else '⚠️ Dynamic'})")

# Estimate
dt = 0.0006
time_real = target / rate
num_steps = int(time_real / dt)
print(f"  Expected steps: ~{num_steps:,}")
print(f"  Expected time: ~30-60 seconds\n")

# Create ultra-minimal MPM
print("Creating minimal MPM...")
start_total = time.time()

mpm = MPM2D_Optimized(
    domain_x=[0, 18],  # Smaller domain
    domain_y=[0, 9],   # Smaller domain
    nx=30,  # Very coarse!
    ny=15,  # Very coarse!
    su=su,
    E=E,
    nu=nu,
    rho=rho,
    use_gimp=False
)

mpm.add_soil_block([0, 18], [0, 6], ppc=4)  # Smaller soil block
mpm.add_strip_foundation(center_x=9, y_base=6, width=B, thickness=0.3, density=2500)

print(f"  Particles: {len(mpm.particles)} (soil: {len(mpm.particles)-len(mpm.foundation_indices)}, foundation: {len(mpm.foundation_indices)})")

# Run ultra-fast simulation
print("\nRunning ultra-fast simulation...")
start_sim = time.time()

dt = mpm.timestep()
mpm.foundation_velocity = -rate

settlements = []
loads = []
step = 0
record_every = 50  # Record every 50 steps

while step < num_steps + 500:
    mpm.mpm_step(dt)
    step += 1

    current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])
    settlement = mpm.foundation_y0 - current_y

    if step % record_every == 0:
        q = mpm.calculate_bearing_capacity() / 1000
        settlements.append(settlement)
        loads.append(q)

        if step % 200 == 0:
            print(f"  Step {step:4d} | s={settlement*1000:4.1f}mm | q={q:5.0f} kN/m")

    if settlement >= target:
        print(f"  Reached target at step {step}!")
        # Record final
        q = mpm.calculate_bearing_capacity() / 1000
        settlements.append(settlement)
        loads.append(q)
        break

elapsed_sim = time.time() - start_sim
print(f"\nSimulation complete in {elapsed_sim:.1f}s")

settlements = np.array(settlements)
loads = np.array(loads)

print(f"Data points collected: {len(loads)}")

if len(loads) == 0 or np.max(loads) == 0:
    print("\n❌ ERROR: No valid load data collected!")
    print("   Simulation may have failed or parameters too aggressive")
    exit(1)

# Compare methods
print(f"\n{'='*70}")
print("COMPARING MAX vs TANGENT METHODS")
print(f"{'='*70}")

# Method 1: MAX (old way)
Q_max = np.max(loads)
idx_max = np.argmax(loads)
s_max = settlements[idx_max]
error_max = abs(Q_max - Q_expected) / Q_expected * 100

print(f"\n1. MAX METHOD (baseline):")
print(f"   Ultimate load: {Q_max:.0f} kN/m")
print(f"   At settlement: {s_max*1000:.1f} mm")
print(f"   Error vs Prandtl: {error_max:.1f}%")

# Method 2: TANGENT (new way)
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

    improvement = error_max - error_tangent

    print(f"\n{'='*70}")
    print("RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"Expected (Prandtl theory): {Q_expected:.0f} kN/m")
    print(f"MAX method result:         {Q_max:.0f} kN/m  ({error_max:.1f}% error)")
    print(f"TANGENT method result:     {Q_tangent:.0f} kN/m  ({error_tangent:.1f}% error)")
    print(f"\nImprovement: {improvement:.1f} percentage points")

    if improvement > 5:
        print("\n✅ SIGNIFICANT IMPROVEMENT!")
        print("   Tangent method reduces error by >5 percentage points")
        status = "success"
    elif improvement > 2:
        print("\n✅ MODERATE IMPROVEMENT")
        print("   Tangent method shows some benefit")
        status = "moderate"
    elif improvement > -2:
        print("\n⚠️  MINIMAL CHANGE")
        print("   Tangent method similar to max method")
        status = "similar"
    else:
        print("\n❌ WORSE PERFORMANCE")
        print("   Tangent method gives higher error")
        status = "worse"

except Exception as e:
    print(f"\n❌ Tangent method failed: {e}")
    status = "failed"
    improvement = 0

# Quick plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Load-settlement
ax1.plot(settlements*1000, loads, 'b-', linewidth=2, label='MPM')
ax1.axhline(Q_expected, color='g', linestyle='--', linewidth=2, label=f'Expected: {Q_expected:.0f} kN/m')
if 'Q_tangent' in locals():
    ax1.axhline(Q_max, color='r', linestyle=':', linewidth=2, label=f'Max: {Q_max:.0f} kN/m')
    ax1.axhline(Q_tangent, color='orange', linestyle='-.', linewidth=2, label=f'Tangent: {Q_tangent:.0f} kN/m')
ax1.set_xlabel('Settlement (mm)')
ax1.set_ylabel('Load (kN/m)')
ax1.set_title('Ultra-Fast Test: Load-Settlement')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Bar comparison
if 'Q_tangent' in locals():
    methods = ['Expected', 'MAX', 'TANGENT']
    values = [Q_expected, Q_max, Q_tangent]
    colors = ['green', 'red', 'orange']
    bars = ax2.bar(methods, values, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax2.axhline(Q_expected, color='g', linestyle='--', alpha=0.5)
    ax2.set_ylabel('Ultimate Load (kN/m)')
    ax2.set_title(f'Method Comparison\\nImprovement: {improvement:.1f}pp')
    ax2.grid(True, alpha=0.3, axis='y')

    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.0f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.tight_layout()
plt.savefig('ultra_fast_tangent_test.png', dpi=150)
print(f"\n📊 Plot saved: ultra_fast_tangent_test.png")

elapsed_total = time.time() - start_total
print(f"\n⏱️  Total time: {elapsed_total:.1f}s")

print(f"\n{'='*70}")
print("GUIDANCE FOR NEXT STEPS")
print(f"{'='*70}")

if status == "success":
    print("\n✅ Tangent method is EFFECTIVE!")
    print("\nRecommendations:")
    print("1. Use tangent method for parametric study")
    print("2. Test with Liu case (6.84m, 30kPa) to confirm")
    print("3. Fine-tune mesh resolution for better accuracy")
    print(f"4. Current accuracy ({error_tangent:.1f}%) can likely be improved with:")
    print("   - Finer mesh (current: 30x15, try 60x30 or 80x40)")
    print("   - More settlement (current: 40mm, try 80-100mm)")

elif status == "moderate":
    print("\n⚠️  Tangent method shows modest benefit")
    print("\nRecommendations:")
    print("1. Test with more realistic parameters (Liu case)")
    print("2. Check if improvement holds with finer mesh")
    print("3. May still be worth using for parametric study")

else:
    print("\n⚠️  Tangent method didn't help much in this test")
    print("\nPossible reasons:")
    print("1. Mesh too coarse (30x15) for proper load-settlement curve")
    print("2. Settlement too small (40mm) to capture failure properly")
    print("3. Prandtl test may not need tangent method")
    print("\nRecommendations:")
    print("1. Run test with FINER mesh (60x30)")
    print("2. Run with MORE settlement (80-100mm)")
    print("3. Test on Liu case specifically (more complex geometry)")

print(f"\n{'='*70}")
