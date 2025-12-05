#!/usr/bin/env python3
"""
COMPREHENSIVE TANGENT METHOD VALIDATION
========================================

Purpose:
1. Reproduce the original 1957 kN result (max method)
2. Apply tangent method to same simulation
3. Test optimized settlement rates and time steps
4. Compare all approaches

Original result: 1957 kN with 22% error (max method)
Target: 2522 kN (Liu et al.)
"""

import numpy as np
import matplotlib.pyplot as plt
import time
from mpm_optimized import MPM2D_Optimized
from tangent_method import tangent_intersection_method

# Liu et al. reference data
LIU_DATA = {
    'foundation_area': 68.4,      # m^2
    'foundation_length': 10.0,    # m
    'foundation_width': 10.0,     # m
    'soil_strength_su': 30000,    # Pa (30 kPa)
    'soil_density': 1600,         # kg/m^3
    'ultimate_load_test': 2522,   # kN
    'ultimate_load_FEM': 2524,    # kN
}

EQUIVALENT_WIDTH = 6.84  # m (Area/Length = 68.4/10)

print("="*80)
print("COMPREHENSIVE TANGENT METHOD VALIDATION")
print("="*80)
print(f"\nTarget: Liu et al. = {LIU_DATA['ultimate_load_test']} kN")
print(f"Previous result (max method): 1957 kN (22% error)")
print(f"\nGoal: Test if tangent method reduces error")

# ============================================================================
# TEST 1: ORIGINAL PARAMETERS (Reproduce 1957 kN result)
# ============================================================================

def run_simulation(su, width, rate, target, nx, ny, test_name):
    """Run MPM simulation and return results with both methods"""

    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")
    print(f"Parameters:")
    print(f"  su = {su/1000:.0f} kPa")
    print(f"  width = {width} m")
    print(f"  settlement rate = {rate} m/s")
    print(f"  target settlement = {target*1000:.0f} mm")
    print(f"  mesh = {nx} x {ny}")

    # Quasi-static check
    rho = 1600
    inertial_ratio = (rho * rate**2) / su
    qs_status = "✅ Quasi-static" if inertial_ratio < 0.01 else "⚠️ Dynamic effects"
    print(f"  Inertial/Strength ratio = {inertial_ratio:.6f} {qs_status}")

    # Estimate time
    dt = 0.0006  # typical timestep
    time_real = target / rate
    num_steps = int(time_real / dt)
    print(f"  Expected steps: ~{num_steps:,}")
    print(f"  Expected runtime: ~{num_steps*0.01/60:.1f} minutes")

    # Create MPM solver
    E = 100 * su
    nu = 0.495

    mpm = MPM2D_Optimized(
        domain_x=[0, 40],
        domain_y=[0, 20],
        nx=nx,
        ny=ny,
        su=su,
        E=E,
        nu=nu,
        rho=rho,
        use_gimp=False  # Standard MPM (verified correct)
    )

    # Add soil
    mpm.add_soil_block([0, 40], [0, 15], ppc=4)

    # Add foundation (centered at x=20)
    mpm.add_strip_foundation(
        center_x=20,
        y_base=15,
        width=width,
        thickness=0.5,
        density=2500
    )

    print(f"\nSetup complete:")
    print(f"  Total particles: {len(mpm.particles)}")
    print(f"  Foundation particles: {len(mpm.foundation_indices)}")

    # Run simulation
    print(f"\nRunning simulation...")
    start_time = time.time()

    dt = mpm.timestep()
    mpm.foundation_velocity = -rate

    settlements = []
    loads = []
    step = 0
    max_steps = num_steps + 5000  # Add buffer
    interval = 0.02  # Record every 20mm
    last_recorded = -interval

    while step < max_steps:
        mpm.mpm_step(dt)
        step += 1

        # Calculate current settlement
        current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])
        settlement = mpm.foundation_y0 - current_y

        # Record data at intervals
        if settlement - last_recorded >= interval:
            q = mpm.calculate_bearing_capacity() / 1000  # kN/m
            settlements.append(settlement)
            loads.append(q)
            last_recorded = settlement

            if step % 1000 == 0:
                print(f"  Step {step:6d} | s={settlement*1000:5.1f}mm | q={q:6.0f} kN/m")

        # Check if target reached
        if settlement >= target:
            print(f"  Reached target settlement: {settlement*1000:.1f}mm")
            break

    elapsed = time.time() - start_time
    print(f"\nSimulation complete in {elapsed/60:.1f} minutes ({elapsed:.0f}s)")

    settlements = np.array(settlements)
    loads = np.array(loads)

    # METHOD 1: Max value (original method)
    Q_max = np.max(loads)
    idx_max = np.argmax(loads)
    s_max = settlements[idx_max]
    error_max = abs(Q_max - LIU_DATA['ultimate_load_test']) / LIU_DATA['ultimate_load_test'] * 100

    # METHOD 2: Tangent intersection (new method)
    tangent_result = tangent_intersection_method(settlements, loads, plot=False)
    Q_tangent = tangent_result['Q_ult']
    s_tangent = tangent_result['s_ult']
    method_used = tangent_result['method']
    error_tangent = abs(Q_tangent - LIU_DATA['ultimate_load_test']) / LIU_DATA['ultimate_load_test'] * 100

    # Results
    print(f"\n{'='*80}")
    print(f"RESULTS: {test_name}")
    print(f"{'='*80}")
    print(f"\nMethod 1: MAX VALUE (original)")
    print(f"  Ultimate load: {Q_max:.0f} kN/m")
    print(f"  Settlement: {s_max*1000:.1f} mm")
    print(f"  Error vs Liu: {error_max:.1f}%")

    print(f"\nMethod 2: TANGENT INTERSECTION (new)")
    print(f"  Ultimate load: {Q_tangent:.0f} kN/m")
    print(f"  Settlement: {s_tangent*1000:.1f} mm")
    print(f"  Method used: {method_used}")
    print(f"  Error vs Liu: {error_tangent:.1f}%")

    improvement = error_max - error_tangent
    print(f"\nIMPROVEMENT:")
    print(f"  Error reduction: {improvement:.1f} percentage points")
    if improvement > 5:
        print(f"  Status: ✅ SIGNIFICANT IMPROVEMENT!")
    elif improvement > 0:
        print(f"  Status: ✅ Modest improvement")
    else:
        print(f"  Status: ⚠️ No improvement (tangent method may not apply)")

    return {
        'test_name': test_name,
        'settlements': settlements,
        'loads': loads,
        'Q_max': Q_max,
        'error_max': error_max,
        's_max': s_max,
        'Q_tangent': Q_tangent,
        'error_tangent': error_tangent,
        's_tangent': s_tangent,
        'method': method_used,
        'runtime': elapsed,
        'improvement': improvement
    }

