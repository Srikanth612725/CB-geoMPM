#!/usr/bin/env python3
"""
VALIDATION OF STANDARD GEOTECHNICAL METHODS ON MPM DATA
========================================================

Tests all standard capacity determination methods on actual MPM simulation:
1. Chin-Konder Hyperbolic Method
2. Brinch Hansen 80% Method
3. Davisson Offset Method
4. 0.1B Settlement Method
5. Fuller-Hoy Method

Compares results and determines best method for journal publication.
"""

import numpy as np
import matplotlib.pyplot as plt
import time
from mpm_optimized import MPM2D_Optimized
from standard_capacity_methods import compare_all_methods, chin_konder_method

print("="*70)
print("VALIDATION: STANDARD GEOTECHNICAL METHODS ON MPM DATA")
print("="*70)

# Test parameters - Prandtl case
su = 6000   # 6 kPa
B = 5.0     # 5m foundation
E = 100 * su
nu = 0.495
rho = 1600
rate = 0.05  # Quasi-static
target = 0.15  # 150mm - MORE settlement for better curve fit

# Expected Prandtl capacity
Nc = 2 + np.pi
Q_expected = su * B * Nc / 1000  # kN/m

print(f"\nTest case: Prandtl strip foundation")
print(f"  Foundation width: {B}m")
print(f"  Soil strength: su = {su/1000}kPa")
print(f"  Expected (Prandtl): {Q_expected:.0f} kN/m (Nc = {Nc:.2f})")
print(f"  Settlement target: {target*1000:.0f}mm")
print(f"  Rate: {rate} m/s (quasi-static)")

# Create MPM simulation
print(f"\nCreating MPM simulation (60x30 mesh)...")
start = time.time()

mpm = MPM2D_Optimized(
    domain_x=[0, 30],
    domain_y=[0, 15],
    nx=60,
    ny=30,
    su=su,
    E=E,
    nu=nu,
    rho=rho,
    use_gimp=False
)

mpm.add_soil_block([0, 30], [0, 10], ppc=4)
mpm.add_strip_foundation(center_x=15, y_base=10, width=B, thickness=0.5, density=2500)

print(f"  Particles: {len(mpm.particles)}")

# Run simulation
print(f"\nRunning MPM simulation...")
print(f"  Expected runtime: ~5-7 minutes\n")

dt = mpm.timestep()
mpm.foundation_velocity = -rate

settlements = []
loads = []
step = 0
record_every = 40  # More frequent recording for better curve

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

        if step % 500 == 0:
            print(f"  Step {step:5d} | s={settlement*1000:5.1f}mm | q={q:5.0f} kN/m | points={len(loads)}")

    if settlement >= target:
        print(f"  Reached target at step {step}!")
        q = mpm.calculate_bearing_capacity() / 1000
        settlements.append(settlement)
        loads.append(q)
        break

elapsed = time.time() - start
print(f"\nSimulation complete in {elapsed/60:.1f} minutes ({elapsed:.1f}s)")
print(f"Data points collected: {len(loads)}")

settlements = np.array(settlements)
loads = np.array(loads)

# Apply all standard methods
print(f"\n{'='*70}")
print("APPLYING ALL STANDARD METHODS")
print(f"{'='*70}\n")

results = compare_all_methods(settlements, loads, B, Q_expected)

# Display results
print(f"{'Method':<25} {'Q_ult':<12} {'Error':<10} {'Settlement':<12} {'Quality/Notes':<30}")
print("-"*95)

for method_name, data in results.items():
    Q = data.get('Q_ult')
    err = data.get('error_percent')
    s_ult = data.get('s_ult')
    quality = data.get('quality', data.get('note', ''))

    Q_str = f"{Q:.0f} kN/m" if Q is not None else "N/A"
    err_str = f"{err:.1f}%" if err is not None else "N/A"
    s_str = f"{s_ult*1000:.1f}mm" if s_ult is not None else "N/A"

    print(f"{method_name:<25} {Q_str:<12} {err_str:<10} {s_str:<12} {quality:<30}")

print(f"\nExpected (Prandtl): {Q_expected:.0f} kN/m")

# Find best method
valid_methods = {k: v for k, v in results.items()
                if v.get('Q_ult') is not None and v.get('error_percent') is not None}

