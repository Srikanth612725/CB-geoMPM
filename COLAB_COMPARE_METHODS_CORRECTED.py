#!/usr/bin/env python3
"""
Compare All 5 Standard Methods on TIER 1 Results
=================================================

This cell loads your TIER 1 results and compares all 5 standard methods:
1. Davisson Offset (your current method)
2. Chin-Konder Hyperbolic
3. Brinch Hansen 80%
4. Fuller-Hoy
5. 0.1B Settlement

Works with CSV data files saved from parametric study.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from standard_capacity_methods import compare_all_methods

print("="*70)
print("COMPARING ALL 5 STANDARD METHODS ON TIER 1 RESULTS")
print("="*70)

# Load your TIER 1 results summary
results_file = 'tier1_results.csv'  # Or 'parametric_results/parametric_study_results.csv'

try:
    df_results = pd.read_csv(results_file)
    print(f"\n✅ Loaded {len(df_results)} TIER 1 runs from {results_file}")
except FileNotFoundError:
    # Try alternative location
    results_file = 'parametric_results/parametric_study_results.csv'
    try:
        df_results = pd.read_csv(results_file)
        print(f"\n✅ Loaded {len(df_results)} TIER 1 runs from {results_file}")
    except FileNotFoundError:
        print(f"\n❌ Could not find results file!")
        print("\nTrying to list available CSV files...")
        import os
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
        print(f"CSV files found: {csv_files}")
        if csv_files:
            results_file = csv_files[0]
            df_results = pd.read_csv(results_file)
            print(f"\nUsing: {results_file}")
        else:
            raise FileNotFoundError("No CSV files found!")

print(f"Columns: {df_results.columns.tolist()}")
print(f"\nFirst few runs:")
print(df_results.head())

# Expected capacity for Prandtl case (su=6kPa, B=5m)
Nc = 2 + np.pi  # Prandtl bearing capacity factor = 5.14
Q_expected_prandtl = 6 * 5 * Nc  # kPa * m * Nc = kN/m
print(f"\nExpected (Prandtl theory, su=6kPa, B=5m): {Q_expected_prandtl:.0f} kN/m")

# Initialize results storage
all_methods_results = []
successful_runs = 0
failed_runs = 0

# Process each run
for idx, row in df_results.iterrows():
    run_id = row['run_id']
    print(f"\n{'='*70}")
    print(f"Processing {run_id} ({idx+1}/{len(df_results)})...")

    # Try different possible data file locations
    possible_files = [
        f"{run_id}_data.csv",
        f"parametric_results/{run_id}_data.csv",
        f"downloads/{run_id}_data.csv"
    ]

    data_file = None
    for pf in possible_files:
        if Path(pf).exists():
            data_file = pf
            break

    if data_file is None:
        print(f"  ⚠️ Data file not found. Tried:")
        for pf in possible_files:
            print(f"    - {pf}")
        failed_runs += 1
        continue

    try:
        # Load the saved data (CSV format)
        df_data = pd.read_csv(data_file)
        settlements = df_data['settlement_m'].values
        loads = df_data['load_kN_per_m'].values

        # Get parameters from results
        width = row['width_m']
        su = row['su_kPa'] * 1000  # Convert kPa to Pa

        # Calculate expected capacity for this specific case
        Q_expected = (su / 1000) * width * Nc  # kN/m

        print(f"  Width: {width}m, su: {su/1000:.0f}kPa")
        print(f"  Expected Q_ult: {Q_expected:.0f} kN/m")
        print(f"  Data points: {len(loads)}")
        print(f"  Settlement range: 0 - {settlements[-1]*1000:.1f}mm")
        print(f"  Load range: {loads[0]:.0f} - {loads[-1]:.0f} kN/m")

        # Apply all 5 standard methods
        results = compare_all_methods(settlements, loads, width, Q_expected)

        # Display results for this run
        print(f"\n  {'Method':<22} {'Q_ult (kN/m)':<15} {'Error (%)':<12} {'Status'}")
        print(f"  {'-'*60}")

        for method_name, data in results.items():
            Q = data.get('Q_ult')
            err = data.get('error_percent')

            if Q is not None:
                Q_str = f"{Q:.0f}"
                err_str = f"{err:.1f}" if err is not None else "N/A"

                # Status emoji
                if err is not None:
                    if err < 10:
                        status = "✅ Excellent"
                    elif err < 15:
                        status = "✅ Good"
                    elif err < 20:
                        status = "⚠️ Fair"
                    else:
                        status = "❌ Poor"
                else:
                    status = ""

                print(f"  {method_name:<22} {Q_str:<15} {err_str:<12} {status}")

                # Store for comparison
                all_methods_results.append({
                    'run_id': run_id,
                    'method': method_name,
                    'Q_ult': Q,
                    'Q_expected': Q_expected,
                    'error_percent': err,
                    'width': width,
                    'su_kPa': su / 1000
                })

        successful_runs += 1

    except Exception as e:
        print(f"  ❌ Error processing {run_id}: {e}")
        import traceback
        traceback.print_exc()
        failed_runs += 1
        continue

print(f"\n{'='*70}")
print(f"Processing complete: {successful_runs} successful, {failed_runs} failed")
print(f"{'='*70}")

# Create comparison dataframe
df_comparison = pd.DataFrame(all_methods_results)

if len(df_comparison) > 0:
    print(f"\n{'='*70}")
    print("SUMMARY: METHOD PERFORMANCE ACROSS ALL RUNS")
    print(f"{'='*70}\n")

    # Group by method and calculate statistics
    method_summary = df_comparison.groupby('method').agg({
        'error_percent': ['mean', 'std', 'min', 'max', 'count'],
        'Q_ult': 'mean'
    }).round(1)

    print("Statistical Summary:")
    print(method_summary)

    # Find best method (lowest average error)
    avg_errors = df_comparison.groupby('method')['error_percent'].mean().sort_values()

    print(f"\n{'='*70}")
    print("RANKING BY AVERAGE ERROR:")
    print(f"{'='*70}\n")

    for rank, (method, error) in enumerate(avg_errors.items(), 1):
        status = "✅ Excellent" if error < 10 else "✅ Good" if error < 15 else "⚠️ Fair" if error < 20 else "❌ Poor"

        # Get std for this method
        std = df_comparison[df_comparison['method'] == method]['error_percent'].std()

        print(f"{rank}. {method:<25} {error:>6.1f}% ± {std:>4.1f}% {status}")

    # Create comprehensive visualization
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

    # Plot 1: Error comparison (box plot)
    ax1 = fig.add_subplot(gs[0, 0])
    methods = avg_errors.index.tolist()
    error_data = [df_comparison[df_comparison['method'] == m]['error_percent'].values
                  for m in methods]

    bp = ax1.boxplot(error_data, labels=methods, patch_artist=True)
    for i, patch in enumerate(bp['boxes']):
        if methods[i] == 'davisson':
            patch.set_facecolor('lightgreen')
        else:
            patch.set_facecolor('lightblue')
    ax1.axhline(10, color='green', linestyle='--', linewidth=2, alpha=0.5, label='10% (Excellent)')
    ax1.axhline(20, color='orange', linestyle='--', linewidth=2, alpha=0.5, label='20% (Fair)')
    ax1.set_ylabel('Error (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Error Distribution by Method', fontsize=13, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3, axis='y')
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)

    # Plot 2: Average Q_ult by method
    ax2 = fig.add_subplot(gs[0, 1])
    avg_capacity = df_comparison.groupby('method')['Q_ult'].mean().sort_values(ascending=False)
    colors = ['lightgreen' if m == 'davisson' else 'steelblue' for m in avg_capacity.index]

    bars = ax2.barh(avg_capacity.index, avg_capacity.values, color=colors, alpha=0.7, edgecolor='black')
    avg_expected = df_comparison['Q_expected'].mean()
    ax2.axvline(avg_expected, color='red', linestyle='--', linewidth=2,
                label=f'Avg Expected: {avg_expected:.0f} kN/m')
    ax2.set_xlabel('Average Q_ult (kN/m)', fontsize=12, fontweight='bold')
    ax2.set_title('Average Capacity by Method', fontsize=13, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3, axis='x')

    for i, (bar, val) in enumerate(zip(bars, avg_capacity.values)):
        ax2.text(val + 5, i, f'{val:.0f}', va='center', fontsize=10, fontweight='bold')

    # Plot 3: Error vs Width (to check if width affects accuracy)
    ax3 = fig.add_subplot(gs[1, 0])
    for method in ['davisson', 'chin_konder', 'brinch_hansen', 'fuller_hoy']:
        if method in df_comparison['method'].values:
            df_method = df_comparison[df_comparison['method'] == method]
            ax3.scatter(df_method['width'], df_method['error_percent'],
                       label=method, alpha=0.7, s=80)
    ax3.set_xlabel('Foundation Width (m)', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Error (%)', fontsize=11, fontweight='bold')
    ax3.set_title('Error vs Foundation Width', fontsize=12, fontweight='bold')
    ax3.axhline(10, color='green', linestyle='--', alpha=0.3)
    ax3.axhline(20, color='orange', linestyle='--', alpha=0.3)
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)

    # Plot 4: Error vs su (to check if soil strength affects accuracy)
    ax4 = fig.add_subplot(gs[1, 1])
    for method in ['davisson', 'chin_konder', 'brinch_hansen', 'fuller_hoy']:
        if method in df_comparison['method'].values:
            df_method = df_comparison[df_comparison['method'] == method]
            ax4.scatter(df_method['su_kPa'], df_method['error_percent'],
                       label=method, alpha=0.7, s=80)
    ax4.set_xlabel('Undrained Shear Strength (kPa)', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Error (%)', fontsize=11, fontweight='bold')
    ax4.set_title('Error vs Soil Strength', fontsize=12, fontweight='bold')
    ax4.axhline(10, color='green', linestyle='--', alpha=0.3)
    ax4.axhline(20, color='orange', linestyle='--', alpha=0.3)
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3)

    plt.suptitle(f'Standard Methods Comparison - TIER 1 Results ({successful_runs} runs)',
                 fontsize=14, fontweight='bold')

    plt.savefig('tier1_methods_comparison.png', dpi=150, bbox_inches='tight')
    print(f"\n📊 Comparison plot saved: tier1_methods_comparison.png")

    # Save detailed comparison to CSV
    df_comparison.to_csv('tier1_all_methods_comparison.csv', index=False)
    print(f"📁 Detailed results saved: tier1_all_methods_comparison.csv")

    # Best method recommendation
    best_method = avg_errors.index[0]
    best_error = avg_errors.values[0]
    best_std = df_comparison[df_comparison['method'] == best_method]['error_percent'].std()

    print(f"\n{'='*70}")
    print("🎯 RECOMMENDATION FOR YOUR JOURNAL PAPER")
    print(f"{'='*70}\n")
    print(f"Best method: {best_method}")
    print(f"Average error: {best_error:.1f}% ± {best_std:.1f}%")

    if best_error < 10:
        print(f"✅ EXCELLENT accuracy - highly suitable for journal publication")
    elif best_error < 15:
        print(f"✅ GOOD accuracy - acceptable for journal publication")
    else:
        print(f"⚠️ Accuracy may need improvement for journal publication")

    print(f"\n{'='*70}")
    print("COMPARISON WITH VALIDATION RESULTS")
    print(f"{'='*70}\n")
    print("Previous single validation (60×30, 150mm settlement):")
    print("  Davisson: 4.5% error ✅")
    print("  Brinch Hansen: 46.7% error")
    print("  Fuller-Hoy: 59.8% error")
    print("  Chin-Konder: 82.1% error")
    print("\nYour TIER 1 results:")
    for method, error in avg_errors.items():
        print(f"  {method}: {error:.1f}% error")

else:
    print("\n⚠️ No data successfully processed!")
    print("\nDiagnostics:")
    print("1. Check if data files exist:")
    print("   !ls -lh *_data.csv")
    print("2. Check results file:")
    print(f"   !ls -lh {results_file}")
    print("3. Verify you're in the correct directory")

print(f"\n{'='*70}")
print("✅ ANALYSIS COMPLETE")
print(f"{'='*70}")