# ============================================================================
# RUN TESTS
# ============================================================================

results = []

# TEST 1: Original parameters (should give ~1957 kN with max method)
print("\n\n")
print("#" * 80)
print("# TEST 1: ORIGINAL PARAMETERS (Reproduce 1957 kN)")
print("#" * 80)

result1 = run_simulation(
    su=30000,
    width=6.84,
    rate=0.01,
    target=0.5,
    nx=80,
    ny=40,
    test_name="Original (slow, 0.01 m/s, 500mm)"
)
results.append(result1)

# TEST 2: Optimized rate (10x faster, still quasi-static)
print("\n\n")
print("#" * 80)
print("# TEST 2: OPTIMIZED RATE (10x faster)")
print("#" * 80)

result2 = run_simulation(
    su=30000,
    width=6.84,
    rate=0.10,
    target=0.15,
    nx=80,
    ny=40,
    test_name="Optimized rate (fast, 0.10 m/s, 150mm)"
)
results.append(result2)

# TEST 3: Super fast (for quick testing)
print("\n\n")
print("#" * 80)
print("# TEST 3: SUPER FAST (For quick validation)")
print("#" * 80)

result3 = run_simulation(
    su=30000,
    width=6.84,
    rate=0.20,
    target=0.10,
    nx=60,
    ny=30,
    test_name="Super fast (0.20 m/s, 100mm, coarse mesh)"
)
results.append(result3)

# ============================================================================
# SUMMARY AND COMPARISON
# ============================================================================

print("\n\n")
print("="*80)
print("SUMMARY: ALL TESTS")
print("="*80)

print(f"\n{'Test':<40} {'Max':<12} {'Tangent':<12} {'Improve':<10} {'Time':<10}")
print("-"*80)

for r in results:
    print(f"{r['test_name']:<40} {r['error_max']:>6.1f}%     {r['error_tangent']:>6.1f}%     {r['improvement']:>6.1f}pp    {r['runtime']/60:>6.1f}min")

print("\n" + "="*80)
print("FINDINGS")
print("="*80)

# Key findings
max_improvement = max(r['improvement'] for r in results)
best_test = max(results, key=lambda r: r['improvement'])
fastest_test = min(results, key=lambda r: r['runtime'])

