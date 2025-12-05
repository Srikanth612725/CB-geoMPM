"""
OPTIMIZED TIER 1 - CONTACT METHOD (Final Fix)
==============================================

CRITICAL FIXES:
1. Uses calculate_bearing_capacity_contact() - DYNAMIC CONTACT DETECTION
2. Faster penetration: 0.20 m/s (4× faster than before)
3. Larger timestep: 0.0002s (2× larger, stable)
4. Deeper penetration: 500mm target (matches Liu's scale)
5. Non-linear recording: Dense early (every 5mm), sparse later (every 25mm)
6. Diagnostic output: Check for plateau

Contact method finds soil particles currently touching foundation,
uses their stress (where physics happens), adapts as foundation moves.

Expected result: ~154 kN/m with < 20% error
"""

# ============================================================================
# CELL 1: SETUP
# ============================================================================

print("="*70)
print("OPTIMIZED 2D MPM - v3 BEARING CAPACITY METHOD")
print("="*70)
print()

# Standard imports
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
import os
from pathlib import Path

# Check for required files
required_files = [
    'mpm_optimized.py',
    'standard_capacity_methods.py'
]

for fname in required_files:
    if not os.path.exists(fname):
        print(f"❌ ERROR: {fname} not found!")
        print("   Make sure all files are uploaded to Colab")
        raise FileNotFoundError(fname)

print("✅ All imports successful!")
print()

# ============================================================================
# CELL 2: MOUNT GOOGLE DRIVE
# ============================================================================

print("="*70)
print("STEP 1: MOUNTING GOOGLE DRIVE")
print("="*70)

from google.colab import drive
drive.mount('/content/drive')

RESULTS_FOLDER = '/content/drive/MyDrive/MPM_TIER1_Results_v3'
os.makedirs(RESULTS_FOLDER, exist_ok=True)

print("✅ Google Drive mounted!")
print(f"📁 Results folder: {RESULTS_FOLDER}")
print()

# ============================================================================
# CELL 3: LOAD TIER 1 PLAN (OPTIMIZED PARAMETERS)
# ============================================================================

print("="*70)
print("STEP 2: LOADING TIER 1 PLAN (OPTIMIZED)")
print("="*70)

# OPTIMIZED PARAMETERS
plan_data = []
for i in range(3):  # Test with 3 runs first
    plan_data.append({
        'run_id': f'T1v3_R{i+1:02d}_B5.0_su6',
        'su_Pa': 6000,
        'width_m': 5.0,
        'nx': 60,
        'ny': 30,
        'rate_m_per_s': 0.20,  # 4× faster!
        'target_settlement_m': 0.50,  # 5× deeper!
        'dt': 0.0002,  # 2× larger timestep
        'use_gimp': False,
        'record_interval': 100  # Will use non-linear recording
    })

df_plan = pd.DataFrame(plan_data)
print("✅ Created optimized plan: 3 test runs")
print()
print("Plan summary:")
print(df_plan[['run_id', 'su_Pa', 'width_m', 'rate_m_per_s', 'target_settlement_m', 'dt']])
print()

# ============================================================================
# CELL 4: CHECKPOINT
# ============================================================================

print("="*70)
print("STEP 3: CHECKING FOR CHECKPOINT")
print("="*70)

checkpoint_file = os.path.join(RESULTS_FOLDER, 'checkpoint_v3.csv')

if os.path.exists(checkpoint_file):
    df_completed = pd.read_csv(checkpoint_file)

    # Only load SUCCESSFUL runs
    if 'status' in df_completed.columns:
        df_successful = df_completed[df_completed['status'] == 'SUCCESS']
        completed_ids = set(df_successful['run_id'].values)
    else:
        completed_ids = set(df_completed['run_id'].values)

    df_remaining = df_plan[~df_plan['run_id'].isin(completed_ids)]

    print(f"📊 Checkpoint found: {len(completed_ids)} runs completed")
    print(f"   Remaining: {len(df_remaining)} runs")
else:
    df_remaining = df_plan.copy()
    completed_ids = set()
    print("🆕 No checkpoint found - starting fresh")

print()
print(f"📊 Execution plan:")
print(f"   Runs to execute: {len(df_remaining)}")
print(f"   Estimated time: {len(df_remaining) * 30:.0f} min @ 30 min/run (optimized!)")
print()

# ============================================================================
# CELL 5: EXECUTE PARAMETRIC STUDY
# ============================================================================

print("="*70)
print("STEP 4: EXECUTING OPTIMIZED TIER 1 STUDY")
print("="*70)
print()

from mpm_optimized import MPM2D_Optimized
from standard_capacity_methods import (
    davisson_offset_method,
    chin_konder_method,
    brinch_hansen_80_method,
    fuller_hoy_method
)

