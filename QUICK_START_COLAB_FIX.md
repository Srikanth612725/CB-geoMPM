# Quick Fix: Compare All 5 Methods on Your TIER 1 Results

**Problem**: ModuleNotFoundError for `standard_capacity_methods`

**Solution**: 2 simple steps below

---

## Step 1: Fix Cell 1 (Fix Import Error)

Replace your **Cell 1** with this:

```python
# Cell 1: Download all required files
print("📥 Downloading files from GitHub...")

!wget -q https://raw.githubusercontent.com/Srikanth612725/A-mat-Journal/claude/continue-simulation-evaluation-01NhZKgYb8TuuckLB6HWaKGk/mpm_optimized.py

# ✅ FIX: Download standard_capacity_methods.py
!wget -q https://raw.githubusercontent.com/Srikanth612725/A-mat-Journal/claude/continue-simulation-evaluation-01NhZKgYb8TuuckLB6HWaKGk/standard_capacity_methods.py

!wget -q https://raw.githubusercontent.com/Srikanth612725/A-mat-Journal/claude/continue-simulation-evaluation-01NhZKgYb8TuuckLB6HWaKGk/smart_parametric_study.py

!wget -q https://raw.githubusercontent.com/Srikanth612725/A-mat-Journal/claude/continue-simulation-evaluation-01NhZKgYb8TuuckLB6HWaKGk/run_parametric_study.py

# Verify
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

**Run this cell** and verify you see: `✅ standard_capacity_methods imported successfully!`

---

## Step 2: Add Comparison Cell (Compare All 5 Methods)

**Add this as a NEW cell** to compare all 5 methods on your TIER 1 data:

```python
# Compare All 5 Standard Methods on TIER 1 Results
# =================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from standard_capacity_methods import compare_all_methods

print("="*70)
print("COMPARING ALL 5 STANDARD METHODS ON TIER 1 RESULTS")
print("="*70)

# Load TIER 1 results
try:
    df_results = pd.read_csv('tier1_results.csv')
    print(f"\n✅ Loaded {len(df_results)} TIER 1 runs")
except FileNotFoundError:
    # Try alternative location
    df_results = pd.read_csv('parametric_results/parametric_study_results.csv')
    print(f"\n✅ Loaded {len(df_results)} runs from parametric_results/")

print(f"Columns: {df_results.columns.tolist()}")

# Expected capacity (Prandtl theory)
Nc = 2 + np.pi  # = 5.14
Q_expected_prandtl = 6 * 5 * Nc  # For su=6kPa, B=5m
print(f"\nExpected (Prandtl, su=6kPa, B=5m): {Q_expected_prandtl:.0f} kN/m")

# Process each run
all_methods_results = []
successful = 0

for idx, row in df_results.iterrows():
    run_id = row['run_id']
    print(f"\n{'='*70}")
    print(f"Processing {run_id} ({idx+1}/{len(df_results)})...")

    # Find data file
    possible_files = [
        f"{run_id}_data.csv",
        f"parametric_results/{run_id}_data.csv"
    ]

    data_file = None
    for pf in possible_files:
        if Path(pf).exists():
            data_file = pf
            break

    if data_file is None:
        print(f"  ⚠️ Data file not found")
        continue

    try:
        # Load data
        df_data = pd.read_csv(data_file)
        settlements = df_data['settlement_m'].values
        loads = df_data['load_kN_per_m'].values
        width = row['width_m']
        su = row['su_kPa'] * 1000

        # Expected for this case
        Q_expected = (su / 1000) * width * Nc

        print(f"  Width: {width}m, su: {su/1000:.0f}kPa")
        print(f"  Expected: {Q_expected:.0f} kN/m")
        print(f"  Data points: {len(loads)}")

        # Apply all 5 methods
        results = compare_all_methods(settlements, loads, width, Q_expected)

        # Display results
        print(f"\n  {'Method':<22} {'Q_ult':<15} {'Error':<12} {'Status'}")
        print(f"  {'-'*60}")

        for method_name, data in results.items():
            Q = data.get('Q_ult')
            err = data.get('error_percent')

            if Q is not None:
                status = "✅" if err < 10 else "⚠️" if err < 20 else "❌"
                print(f"  {method_name:<22} {Q:.0f} kN/m{' ':<7} {err:.1f}%{' ':<7} {status}")

                # Store
                all_methods_results.append({
                    'run_id': run_id,
                    'method': method_name,
                    'Q_ult': Q,
                    'error_percent': err,
                    'width': width,
                    'su_kPa': su / 1000
                })

        successful += 1

    except Exception as e:
        print(f"  ❌ Error: {e}")
        continue

print(f"\n{'='*70}")
print(f"Processed: {successful} runs")
print(f"{'='*70}")

# Summary
df_comparison = pd.DataFrame(all_methods_results)