print(f"\n1. TANGENT METHOD EFFECTIVENESS:")
print(f"   Maximum error reduction: {max_improvement:.1f} percentage points")
print(f"   Best test: {best_test['test_name']}")
print(f"   - Max method error: {best_test['error_max']:.1f}%")
print(f"   - Tangent method error: {best_test['error_tangent']:.1f}%")

print(f"\n2. COMPUTATIONAL EFFICIENCY:")
print(f"   Fastest test: {fastest_test['test_name']}")
print(f"   Runtime: {fastest_test['runtime']/60:.1f} minutes")
print(f"   Error: {fastest_test['error_tangent']:.1f}% (tangent method)")

print(f"\n3. RECOMMENDED PARAMETERS FOR PARAMETRIC STUDY:")
# Find best balance of speed and accuracy
for r in results:
    if r['runtime'] < 600 and r['error_tangent'] < 20:  # Under 10 min, reasonable error
        print(f"   Rate: {r['test_name']}")
        print(f"   - Runtime: {r['runtime']/60:.1f} minutes")
        print(f"   - Error: {r['error_tangent']:.1f}%")
        print(f"   - Improvement over max method: {r['improvement']:.1f}pp")
        break

# ============================================================================
# VISUALIZATION
# ============================================================================

print("\n" + "="*80)
print("CREATING VISUALIZATION")
print("="*80)

fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

# Plot load-settlement curves
for idx, r in enumerate(results):
    ax = fig.add_subplot(gs[idx, :2])

    ax.plot(r['settlements']*1000, r['loads'], 'b-', linewidth=2, label='MPM simulation')
    ax.axhline(LIU_DATA['ultimate_load_test'], color='g', linestyle='--', linewidth=2,
               label=f"Liu et al. ({LIU_DATA['ultimate_load_test']} kN)")
    ax.axhline(r['Q_max'], color='r', linestyle=':', linewidth=2,
               label=f"Max method: {r['Q_max']:.0f} kN ({r['error_max']:.1f}% error)")
    ax.axhline(r['Q_tangent'], color='orange', linestyle='-.', linewidth=2,
               label=f"Tangent method: {r['Q_tangent']:.0f} kN ({r['error_tangent']:.1f}% error)")

    ax.set_xlabel('Settlement (mm)', fontsize=10)
    ax.set_ylabel('Load (kN/m)', fontsize=10)
    ax.set_title(f"{r['test_name']}\nImprovement: {r['improvement']:.1f}pp | Runtime: {r['runtime']/60:.1f}min",
                 fontsize=11, fontweight='bold')
    ax.legend(fontsize=9, loc='best')
    ax.grid(True, alpha=0.3)

# Comparison bar chart
ax_comp = fig.add_subplot(gs[:, 2])

x = np.arange(len(results))
width = 0.35

bars1 = ax_comp.bar(x - width/2, [r['error_max'] for r in results], width,
                    label='Max method', color='red', alpha=0.7)
bars2 = ax_comp.bar(x + width/2, [r['error_tangent'] for r in results], width,
                    label='Tangent method', color='orange', alpha=0.7)

ax_comp.axhline(0, color='green', linestyle='--', linewidth=2, label='Target (0% error)')
ax_comp.set_xlabel('Test Number', fontsize=10)
ax_comp.set_ylabel('Error (%)', fontsize=10)
ax_comp.set_title('Error Comparison\nMax vs Tangent Method', fontsize=11, fontweight='bold')
ax_comp.set_xticks(x)
ax_comp.set_xticklabels([f"Test {i+1}" for i in range(len(results))])
ax_comp.legend(fontsize=9)
ax_comp.grid(True, alpha=0.3, axis='y')

# Add value labels on bars
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax_comp.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=8)

plt.suptitle('Comprehensive Tangent Method Validation\nOriginal vs Optimized Parameters',
             fontsize=14, fontweight='bold')

plt.savefig('tangent_method_comprehensive_validation.png', dpi=150, bbox_inches='tight')
print(f"\n✅ Plot saved: tangent_method_comprehensive_validation.png")

plt.show()

print("\n" + "="*80)
print("VALIDATION COMPLETE!")
print("="*80)
print(f"\nKey Takeaways:")
print(f"1. Tangent method {'DOES' if max_improvement > 5 else 'does NOT'} significantly improve accuracy")
print(f"2. Optimized parameters can reduce runtime by {results[0]['runtime']/results[-1]['runtime']:.1f}x")
print(f"3. Best accuracy achieved: {min(r['error_tangent'] for r in results):.1f}% error")
print(f"4. Recommended for parametric study: {fastest_test['test_name']}")