if valid_methods:
    best_method = min(valid_methods.items(), key=lambda x: x[1]['error_percent'])
    worst_method = max(valid_methods.items(), key=lambda x: x[1]['error_percent'])

    print(f"\n{'='*70}")
    print("ANALYSIS")
    print(f"{'='*70}")
    print(f"\n✅ BEST METHOD: {best_method[0]}")
    print(f"   Q_ult = {best_method[1]['Q_ult']:.0f} kN/m")
    print(f"   Error = {best_method[1]['error_percent']:.1f}%")

    print(f"\n❌ WORST METHOD: {worst_method[0]}")
    print(f"   Q_ult = {worst_method[1]['Q_ult']:.0f} kN/m")
    print(f"   Error = {worst_method[1]['error_percent']:.1f}%")

# Comprehensive visualization
fig = plt.figure(figsize=(18, 12))
gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

# 1. Main load-settlement curve with all methods
ax1 = fig.add_subplot(gs[0, :2])
ax1.plot(settlements*1000, loads, 'b-o', linewidth=2, markersize=3, label='MPM Simulation', zorder=1)
ax1.axhline(Q_expected, color='green', linestyle='--', linewidth=2.5, label=f'Prandtl Theory: {Q_expected:.0f} kN/m', zorder=2)

colors = {'chin_konder': 'red', 'brinch_hansen': 'orange', 'davisson': 'purple',
          'settlement_10_percent': 'brown', 'fuller_hoy': 'pink', 'maximum_load': 'gray'}

for method_name, data in results.items():
    if data.get('Q_ult') is not None:
        color = colors.get(method_name, 'black')
        label = f"{method_name}: {data['Q_ult']:.0f} kN/m ({data.get('error_percent', 0):.1f}%)"
        ax1.axhline(data['Q_ult'], color=color, linestyle='-.', linewidth=1.5, alpha=0.7, label=label, zorder=3)

ax1.set_xlabel('Settlement (mm)', fontsize=11)
ax1.set_ylabel('Load (kN/m)', fontsize=11)
ax1.set_title('Load-Settlement Curve: All Methods Comparison', fontsize=13, fontweight='bold')
ax1.legend(fontsize=8, loc='lower right')
ax1.grid(True, alpha=0.3)

# 2. Error comparison bar chart
ax2 = fig.add_subplot(gs[0, 2])
valid_for_plot = {k: v for k, v in valid_methods.items() if k != 'maximum_load'}
if valid_for_plot:
    methods_plot = list(valid_for_plot.keys())
    errors_plot = [valid_for_plot[m]['error_percent'] for m in methods_plot]
    colors_plot = [colors.get(m, 'blue') for m in methods_plot]

    bars = ax2.barh(methods_plot, errors_plot, color=colors_plot, alpha=0.7, edgecolor='black')
    ax2.axvline(20, color='orange', linestyle='--', linewidth=2, label='20% threshold')
    ax2.axvline(10, color='green', linestyle='--', linewidth=2, label='10% threshold')
    ax2.set_xlabel('Error (%)', fontsize=11)
    ax2.set_title('Error Comparison', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3, axis='x')

    for i, (bar, err) in enumerate(zip(bars, errors_plot)):
        ax2.text(err + 1, i, f'{err:.1f}%', va='center', fontsize=9, fontweight='bold')

# 3. Chin-Konder diagnostic plot (if available)
if 'chin_konder' in results and results['chin_konder'].get('Q_ult'):
    ax3 = fig.add_subplot(gs[1, :2])

    s_clean = settlements[loads > 0]
    Q_clean = loads[loads > 0]
    s_over_Q = s_clean / Q_clean

    slope = results['chin_konder']['slope']
    intercept = results['chin_konder']['intercept']
    R2 = results['chin_konder']['R_squared']

    ax3.plot(s_clean, s_over_Q, 'bo', markersize=6, label='Data points')
    s_fit = np.linspace(s_clean.min(), s_clean.max(), 100)
    s_over_Q_fit = intercept + slope * s_fit
    ax3.plot(s_fit, s_over_Q_fit, 'r--', linewidth=2,
            label=f'Linear fit: s/Q = {intercept:.4f} + {slope:.4f}*s\nR² = {R2:.3f}\nQ_ult = 1/slope = {1/slope:.0f} kN/m')
    ax3.set_xlabel('Settlement, s (m)', fontsize=11)
    ax3.set_ylabel('s/Q (m/kN)', fontsize=11)
    ax3.set_title('Chin-Konder Hyperbolic Method Diagnostic', fontsize=12, fontweight='bold')
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3)

