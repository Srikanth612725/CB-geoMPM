# Fix for ModuleNotFoundError + Compare All 5 Methods

**Problem**: Cell 1 doesn't download `standard_capacity_methods.py`, causing import error

**Solution**: Updated Cell 1 + New comparison cell

---

## UPDATED CELL 1: Fix Import Error

Replace your current Cell 1 with this:

```python
# Cell 1: Download all required files from GitHub
# ================================================

print("📥 Downloading files from GitHub...")

# Download all Python modules
!wget -q https://raw.githubusercontent.com/Srikanth612725/A-mat-Journal/claude/continue-simulation-evaluation-01NhZKgYb8TuuckLB6HWaKGk/mpm_optimized.py

# ✅ FIX: Add this line to download standard_capacity_methods.py
!wget -q https://raw.githubusercontent.com/Srikanth612725/A-mat-Journal/claude/continue-simulation-evaluation-01NhZKgYb8TuuckLB6HWaKGk/standard_capacity_methods.py

!wget -q https://raw.githubusercontent.com/Srikanth612725/A-mat-Journal/claude/continue-simulation-evaluation-01NhZKgYb8TuuckLB6HWaKGk/smart_parametric_study.py

!wget -q https://raw.githubusercontent.com/Srikanth612725/A-mat-Journal/claude/continue-simulation-evaluation-01NhZKgYb8TuuckLB6HWaKGk/run_parametric_study.py

# Verify all files downloaded
import os
files_needed = ['mpm_optimized.py', 'standard_capacity_methods.py',
                'smart_parametric_study.py', 'run_parametric_study.py']

print("\n✅ Files downloaded:")
for f in files_needed:
    if os.path.exists(f):
        size = os.path.getsize(f) / 1024
        print(f"  ✓ {f} ({size:.1f} KB)")
    else:
        print(f"  ✗ {f} - MISSING!")

# Test import
try:
    from standard_capacity_methods import davisson_offset_method
    print("\n✅ standard_capacity_methods imported successfully!")
except Exception as e:
    print(f"\n❌ Import failed: {e}")
```

---

## NEW CELL: Compare All 5 Methods on TIER 1 Results

Add this as a new cell to analyze your completed TIER 1 runs:

