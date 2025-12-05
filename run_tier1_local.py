"""
Run TIER 1 Parametric Study LOCALLY
===================================
No Google Drive, no disconnects, full control!

This script runs all 12 TIER 1 simulations on your local machine.
Results are saved to ./tier1_results_local/

To run:
    python3 run_tier1_local.py

To run in background:
    nohup python3 run_tier1_local.py > tier1.log 2>&1 &
    tail -f tier1.log  # Monitor progress
"""

import numpy as np
import pandas as pd
import time
import os
from pathlib import Path

# Import your MPM solver
from mpm_optimized import MPM2D_Optimized
from standard_capacity_methods import davisson_offset_method

print("="*70)
print("TIER 1 PARAMETRIC STUDY - LOCAL EXECUTION")
print("="*70)
print()

# ====================================================================
# SETUP: Create output directory
# ====================================================================

results_dir = Path("./tier1_results_local")
results_dir.mkdir(exist_ok=True)
print(f"📁 Results directory: {results_dir}")
print(f"   Results will be saved here even if script crashes!")
print()

# ====================================================================
# STEP 1: Load or create plan
# ====================================================================

plan_file = "tier1_plan.csv"

if os.path.exists(plan_file):
    df = pd.read_csv(plan_file)
    print(f"✅ Loaded existing plan: {len(df)} runs")
else:
    print("⚠️  No plan found. Creating default TIER 1 plan...")

    # Create default TIER 1: 12 runs
    plan_data = []
    run_count = 1

    for width in [5.0, 6.84]:  # 5m and Liu width
        for su in [6000, 10000]:  # 6 kPa and 10 kPa
            for rep in range(3):  # 3 replicates
                plan_data.append({
                    'run_id': f'T1_R{run_count:02d}_B{width}_su{int(su/1000)}',
                    'su_Pa': su,
                    'width_m': width,
                    'nx': 60,
                    'ny': 30,
                    'rate_m_per_s': 0.10,  # FASTER for local testing
                    'target_settlement_m': 0.10,  # LESS settlement
                    'use_gimp': False,
                    'record_interval': 200  # LESS FREQUENT recording
                })
                run_count += 1

    df = pd.DataFrame(plan_data)
    df.to_csv(plan_file, index=False)
    print(f"✅ Created plan: {len(df)} runs")

print(f"\nPlan summary:")
print(df.head(3))
print()

# ====================================================================
# STEP 2: Check for checkpoint (resume capability)
# ====================================================================

checkpoint_file = results_dir / "checkpoint.csv"

if checkpoint_file.exists():
    print(f"⚠️  CHECKPOINT FOUND!")
    df_completed = pd.read_csv(checkpoint_file)

    # Only load SUCCESSFUL runs
    if 'status' in df_completed.columns:
        df_successful = df_completed[df_completed['status'] == 'SUCCESS']
        completed_ids = set(df_successful['run_id'].values)
    else:
        completed_ids = set(df_completed['run_id'].values)

    df_remaining = df[~df['run_id'].isin(completed_ids)]
    all_results = df_completed.to_dict('records')

    print(f"   Successful: {len(completed_ids)} runs")
    if 'status' in df_completed.columns:
        failed_count = len(df_completed[df_completed['status'] == 'FAILED'])
        print(f"   Failed (will retry): {failed_count} runs")
    print(f"   Remaining: {len(df_remaining)} runs")
    print(f"   → Resuming from where you left off!")
else:
    print(f"🆕 No checkpoint found - starting fresh")
    all_results = []
    df_remaining = df

print(f"\n📊 Execution plan:")
print(f"   Runs to execute: {len(df_remaining)}")
print(f"   Estimated time: {len(df_remaining) * 2 / 60:.1f} hours @ 2 min/run")
print()

# ====================================================================
# STEP 3: Execute simulations
# ====================================================================

print("="*70)
print("EXECUTING TIER 1 PARAMETRIC STUDY")
print("="*70)
print()

start_time_total = time.time()

