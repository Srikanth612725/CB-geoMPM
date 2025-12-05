#!/usr/bin/env python3
"""
Compare original vs optimized MPM implementations
"""

import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Import both implementations
from mpm_validation import run_validation_simulation as run_original, LIU_DATA, EQUIVALENT_WIDTH
from mpm_optimized import run_optimized_validation


def compare_performance_and_accuracy():
    """Run both implementations and compare results"""

    print("="*80)
    print(" MPM IMPLEMENTATION COMPARISON")
    print("="*80)
    print("\nRunning 2 simulations:")
    print("  1. Original MPM (mpm_validation.py)")
    print("  2. Optimized MPM with Numba + GIMP (mpm_optimized.py)")
    print()

    # Common parameters
    params = {
        'su': 6000,
        'width': EQUIVALENT_WIDTH,
        'thickness': 0.5,
        'rate': 0.01,
        'target': 0.5,
        'interval': 0.02,
        'max_steps': 12000,
        'nx': 80,
        'ny': 40,
        'plot_results': False,
    }

    results = {}

    # Run original
    print("\n" + "="*80)
    print("1. ORIGINAL MPM")
    print("="*80)
    t0 = time.time()
    orig = run_original(**params)
    elapsed_orig = time.time() - t0

    if orig and len(orig['loads']) > 0:
        ult_load_orig = np.max(orig['loads'])
        error_orig = abs(ult_load_orig - LIU_DATA['ultimate_load_test']) / LIU_DATA['ultimate_load_test'] * 100

        results['original'] = {
            'time': elapsed_orig,
            'ultimate_load': ult_load_orig,
            'error_pct': error_orig,
            'settlements': orig['settlements'],
            'loads': orig['loads'],
            'times': orig['times'],
        }

        print(f"\n✅ Original MPM Complete!")
        print(f"   Time: {elapsed_orig:.1f}s")
        print(f"   Ultimate load: {ult_load_orig:.0f} kN")
        print(f"   Error: {error_orig:.1f}%")
    else:
        print("❌ Original MPM failed!")
        results['original'] = None

    # Run optimized
    print("\n" + "="*80)
    print("2. OPTIMIZED MPM (Numba + GIMP)")
    print("="*80)
    print("Note: First run includes Numba compilation time (~30s)")
    t0 = time.time()
    opt = run_optimized_validation(**params, use_gimp=True)
    elapsed_opt = time.time() - t0

    if opt:
        results['optimized'] = {
            'time': elapsed_opt,
            'ultimate_load': opt['ultimate_load'],
            'error_pct': opt['error_percent'],
            'settlements': opt['settlements'],
            'loads': opt['loads'],
            'times': opt['times'],
        }

        print(f"\n✅ Optimized MPM Complete!")
        print(f"   Time: {elapsed_opt:.1f}s")
        print(f"   Ultimate load: {opt['ultimate_load']:.0f} kN")
        print(f"   Error: {opt['error_percent']:.1f}%")
    else:
        print("❌ Optimized MPM failed!")
        results['optimized'] = None

    # Summary
    print("\n" + "="*80)
    print(" COMPARISON SUMMARY")
    print("="*80)

    if results['original'] and results['optimized']:
        speedup = elapsed_orig / elapsed_opt
        accuracy_improvement = results['original']['error_pct'] - results['optimized']['error_pct']

        print(f"\n⏱️  PERFORMANCE:")
        print(f"   Original:  {elapsed_orig:.1f}s")
        print(f"   Optimized: {elapsed_opt:.1f}s")
        print(f"   Speedup:   {speedup:.2f}x")

        print(f"\n🎯 ACCURACY:")
        print(f"   Target (Liu et al.):        {LIU_DATA['ultimate_load_test']} kN")
        print(f"   Original MPM:               {results['original']['ultimate_load']:.0f} kN ({results['original']['error_pct']:.1f}% error)")
        print(f"   Optimized MPM:              {results['optimized']['ultimate_load']:.0f} kN ({results['optimized']['error_pct']:.1f}% error)")
        print(f"   Accuracy improvement:       {accuracy_improvement:.1f} percentage points")

        # Create comparison plots
        create_comparison_plots(results)

        print(f"\n📊 Plots saved:")
        print(f"   - comparison_curves.png")
        print(f"   - comparison_summary.png")

        # Save results
        import json
        with open('comparison_results.json', 'w') as f:
            json.dump({
                'original': {
                    'time_s': elapsed_orig,
                    'ultimate_load_kN': float(results['original']['ultimate_load']),
                    'error_pct': float(results['original']['error_pct']),
                },
                'optimized': {
                    'time_s': elapsed_opt,
                    'ultimate_load_kN': float(results['optimized']['ultimate_load']),
                    'error_pct': float(results['optimized']['error_pct']),
                },
                'speedup': float(speedup),
                'accuracy_improvement_pct': float(accuracy_improvement),
            }, f, indent=2)

        print(f"   - comparison_results.json")

    return results