```python
# Cell: Compare All 5 Standard Methods on TIER 1 Results
# =======================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from standard_capacity_methods import compare_all_methods

print("="*70)
print("COMPARING ALL 5 STANDARD METHODS ON TIER 1 RESULTS")
print("="*70)

# Load your TIER 1 results
df_results = pd.read_csv('tier1_results.csv')
print(f"\nLoaded {len(df_results)} TIER 1 runs")
print(f"Columns: {df_results.columns.tolist()}")

# Expected capacity for Prandtl case (su=6kPa, B=5m)
Nc = 2 + np.pi  # Prandtl bearing capacity factor
Q_expected = 6 * 5 * Nc  # kPa * m * Nc = kN/m
print(f"\nExpected (Prandtl theory): {Q_expected:.0f} kN/m")

# Initialize results storage
all_methods_results = []

# Process each run
for idx, row in df_results.iterrows():
    run_id = row['run_id']
    print(f"\n{'='*70}")
    print(f"Processing {run_id}...")

    # Load saved load-settlement data
    data_file = f"{run_id}_data.npz"

    try:
        # Load the saved data
        data = np.load(data_file)
        settlements = data['settlements']
        loads = data['loads']
        width = row['width_m']
        su = row['su_Pa']

        print(f"  Width: {width}m, su: {su/1000:.0f}kPa")
        print(f"  Data points: {len(loads)}")
        print(f"  Settlement range: 0 - {settlements[-1]*1000:.1f}mm")
        print(f"  Load range: {loads[0]:.0f} - {loads[-1]:.0f} kN/m")

        # Apply all 5 standard methods
        results = compare_all_methods(settlements, loads, width, Q_expected)

        # Display results for this run
        print(f"\n  {'Method':<20} {'Q_ult (kN/m)':<15} {'Error (%)':<12}")
        print(f"  {'-'*50}")

        for method_name, data in results.items():
            Q = data.get('Q_ult')
            err = data.get('error_percent')

            if Q is not None:
                Q_str = f"{Q:.0f}"
                err_str = f"{err:.1f}%" if err is not None else "N/A"
                print(f"  {method_name:<20} {Q_str:<15} {err_str:<12}")

                # Store for comparison
                all_methods_results.append({
                    'run_id': run_id,
                    'method': method_name,
                    'Q_ult': Q,
                    'error_percent': err,
                    'width': width,
                    'su': su
                })

    except FileNotFoundError:
        print(f"  ⚠️ Data file not found: {data_file}")
        print(f"  Skipping {run_id}")
        continue
    except Exception as e:
        print(f"  ❌ Error processing {run_id}: {e}")
        continue

# Create comparison dataframe
df_comparison = pd.DataFrame(all_methods_results)

if len(df_comparison) > 0:
    print(f"\n{'='*70}")
    print("SUMMARY: BEST METHOD ACROSS ALL RUNS")
    print(f"{'='*70}\n")

    # Group by method and calculate average error
    method_summary = df_comparison.groupby('method').agg({
        'error_percent': ['mean', 'std', 'min', 'max'],
        'Q_ult': 'mean'
    }).round(1)

    print(method_summary)

    # Find best method (lowest average error)
    avg_errors = df_comparison.groupby('method')['error_percent'].mean().sort_values()

    print(f"\n{'='*70}")
    print("RANKING BY AVERAGE ERROR:")
    print(f"{'='*70}\n")

    for rank, (method, error) in enumerate(avg_errors.items(), 1):
        status = "✅ Excellent" if error < 10 else "✅ Good" if error < 15 else "⚠️ Fair" if error < 20 else "❌ Poor"
        print(f"{rank}. {method:<25} {error:>6.1f}% {status}")

    # Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Plot 1: Error comparison (box plot)
    methods = df_comparison['method'].unique()
    error_data = [df_comparison[df_comparison['method'] == m]['error_percent'].values
                  for m in methods]

    bp = ax1.boxplot(error_data, labels=methods, patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor('lightblue')
    ax1.axhline(10, color='green', linestyle='--', linewidth=2, label='10% threshold')
    ax1.axhline(20, color='orange', linestyle='--', linewidth=2, label='20% threshold')
    ax1.set_ylabel('Error (%)', fontsize=12)
    ax1.set_title('Error Distribution by Method', fontsize=13, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Plot 2: Average Q_ult by method
    avg_capacity = df_comparison.groupby('method')['Q_ult'].mean().sort_values(ascending=False)
    colors = ['green' if m == 'davisson' else 'steelblue' for m in avg_capacity.index]

    bars = ax2.barh(avg_capacity.index, avg_capacity.values, color=colors, alpha=0.7, edgecolor='black')
    ax2.axvline(Q_expected, color='red', linestyle='--', linewidth=2, label=f'Expected: {Q_expected:.0f} kN/m')
    ax2.set_xlabel('Average Q_ult (kN/m)', fontsize=12)
    ax2.set_title('Average Capacity by Method', fontsize=13, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='x')

    for i, (bar, val) in enumerate(zip(bars, avg_capacity.values)):
        ax2.text(val + 5, i, f'{val:.0f}', va='center', fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig('tier1_methods_comparison.png', dpi=150, bbox_inches='tight')
    print(f"\n📊 Comparison plot saved: tier1_methods_comparison.png")

    # Save detailed comparison to CSV
    df_comparison.to_csv('tier1_all_methods_comparison.csv', index=False)
    print(f"📁 Detailed results saved: tier1_all_methods_comparison.csv")

    # Best method recommendation
    best_method = avg_errors.index[0]
    best_error = avg_errors.values[0]

    print(f"\n{'='*70}")
    print("🎯 RECOMMENDATION FOR YOUR PAPER")
    print(f"{'='*70}\n")
    print(f"Best method: {best_method}")
    print(f"Average error: {best_error:.1f}%")
    print(f"\nThis method should be used for all analyses in your journal paper.")

else:
    print("\n⚠️ No data files found!")
    print("Make sure the .npz files from TIER 1 runs are in the same directory.")
    print("\nExpected files:")
    for idx, row in df_results.iterrows():
        print(f"  - {row['run_id']}_data.npz")

print(f"\n{'='*70}")
print("✅ ANALYSIS COMPLETE")
print(f"{'='*70}")
```

---

## How to Use

### Step 1: Fix Import Error
1. Replace Cell 1 with the updated version above
2. Run Cell 1
3. Verify you see: `✅ standard_capacity_methods imported successfully!`

### Step 2: Compare Methods
1. Add the comparison cell as a new cell
2. Run it to compare all 5 methods on your TIER 1 data
3. Review the ranking and visualization

---

## Expected Output

The comparison cell will:
1. ✅ Load all 12 TIER 1 runs
2. ✅ Apply all 5 methods to each run:
   - Davisson Offset
   - Chin-Konder Hyperbolic
   - Brinch Hansen 80%
   - Fuller-Hoy
   - 0.1B Settlement
3. ✅ Calculate errors vs Prandtl theory
4. ✅ Rank methods by accuracy
5. ✅ Generate visualization comparing methods
6. ✅ Recommend best method for your paper

---

## Troubleshooting

### If Cell 1 Still Fails
```python
# Try manual download
!curl -O https://raw.githubusercontent.com/Srikanth612725/A-mat-Journal/claude/continue-simulation-evaluation-01NhZKgYb8TuuckLB6HWaKGk/standard_capacity_methods.py
```

### If Data Files Not Found
Your TIER 1 runs should have saved files named like:
- `T1_R1_B5.0_su6_data.npz`
- `T1_R2_B5.0_su6_data.npz`
- etc.

Check the downloads folder:
```python
from google.colab import files
import os
os.chdir('/content')  # Or wherever your files are
!ls -lh *.npz
```

---

## What You'll Learn

After running the comparison:
1. **Which method is best** for your MPM simulations
2. **Average errors** for each method across all runs
3. **Consistency** of each method (std deviation)
4. **Visual comparison** of all methods

This will tell you definitively which method to use for your journal paper!

---

## Quick Check: Expected Results from Validation

From previous validation (single run, 60×30, 150mm):
- **Davisson**: 4.5% error ✅ BEST
- **Brinch Hansen**: 46.7% error
- **Fuller-Hoy**: 59.8% error
- **Chin-Konder**: 82.1% error
- **0.1B**: N/A (needs 500mm settlement)

Your TIER 1 results should confirm Davisson as the best method!