if len(df_comparison) > 0:
    # Rank by average error
    avg_errors = df_comparison.groupby('method')['error_percent'].mean().sort_values()

    print(f"\n{'='*70}")
    print("RANKING BY AVERAGE ERROR:")
    print(f"{'='*70}\n")

    for rank, (method, error) in enumerate(avg_errors.items(), 1):
        std = df_comparison[df_comparison['method'] == method]['error_percent'].std()
        status = "✅ Excellent" if error < 10 else "✅ Good" if error < 15 else "⚠️ Fair" if error < 20 else "❌ Poor"
        print(f"{rank}. {method:<25} {error:>6.1f}% ± {std:>4.1f}% {status}")

    # Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Plot 1: Error box plot
    methods = avg_errors.index.tolist()
    error_data = [df_comparison[df_comparison['method'] == m]['error_percent'].values
                  for m in methods]

    bp = ax1.boxplot(error_data, labels=methods, patch_artist=True)
    for i, patch in enumerate(bp['boxes']):
        if methods[i] == 'davisson':
            patch.set_facecolor('lightgreen')
        else:
            patch.set_facecolor('lightblue')

    ax1.axhline(10, color='green', linestyle='--', linewidth=2, label='10% threshold')
    ax1.axhline(20, color='orange', linestyle='--', linewidth=2, label='20% threshold')
    ax1.set_ylabel('Error (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Error Distribution by Method', fontsize=13, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Plot 2: Average Q_ult
    avg_capacity = df_comparison.groupby('method')['Q_ult'].mean().sort_values(ascending=False)
    colors = ['lightgreen' if m == 'davisson' else 'steelblue' for m in avg_capacity.index]

    bars = ax2.barh(avg_capacity.index, avg_capacity.values, color=colors, alpha=0.7, edgecolor='black')
    ax2.axvline(Q_expected_prandtl, color='red', linestyle='--', linewidth=2,
                label=f'Expected: {Q_expected_prandtl:.0f} kN/m')
    ax2.set_xlabel('Average Q_ult (kN/m)', fontsize=12, fontweight='bold')
    ax2.set_title('Average Capacity by Method', fontsize=13, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='x')

    for i, (bar, val) in enumerate(zip(bars, avg_capacity.values)):
        ax2.text(val + 5, i, f'{val:.0f}', va='center', fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig('tier1_methods_comparison.png', dpi=150, bbox_inches='tight')
    print(f"\n📊 Comparison plot saved: tier1_methods_comparison.png")

    # Save CSV
    df_comparison.to_csv('tier1_all_methods_comparison.csv', index=False)
    print(f"📁 Detailed results saved: tier1_all_methods_comparison.csv")

    # Recommendation
    best_method = avg_errors.index[0]
    best_error = avg_errors.values[0]

    print(f"\n{'='*70}")
    print("🎯 RECOMMENDATION FOR YOUR PAPER")
    print(f"{'='*70}\n")
    print(f"Best method: {best_method}")
    print(f"Average error: {best_error:.1f}%")
    print(f"\nUse this method for all analyses in your journal paper.")

else:
    print("\n⚠️ No data processed! Check file locations.")

print(f"\n{'='*70}")
print("✅ ANALYSIS COMPLETE")
print(f"{'='*70}")
```

---

## What You'll Get

After running Step 2, you'll see:

1. **Ranking** of all 5 methods by accuracy
2. **Visualization** comparing error distributions
3. **CSV file** with detailed results
4. **Recommendation** for which method to use in your paper

---

## Expected Results

Based on previous validation, you should see:

| Rank | Method | Expected Error |
|------|--------|----------------|
| 1 🥇 | Davisson Offset | ~4-10% ✅ |
| 2 | Brinch Hansen | ~40-50% |
| 3 | Fuller-Hoy | ~50-60% |
| 4 | Chin-Konder | ~70-90% |
| 5 | 0.1B | N/A (needs 500mm) |

**Davisson should win by a large margin!**

---

## Troubleshooting

### If files not found:
```python
# Check what files you have
!ls -lh *.csv
!ls -lh *_data.csv
```

### If wrong directory:
```python
# List all CSV files
import os
csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
print(csv_files)
```

### If data in downloads:
```python
# Move to downloads folder
import os
os.chdir('/content')  # or wherever your files are
```

---

## Why This Matters

Your TIER 1 results show Q_ult ≈ 320 kN/m, but expected is ~154 kN/m.

This comparison will tell you:
- **Do all methods give the same error?** → Problem with simulation
- **Does Davisson still perform best?** → Validates method choice
- **What's the actual accuracy?** → Determines if results are usable

---

## Next Steps After Comparison

1. **If Davisson error is still <10%**: ✅ Proceed with confidence
2. **If all methods show high error**: Need to investigate simulation setup
3. **If other method is better**: Switch to that method

The comparison will give you definitive answers!

---

**Ready to proceed?** Run Step 1, then Step 2, and you'll have your answer in ~1 minute!
