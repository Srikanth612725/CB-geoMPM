"""
QUICK TEST VERSION - Run 3 simulations in ~10 minutes instead of 4 hours
==========================================================================

This version uses FASTER settings for validation:
- record_interval: 200 (instead of 40) → 5× less recording
- dt: 0.0002 (instead of 0.0001) → 2× larger timestep
- rate: 0.10 m/s (instead of 0.05) → 2× faster settlement
- target: 0.10 m (instead of 0.15) → 67% of original
- Only 3 runs instead of 12

Combined speedup: 5 × 2 × 2 × 0.67 = ~13× faster
Expected time: ~2-3 minutes per run, ~10 minutes total

Use this to:
1. Verify the simulation works
2. Check if capacity is reasonable
3. Validate the checkpoint system

If results look good, switch back to full TIER 1 parameters.
"""

import numpy as np
import pandas as pd
import time
import os
from pathlib import Path
from google.colab import files, drive

# Import MPM solver
from mpm_optimized import MPM2D_Optimized

# Import standard capacity methods
from standard_capacity_methods import (
    davisson_offset_method,
    chin_konder_method,
    brinch_hansen_80_method,
    fuller_hoy_method,
    settlement_10_percent_method
)

print("✅ All imports successful!")

# ==============================================================================
# STEP 1: MOUNT GOOGLE DRIVE
# ==============================================================================

print("\n" + "="*70)
print("QUICK TEST: 3 FAST RUNS FOR VALIDATION")
print("="*70)

drive.mount('/content/drive', force_remount=True)

drive_dir = '/content/drive/MyDrive/MPM_QUICK_TEST'
Path(drive_dir).mkdir(parents=True, exist_ok=True)

print(f"✅ Google Drive mounted!")
print(f"📁 Results folder: {drive_dir}")

local_dir = '/content/quick_test'
Path(local_dir).mkdir(parents=True, exist_ok=True)

# ==============================================================================
# STEP 2: CREATE QUICK TEST PLAN (3 runs only)
# ==============================================================================

print("\n" + "="*70)
print("CREATING QUICK TEST PLAN (3 runs)")
print("="*70)

plan_data = [
    {
        'run_id': 'QUICK_R01_B5.0_su6',
        'su_Pa': 6000,
        'width_m': 5.0,
        'nx': 60,
        'ny': 30,
        'rate_m_per_s': 0.10,  # ← FASTER
        'target_settlement_m': 0.10,  # ← LESS SETTLEMENT
        'use_gimp': False,
        'record_interval': 200  # ← LESS FREQUENT RECORDING
    },
    {
        'run_id': 'QUICK_R02_B5.0_su10',
        'su_Pa': 10000,
        'width_m': 5.0,
        'nx': 60,
        'ny': 30,
        'rate_m_per_s': 0.10,
        'target_settlement_m': 0.10,
        'use_gimp': False,
        'record_interval': 200
    },
    {
        'run_id': 'QUICK_R03_B6.84_su6',
        'su_Pa': 6000,
        'width_m': 6.84,
        'nx': 60,
        'ny': 30,
        'rate_m_per_s': 0.10,
        'target_settlement_m': 0.10,
        'use_gimp': False,
        'record_interval': 200
    }
]

df = pd.DataFrame(plan_data)
print(f"✅ Quick test plan: {len(df)} runs")
print(f"\n   Settings for speed:")
print(f"   - Settlement rate: 0.10 m/s (2× faster)")
print(f"   - Target settlement: 0.10 m (67% of normal)")
print(f"   - Recording interval: 200 steps (5× less frequent)")
print(f"   - Timestep: 0.0002 s (2× larger)")
print(f"\n   Expected time: ~2-3 min/run, ~10 min total")

# ==============================================================================
# STEP 3: RUN QUICK TEST
# ==============================================================================

print("\n" + "="*70)
print("EXECUTING QUICK TEST")
print("="*70)