for idx_orig, row in df_remaining.iterrows():
    run_id = row['run_id']
    su = row['su_Pa']
    width = row['width_m']

    current_idx = len(all_results) + 1
    total_runs = len(df)

    print(f"{'#'*70}")
    print(f"# RUN {current_idx}/{total_runs}: {run_id}")
    print(f"# su = {su/1000:.0f} kPa, width = {width:.2f} m")
    print(f"# Elapsed: {(time.time()-start_time_total)/60:.1f} min")
    print(f"{'#'*70}")
    print()

    try:
        # ================================================================
        # CREATE MPM SOLVER
        # ================================================================

        print(f"[1/5] Creating MPM solver...")

        domain_width = width * 6.0
        domain_height = 20.0
        E = su * 500
        nu = 0.495
        rho = 1600
        use_gimp = bool(row['use_gimp'])

        mpm = MPM2D_Optimized(
            domain_x=(0, domain_width),
            domain_y=(0, domain_height),
            nx=int(row['nx']),
            ny=int(row['ny']),
            su=su,
            E=E,
            nu=nu,
            rho=rho,
            use_gimp=use_gimp
        )

        print(f"   ✓ Domain: {domain_width}m × {domain_height}m")
        print(f"   ✓ Mesh: {int(row['nx'])}×{int(row['ny'])}")

        # Add soil
        soil_depth = 15.0
        mpm.add_soil_block(
            x_range=(0, domain_width),
            y_range=(0, soil_depth),
            ppc=4
        )

        # Add foundation
        center_x = domain_width / 2.0
        y_base = soil_depth
        mpm.add_strip_foundation(
            center_x=center_x,
            y_base=y_base,
            width=width,
            thickness=0.5,
            density=2500
        )

        print(f"   ✓ Soil: {sum(1 for mp in mpm.particles if mp.material_id==0)} particles")
        print(f"   ✓ Foundation: {len(mpm.foundation_indices)} particles")

        # ================================================================
        # RUN SIMULATION
        # ================================================================

        print(f"\n[2/5] Running MPM simulation...")

        max_steps = 100000
        dt = 0.0001
        target = row['target_settlement_m']
        rate = row['rate_m_per_s']
        record_every = int(row['record_interval'])

        settlements = []
        loads = []
        step = 0

        mpm.foundation_velocity = -rate

        run_start = time.time()

        while step < max_steps:
            mpm.mpm_step(dt)
            step += 1

            current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])

            if mpm.foundation_y0 is None:
                mpm.foundation_y0 = current_y

            settlement = mpm.foundation_y0 - current_y

            if step % record_every == 0:
                q = mpm.calculate_bearing_capacity() / 1000
                settlements.append(settlement)
                loads.append(q)

                if step % 1000 == 0:
                    elapsed = time.time() - run_start
                    print(f"   Step {step:5d} | s={settlement*1000:5.1f}mm | "
                          f"q={q:6.0f} kN/m | {elapsed:.0f}s")

            if settlement >= target:
                q = mpm.calculate_bearing_capacity() / 1000
                settlements.append(settlement)
                loads.append(q)
                print(f"   ✓ Target {target*1000:.0f}mm reached at step {step}")
                break

        runtime = time.time() - run_start

        settlements = np.array(settlements)
        loads = np.array(loads)

        print(f"   ✓ Complete: {runtime/60:.1f} min, {len(loads)} data points")

        # ================================================================
        # CALCULATE CAPACITY
        # ================================================================

        print(f"\n[3/5] Calculating capacity...")

        Nc = 2 + np.pi
        Q_expected = (su / 1000) * width * Nc

        try:
            result = davisson_offset_method(settlements, loads, width)
            Q_davisson = result['Q_ult']
        except:
            Q_davisson = np.nan

        Q_max = np.max(loads)
        error = abs(Q_davisson - Q_expected) / Q_expected * 100 if not np.isnan(Q_davisson) else np.nan

        print(f"   ✓ Davisson:  {Q_davisson:.0f} kN/m" if not np.isnan(Q_davisson) else "   ✗ Davisson:  Failed")
        print(f"   ✓ Maximum:   {Q_max:.0f} kN/m")
        print(f"   → Expected:  {Q_expected:.0f} kN/m (Prandtl)")
        if not np.isnan(error):
            print(f"   → Error:     {error:.1f}%")

        # ================================================================
        # SAVE DATA FILES
        # ================================================================

        print(f"\n[4/5] Saving data files...")

        pd.DataFrame({
            'settlement_m': settlements,
            'load_kN_per_m': loads
        }).to_csv(results_dir / f"{run_id}_data.csv", index=False)

        print(f"   ✓ Saved: {run_id}_data.csv")

        # ================================================================
        # UPDATE CHECKPOINT
        # ================================================================

        print(f"\n[5/5] Updating checkpoint...")

        result = {
            'run_id': run_id,
            'su_kPa': su / 1000,
            'width_m': width,
            'Q_expected_kN_per_m': Q_expected,
            'Q_davisson_kN_per_m': Q_davisson,
            'Q_max_kN_per_m': Q_max,
            'error_%': error,
            'runtime_min': runtime / 60,
            'status': 'SUCCESS'
        }
        all_results.append(result)

        # Save checkpoint
        df_checkpoint = pd.DataFrame(all_results)
        df_checkpoint.to_csv(checkpoint_file, index=False)

        print(f"   ✓ Checkpoint updated ({len(all_results)}/{total_runs} complete)")

        # ================================================================
        # RUN SUMMARY
        # ================================================================

        print(f"\n{'='*70}")
        print(f"✅ {run_id} COMPLETE")
        print(f"{'='*70}")
        if not np.isnan(Q_davisson):
            print(f"Davisson: {Q_davisson:.0f} kN/m ({error:.1f}% error)")
        print(f"Runtime: {runtime/60:.1f} min")
        print(f"Progress: {len(all_results)}/{total_runs} ({len(all_results)/total_runs*100:.0f}%)")

        remaining = total_runs - len(all_results)
        if remaining > 0:
            eta_min = remaining * (runtime / 60)
            print(f"ETA: {eta_min:.0f} min ({eta_min/60:.1f} hours)")
        print()

    except Exception as e:
        print(f"\n❌ ERROR in {run_id}:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()

        # Log error
        all_results.append({
            'run_id': run_id,
            'su_kPa': su / 1000,
            'width_m': width,
            'status': 'FAILED',
            'error': str(e)
        })

        # Save checkpoint even with error
        df_checkpoint = pd.DataFrame(all_results)
        df_checkpoint.to_csv(checkpoint_file, index=False)

        print(f"⚠️  Error logged, continuing...")
        print()

# ====================================================================
# FINAL SUMMARY
# ====================================================================

total_time = time.time() - start_time_total

print("="*70)
print("🎉 TIER 1 COMPLETE!")
print("="*70)

df_results = pd.DataFrame(all_results)
successful = df_results[df_results['status'] == 'SUCCESS']
failed = df_results[df_results.get('status', 'SUCCESS') == 'FAILED']

print(f"\nSummary:")
print(f"  ✅ Successful: {len(successful)}/{len(df)}")
print(f"  ❌ Failed: {len(failed)}/{len(df)}")
print(f"  ⏱️  Total time: {total_time/3600:.2f} hours")
print(f"  📁 Data saved to: {results_dir}")

# Save final results
results_file = results_dir / "tier1_results_FINAL.csv"
df_results.to_csv(results_file, index=False)

print(f"\n📊 Final results:")
print(f"  {results_file}")

if len(successful) > 0:
    print(f"\nResults:")
    print(df_results[['run_id', 'Q_expected_kN_per_m', 'Q_davisson_kN_per_m',
                      'error_%', 'runtime_min']].to_string(index=False))

    avg_error = successful['error_%'].mean()
    print(f"\n  Average error: {avg_error:.1f}%")

    if avg_error < 20:
        print(f"\n  ✅ EXCELLENT! Error < 20%")
    elif avg_error < 50:
        print(f"\n  ✅ GOOD! Error < 50%")
    else:
        print(f"\n  ⚠️  High error - check bearing capacity calculation")

print(f"\n{'='*70}")
print(f"✅ ALL DONE!")
print(f"{'='*70}")
print(f"""
Your results are saved in:
  📁 {results_dir}/

Files created:
  - tier1_results_FINAL.csv (summary)
  - T1_R01_B5.0_su6_data.csv (load-settlement curves)
  - ... (one CSV per run)

Next steps:
  1. Check results in tier1_results_FINAL.csv
  2. Plot load-settlement curves
  3. Compare with Liu et al. (2022) validation data
""")