def create_comparison_plots(results):
    """Create comparison visualization"""

    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

    # 1. Load-displacement curves
    ax1 = fig.add_subplot(gs[0, :])

    if results['original']:
        ax1.plot(results['original']['settlements'], results['original']['loads'],
                'b-', lw=2, label='Original MPM', alpha=0.7)

    if results['optimized']:
        ax1.plot(results['optimized']['settlements'], results['optimized']['loads'],
                'r-', lw=2.5, label='Optimized MPM (GIMP)', alpha=0.9)

    ax1.axhline(LIU_DATA['ultimate_load_test'], color='green', ls='--', lw=2,
                label=f"Liu et al. Test ({LIU_DATA['ultimate_load_test']} kN)")
    ax1.axhline(LIU_DATA['ultimate_load_FEM'], color='orange', ls=':', lw=2,
                label=f"Liu et al. FEM ({LIU_DATA['ultimate_load_FEM']} kN)")

    ax1.set_xlabel('Settlement (m)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Load (kN)', fontsize=12, fontweight='bold')
    ax1.set_title('Load-Displacement Curves: Original vs Optimized', fontsize=14, fontweight='bold')
    ax1.legend(loc='lower right', fontsize=11)
    ax1.grid(True, alpha=0.3)

    # 2. Ultimate load comparison
    ax2 = fig.add_subplot(gs[1, 0])

    labels = []
    values = []
    colors = []

    labels.append('Liu et al.\nTest')
    values.append(LIU_DATA['ultimate_load_test'])
    colors.append('green')

    labels.append('Liu et al.\nFEM')
    values.append(LIU_DATA['ultimate_load_FEM'])
    colors.append('orange')

    if results['original']:
        labels.append('Original\nMPM')
        values.append(results['original']['ultimate_load'])
        colors.append('blue')

    if results['optimized']:
        labels.append('Optimized\nMPM')
        values.append(results['optimized']['ultimate_load'])
        colors.append('red')

    bars = ax2.bar(labels, values, color=colors, alpha=0.7, edgecolor='black', linewidth=2)

    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 50,
                f'{int(val)} kN',
                ha='center', va='bottom', fontweight='bold', fontsize=10)

    ax2.set_ylabel('Ultimate Load (kN)', fontsize=12, fontweight='bold')
    ax2.set_title('Ultimate Load Comparison', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.set_ylim(0, max(values) * 1.15)

    # 3. Error and speedup metrics
    ax3 = fig.add_subplot(gs[1, 1])

    if results['original'] and results['optimized']:
        # Error comparison
        metrics = ['Error (%)', 'Time (s)', 'Speedup (x)']

        orig_metrics = [
            results['original']['error_pct'],
            results['original']['time'],
            1.0
        ]

        opt_metrics = [
            results['optimized']['error_pct'],
            results['optimized']['time'],
            results['original']['time'] / results['optimized']['time']
        ]

        x = np.arange(len(metrics))
        width = 0.35

        bars1 = ax3.barh([0], [orig_metrics[0]], width, label='Original', color='blue', alpha=0.7)
        bars2 = ax3.barh([0+width], [opt_metrics[0]], width, label='Optimized', color='red', alpha=0.7)

        ax3.barh([1], [orig_metrics[1]], width, color='blue', alpha=0.7)
        ax3.barh([1+width], [opt_metrics[1]], width, color='red', alpha=0.7)

        ax3.barh([2+width], [opt_metrics[2]], width, color='green', alpha=0.7)

        ax3.set_yticks([0.175, 1.175, 2.175])
        ax3.set_yticklabels(metrics)
        ax3.set_xlabel('Value', fontsize=12, fontweight='bold')
        ax3.set_title('Performance Metrics', fontsize=14, fontweight='bold')
        ax3.legend(loc='best', fontsize=10)
        ax3.grid(True, alpha=0.3, axis='x')

        # Add value labels
        for i, (orig, opt) in enumerate(zip(orig_metrics[:2], opt_metrics[:2])):
            ax3.text(orig + 0.5, i, f'{orig:.1f}', va='center', fontweight='bold', fontsize=9)
            ax3.text(opt + 0.5, i+width, f'{opt:.1f}', va='center', fontweight='bold', fontsize=9)

        ax3.text(opt_metrics[2] + 0.05, 2+width, f'{opt_metrics[2]:.2f}x',
                va='center', fontweight='bold', fontsize=9)

    plt.suptitle('MPM Implementation Comparison', fontsize=16, fontweight='bold', y=0.98)

    plt.savefig('comparison_curves.png', dpi=150, bbox_inches='tight')
    plt.close()

    print("   Saved: comparison_curves.png")


if __name__ == "__main__":
    results = compare_performance_and_accuracy()

    if results['original'] and results['optimized']:
        print("\n" + "="*80)
        print("✅ COMPARISON COMPLETE!")
        print("="*80)

        speedup = results['original']['time'] / results['optimized']['time']
        improvement = results['original']['error_pct'] - results['optimized']['error_pct']

        if speedup > 2.0:
            print(f"\n🚀 EXCELLENT speedup: {speedup:.1f}x faster!")
        elif speedup > 1.5:
            print(f"\n✅ Good speedup: {speedup:.1f}x faster")
        else:
            print(f"\n⚠️  Modest speedup: {speedup:.1f}x (Numba compilation overhead on first run)")

        if improvement > 5:
            print(f"🎯 SIGNIFICANT accuracy improvement: {improvement:.1f} percentage points!")
        elif improvement > 2:
            print(f"✅ Good accuracy improvement: {improvement:.1f} percentage points")
        elif improvement > 0:
            print(f"📊 Slight accuracy improvement: {improvement:.1f} percentage points")
        else:
            print(f"⚠️  No accuracy improvement (may need CPDI or finer mesh)")

        if results['optimized']['error_pct'] < 10:
            print("\n🎉 PUBLISHABLE ACCURACY ACHIEVED! (<10% error)")
        elif results['optimized']['error_pct'] < 15:
            print("\n📝 Good accuracy for preliminary results (<15% error)")
        else:
            print("\n⚠️  Further improvements needed (consider CPDI or mesh refinement)")