def non_linear_recording(step, settlement, rate, dt):
    """
    Non-linear recording intervals:
    - 0-20mm: every 1mm (tight spacing for elastic region)
    - 20-100mm: every 5mm
    - 100-200mm: every 10mm
    - 200mm+: every 25mm
    """
    # Calculate step intervals
    step_per_mm = 1.0 / (rate * dt * 1000)  # steps per 1mm

    if settlement < 0.020:  # First 20mm
        return step % int(1.0 * step_per_mm) == 0
    elif settlement < 0.100:  # 20-100mm
        return step % int(5.0 * step_per_mm) == 0
    elif settlement < 0.200:  # 100-200mm
        return step % int(10.0 * step_per_mm) == 0
    else:  # 200mm+
        return step % int(25.0 * step_per_mm) == 0

# Results storage
all_results = []
start_time_total = time.time()

for run_idx, (idx, row) in enumerate(df_remaining.iterrows()):
    elapsed_min = (time.time() - start_time_total) / 60

    print()
    print("#" * 70)
    print(f"# RUN {run_idx+1}/{len(df_remaining)}: {row['run_id']}")
    print(f"# su = {row['su_Pa']/1000:.0f} kPa, width = {row['width_m']:.2f} m")
    print(f"# Rate = {row['rate_m_per_s']:.2f} m/s, Target = {row['target_settlement_m']*1000:.0f}mm")
    print(f"# Elapsed: {elapsed_min:.1f} min")
    print("#" * 70)
    print()

    try:
        # [1/6] Create MPM solver
        print("[1/6] Creating MPM solver...")
        mpm = MPM2D_Optimized(
            domain_x=(0, 30),
            domain_y=(0, 20),
            nx=int(row['nx']),
            ny=int(row['ny']),
            su=row['su_Pa'],
            E=3e6,
            nu=0.495,
            rho=1600,
            use_gimp=row['use_gimp']
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
            width=row['width_m'],
            thickness=0.5,
            density=2500
        )

        print(f"   ✓ Soil: {len([p for p in mpm.particles if p.material_id == 0])} particles")
        print(f"   ✓ Foundation: {len(mpm.foundation_indices)} particles")
        print()

        # [2/6] Run simulation
        print("[2/6] Running MPM simulation (v3 method)...")

        max_steps = 500000  # Much larger limit
        dt = row['dt']
        target = row['target_settlement_m']
        rate = row['rate_m_per_s']

        settlements = []
        loads = []
        step = 0

        mpm.foundation_velocity = -rate

        run_start = time.time()
        last_print_time = run_start

        while step < max_steps:
            mpm.mpm_step(dt)
            step += 1

            # Calculate settlement
            current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])
            if mpm.foundation_y0 is None:
                mpm.foundation_y0 = current_y
            settlement = mpm.foundation_y0 - current_y

            # Non-linear recording
            if non_linear_recording(step, settlement, rate, dt):
                # ✅ USE CONTACT METHOD!
                q = mpm.calculate_bearing_capacity_contact() / 1000  # kN/m

                settlements.append(settlement)
                loads.append(q)

                # Print progress every 5 seconds
                current_time = time.time()
                if current_time - last_print_time >= 5.0:
                    elapsed = current_time - run_start
                    print(f"   Step {step:6d} | s={settlement*1000:6.1f}mm | q={q:6.0f} kN/m | {elapsed:.0f}s")
                    last_print_time = current_time

            # Check if target reached
            if settlement >= target:
                q = mpm.calculate_bearing_capacity_contact() / 1000
                settlements.append(settlement)
                loads.append(q)
                print(f"   ✓ Target {target*1000:.0f}mm reached at step {step}")
                break

        runtime = time.time() - run_start

        settlements = np.array(settlements)
        loads = np.array(loads)

        print(f"   ✓ Complete: {runtime/60:.1f} min, {len(settlements)} data points")
        print()

        # [3/6] Calculate capacity
        print("[3/6] Analyzing capacity...")

        # Check for plateau (should stabilize within ±5%)
        if len(loads) > 10:
            last_10_avg = np.mean(loads[-10:])
            last_10_std = np.std(loads[-10:])
            plateau_variation = (last_10_std / last_10_avg) * 100 if last_10_avg > 0 else 999

            print(f"   Plateau check: Last 10 points avg={last_10_avg:.0f} kN/m, std={last_10_std:.0f} kN/m ({plateau_variation:.1f}%)")

            if plateau_variation < 5:
                print(f"   ✅ GOOD: Plateau reached (variation < 5%)")
            else:
                print(f"   ⚠️  WARNING: No clear plateau (variation {plateau_variation:.1f}% > 5%)")

        # Davisson method
        try:
            result_davisson = davisson_offset_method(settlements, loads, row['width_m'])
            Q_davisson = result_davisson['Q_ult']
            print(f"   ✓ Davisson: {Q_davisson:.0f} kN/m")
        except:
            Q_davisson = np.nan
            print(f"   ✗ Davisson: Failed")

        # Chin-Konder
        try:
            result_ck = chin_konder_method(settlements, loads)
            Q_ck = result_ck['Q_ult']
            print(f"   ✓ Chin-Konder: {Q_ck:.0f} kN/m")
        except:
            Q_ck = np.nan
            print(f"   ✗ Chin-Konder: Failed")

        # Maximum load
        Q_max = np.max(loads)
        print(f"   ✓ Maximum: {Q_max:.0f} kN/m")

        # Expected (Prandtl)
        Nc = 5.14
        qu_expected = row['su_Pa'] * Nc
        Q_expected = qu_expected * row['width_m'] / 1000
        print(f"   → Expected: {Q_expected:.0f} kN/m (Prandtl)")

        # Best estimate
        Q_best = Q_davisson if not np.isnan(Q_davisson) else Q_max
        error_pct = abs(Q_best - Q_expected) / Q_expected * 100

        print(f"   → Best estimate: {Q_best:.0f} kN/m")
        print(f"   → Error: {error_pct:.1f}%")

        if error_pct < 20:
            print(f"   ✅ EXCELLENT: Error < 20%")
        elif error_pct < 50:
            print(f"   ✓ ACCEPTABLE: Error < 50%")
        else:
            print(f"   ⚠️  HIGH ERROR: {error_pct:.1f}%")

        print()

        # [4/6] Save data
        print("[4/6] Saving data...")

        # Save to drive
        csv_path = os.path.join(RESULTS_FOLDER, f"{row['run_id']}_data.csv")
        df_data = pd.DataFrame({'settlement_m': settlements, 'load_kN_per_m': loads})
        df_data.to_csv(csv_path, index=False)
        print(f"   ✓ Saved: {csv_path}")
        print()

        # [5/6] Update checkpoint
        print("[5/6] Updating checkpoint...")

        result_dict = {
            'run_id': row['run_id'],
            'su_Pa': row['su_Pa'],
            'width_m': row['width_m'],
            'Q_davisson': Q_davisson,
            'Q_max': Q_max,
            'Q_expected': Q_expected,
            'error_pct': error_pct,
            'runtime_min': runtime / 60,
            'num_points': len(settlements),
            'status': 'SUCCESS'
        }

        all_results.append(result_dict)

        # Save checkpoint
        df_checkpoint = pd.DataFrame(all_results)
        df_checkpoint.to_csv(checkpoint_file, index=False)
        print(f"   ✓ Checkpoint: {len(all_results)}/{len(df_remaining)} complete")
        print()

        # [6/6] Summary
        print("="*70)
        print(f"✅ {row['run_id']} COMPLETE")
        print("="*70)
        print(f"Bearing capacity: {Q_best:.0f} kN/m (expected {Q_expected:.0f}, error {error_pct:.1f}%)")
        print(f"Runtime: {runtime/60:.1f} min")
        print(f"Progress: {len(all_results)}/{len(df_remaining)} ({100*len(all_results)/len(df_remaining):.0f}%)")

        if len(all_results) < len(df_remaining):
            remaining_time = (len(df_remaining) - len(all_results)) * (runtime / 60)
            print(f"ETA: {remaining_time:.0f} min ({remaining_time/60:.1f} hours)")

        print()

    except Exception as e:
        print(f"❌ ERROR in {row['run_id']}: {str(e)}")
        import traceback
        traceback.print_exc()

        # Record failure
        result_dict = {
            'run_id': row['run_id'],
            'status': 'FAILED',
            'error': str(e)
        }
        all_results.append(result_dict)

        # Save checkpoint
        df_checkpoint = pd.DataFrame(all_results)
        df_checkpoint.to_csv(checkpoint_file, index=False)
        print()
        continue

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print()
print("="*70)
print("🎉 TIER 1 STUDY COMPLETE!")
print("="*70)

df_results = pd.DataFrame(all_results)
successful = df_results[df_results['status'] == 'SUCCESS']

print(f"Completed: {len(successful)}/{len(df_remaining)}")
print()

if len(successful) > 0:
    print("Summary statistics:")
    print(f"  Mean error: {successful['error_pct'].mean():.1f}%")
    print(f"  Std error: {successful['error_pct'].std():.1f}%")
    print(f"  Min error: {successful['error_pct'].min():.1f}%")
    print(f"  Max error: {successful['error_pct'].max():.1f}%")
    print()

    print("Results:")
    print(successful[['run_id', 'Q_davisson', 'Q_expected', 'error_pct', 'runtime_min']])

print()
print(f"📁 All results saved to: {RESULTS_FOLDER}")
print("="*70)