all_results = []
start_time_total = time.time()

for idx, row in df.iterrows():
    run_id = row['run_id']
    su = row['su_Pa']
    width = row['width_m']

    print(f"\n{'#'*70}")
    print(f"# RUN {idx+1}/{len(df)}: {run_id}")
    print(f"# su = {su/1000:.0f} kPa, width = {width:.2f} m")
    print(f"{'#'*70}")

    try:
        # ====================================================================
        # CREATE MPM SOLVER
        # ====================================================================

        print(f"\n[1/5] Creating MPM solver...")

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

        print(f"   ✓ Soil: {mpm.particles.count(lambda p: p.material_id==0)} particles")
        print(f"   ✓ Foundation: {len(mpm.foundation_indices)} particles")

        # ====================================================================
        # RUN SIMULATION (FAST SETTINGS)
        # ====================================================================

        print(f"\n[2/5] Running MPM simulation (FAST mode)...")

        max_steps = 100000
        dt = 0.0002  # ← LARGER TIMESTEP
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

        # ====================================================================
        # CALCULATE CAPACITY
        # ====================================================================

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

        # ====================================================================
        # SAVE FILES
        # ====================================================================

        print(f"\n[4/5] Saving...")

        pd.DataFrame({
            'settlement_m': settlements,
            'load_kN_per_m': loads
        }).to_csv(f'{drive_dir}/{run_id}_data.csv', index=False)

        # ====================================================================
        # STORE RESULT
        # ====================================================================

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

        print(f"\n[5/5] ✅ {run_id} COMPLETE")
        print(f"   Runtime: {runtime/60:.1f} min")
        print(f"   Progress: {len(all_results)}/{len(df)}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

        all_results.append({
            'run_id': run_id,
            'su_kPa': su / 1000,
            'width_m': width,
            'status': 'FAILED',
            'error': str(e)
        })

# ==============================================================================
# FINAL SUMMARY
# ==============================================================================

total_time = time.time() - start_time_total

print(f"\n{'='*70}")
print(f"🎉 QUICK TEST COMPLETE!")
print(f"{'='*70}")

df_results = pd.DataFrame(all_results)
successful = df_results[df_results['status'] == 'SUCCESS']

print(f"\nSummary:")
print(f"  ✅ Successful: {len(successful)}/{len(df)}")
print(f"  ⏱️  Total time: {total_time/60:.1f} min")

if len(successful) > 0:
    print(f"\nResults:")
    print(df_results[['run_id', 'Q_expected_kN_per_m', 'Q_davisson_kN_per_m',
                      'error_%', 'runtime_min']].to_string(index=False))

    avg_error = successful['error_%'].mean()
    print(f"\n  Average error: {avg_error:.1f}%")

    if avg_error < 20:
        print(f"\n  ✅ GOOD! Error < 20% - Proceed with full TIER 1")
    elif avg_error < 50:
        print(f"\n  ⚠️  FAIR: Error = {avg_error:.1f}% - Check bearing capacity calculation")
    else:
        print(f"\n  ❌ POOR: Error = {avg_error:.1f}% - Debug needed!")

# Save results
df_results.to_csv(f'{drive_dir}/quick_test_results.csv', index=False)
df_results.to_csv('quick_test_results.csv', index=False)

print(f"\n📊 Results saved to: {drive_dir}/quick_test_results.csv")

print(f"\n{'='*70}")
print(f"NEXT STEPS:")
print(f"{'='*70}")
print(f"""
1. If results look good (error < 30%):
   → Run full TIER 1 with COLAB_CELL_6A_FINAL_CORRECT_API.py

2. If capacity is too high (error > 100%):
   → Debug calculate_bearing_capacity() method
   → Check if foundation is penetrating properly

3. If runs took > 5 min each:
   → Consider keeping faster settings for full study
   → Or run overnight (12 runs × 5 min = 1 hour)
""")