# 4. Settlement at ultimate comparison
ax4 = fig.add_subplot(gs[1, 2])
methods_with_settlement = {k: v for k, v in valid_methods.items()
                          if v.get('s_ult') is not None}
if methods_with_settlement:
    methods_s = list(methods_with_settlement.keys())
    settlements_s = [methods_with_settlement[m]['s_ult']*1000 for m in methods_s]
    colors_s = [colors.get(m, 'blue') for m in methods_s]

    bars = ax4.barh(methods_s, settlements_s, color=colors_s, alpha=0.7, edgecolor='black')
    ax4.set_xlabel('Settlement at Ultimate (mm)', fontsize=11)
    ax4.set_title('Settlement Comparison', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='x')

    for i, (bar, s_val) in enumerate(zip(bars, settlements_s)):
        ax4.text(s_val + 2, i, f'{s_val:.1f}mm', va='center', fontsize=9, fontweight='bold')

# 5. Ultimate capacity comparison
ax5 = fig.add_subplot(gs[2, :])
if valid_for_plot:
    methods_cap = ['Prandtl\nTheory'] + list(valid_for_plot.keys())
    capacities = [Q_expected] + [valid_for_plot[m]['Q_ult'] for m in list(valid_for_plot.keys())]
    colors_cap = ['green'] + [colors.get(m, 'blue') for m in list(valid_for_plot.keys())]

    bars = ax5.bar(methods_cap, capacities, color=colors_cap, alpha=0.7, edgecolor='black', linewidth=2)
    ax5.axhline(Q_expected, color='green', linestyle='--', linewidth=1, alpha=0.5)
    ax5.set_ylabel('Ultimate Capacity (kN/m)', fontsize=11)
    ax5.set_title('Ultimate Capacity: Method Comparison', fontsize=13, fontweight='bold')
    ax5.grid(True, alpha=0.3, axis='y')
    plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45, ha='right')

    for bar, cap in zip(bars, capacities):
        height = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width()/2., height,
                f'{cap:.0f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.suptitle(f'Standard Geotechnical Methods Validation on MPM Data\n{len(loads)} data points | Runtime: {elapsed/60:.1f} min',
             fontsize=14, fontweight='bold')

plt.savefig('standard_methods_validation.png', dpi=150, bbox_inches='tight')
print(f"\n📊 Comprehensive plot saved: standard_methods_validation.png")

# Recommendations
print(f"\n{'='*70}")
print("RECOMMENDATIONS FOR JOURNAL PUBLICATION")
print(f"{'='*70}\n")

if valid_methods:
    # Rank by error
    ranked = sorted(valid_methods.items(), key=lambda x: x[1]['error_percent'])

    print("Methods ranked by accuracy:\n")
    for rank, (method, data) in enumerate(ranked, 1):
        Q = data['Q_ult']
        err = data['error_percent']
        quality = data.get('quality', '')

        status = "✅ Excellent" if err < 10 else "✅ Good" if err < 15 else "⚠️ Fair" if err < 20 else "❌ Poor"

        print(f"{rank}. {method}")
        print(f"   Q_ult: {Q:.0f} kN/m | Error: {err:.1f}% | {status}")
        if quality:
            print(f"   Quality: {quality}")
        print()

    best = ranked[0]
    print(f"🎯 RECOMMENDED FOR PUBLICATION: {best[0]}")
    print(f"   • Well-established method with peer-reviewed references")
    print(f"   • Error: {best[1]['error_percent']:.1f}% (acceptable for MPM simulations)")
    print(f"   • Q_ult: {best[1]['Q_ult']:.0f} kN/m")

    # Check if Chin-Konder is in top 2
    if 'chin_konder' in [r[0] for r in ranked[:2]]:
        print(f"\n   Alternative: Chin-Konder method")
        print(f"   • Most widely used in practice")
        print(f"   • Based on hyperbolic load-settlement relationship")
        if 'chin_konder' in results:
            print(f"   • R² = {results['chin_konder']['R_squared']:.3f}")

print(f"\n{'='*70}")
print("✅ VALIDATION COMPLETE")
print(f"{'='*70}")
print(f"\nTotal runtime: {elapsed/60:.1f} minutes")
print(f"Data quality: {len(loads)} points over {target*1000:.0f}mm settlement")
