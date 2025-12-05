"""
BULLETPROOF CELL 6A: Parametric Study with Drive Backup
========================================================

Features:
- ✅ Saves to Google Drive (persistent storage)
- ✅ Creates local backups
- ✅ Checkpointing (resume if disconnected)
- ✅ Auto-downloads completed runs
- ✅ Progress tracking
- ✅ Error recovery

Even if Colab disconnects, your data is SAFE in Google Drive!
"""

# ==============================================================================
# CELL 6A: BULLETPROOF PARAMETRIC STUDY WITH DRIVE BACKUP
# ==============================================================================

def run_tier1_with_drive_backup(df):
    """
    Run TIER 1 parametric study with Google Drive backup

    Features:
    - Saves each run to Drive immediately
    - Creates checkpoint file (can resume if interrupted)
    - Auto-downloads files as backup
    - Progress tracking

    Parameters:
    -----------
    df : DataFrame
        Must have columns: run_id, su_Pa, width_m, nx, ny, rate_m_per_s,
                          target_settlement_m, use_gimp, record_interval
    """

    from google.colab import files
    import os
    import time
    from pathlib import Path

    # ========================================================================
    # STEP 1: Setup Google Drive (persistent storage)
    # ========================================================================

    print("="*70)
    print("TIER 1 PARAMETRIC STUDY - BULLETPROOF VERSION")
    print("="*70)

    # Mount Google Drive
    from google.colab import drive
    drive.mount('/content/drive', force_remount=True)

    # Create project folder in Drive
    drive_dir = '/content/drive/MyDrive/MPM_TIER1_Results'
    Path(drive_dir).mkdir(parents=True, exist_ok=True)

    print(f"\n✅ Google Drive mounted")
    print(f"📁 Results will be saved to: {drive_dir}")
    print(f"   Even if Colab disconnects, data is SAFE in your Drive!")

    # Create local working directory
    local_dir = '/content/tier1_results'
    Path(local_dir).mkdir(parents=True, exist_ok=True)

    # ========================================================================
    # STEP 2: Check for checkpoint (resume capability)
    # ========================================================================

    checkpoint_file = f'{drive_dir}/checkpoint.csv'

    if os.path.exists(checkpoint_file):
        print(f"\n⚠️  CHECKPOINT FOUND!")
        df_completed = pd.read_csv(checkpoint_file)

        # ✅ FIX: Only load SUCCESSFUL runs, re-attempt failed ones
        if 'status' in df_completed.columns:
            df_successful = df_completed[df_completed['status'] == 'SUCCESS']
            completed_ids = set(df_successful['run_id'].values)
        else:
            # Backwards compatibility: assume all are successful if no status column
            completed_ids = set(df_completed['run_id'].values)

        # Filter out completed runs
        df_remaining = df[~df['run_id'].isin(completed_ids)]

        print(f"   Successful: {len(completed_ids)} runs")
        if 'status' in df_completed.columns:
            failed_count = len(df_completed[df_completed['status'] == 'FAILED'])
            print(f"   Failed (will retry): {failed_count} runs")
        print(f"   Remaining: {len(df_remaining)} runs")
        print(f"\n➡️  Resuming from where you left off!")

        all_results = df_completed.to_dict('records')
        df_to_run = df_remaining
    else:
        print(f"\n🆕 Starting fresh (no checkpoint found)")
        all_results = []
        df_to_run = df

    print(f"\n{'='*70}")
    print(f"EXECUTION PLAN")
    print(f"{'='*70}")
    print(f"Total runs to execute: {len(df_to_run)}")
    print(f"Estimated time: {len(df_to_run) * 7 / 60:.1f} hours (at 7 min/run)")
    print(f"{'='*70}\n")

    # ========================================================================
    # STEP 3: Execute parametric study with saves
    # ========================================================================

    start_time_total = time.time()

    for idx, row in df_to_run.iterrows():
        run_id = row['run_id']
        su = row['su_Pa']
        width = row['width_m']

        print(f"\n{'#'*70}")
        print(f"# RUN {idx+1}/{len(df)}: {run_id}")
        print(f"# su = {su/1000:.0f} kPa, width = {width:.2f} m")
        print(f"# Elapsed: {(time.time()-start_time_total)/60:.1f} min")
        print(f"{'#'*70}")

        try:
            # ================================================================
            # Create MPM solver
            # ================================================================

            print(f"\n[1/5] Creating MPM solver...")

            mpm = MPM2D_Optimized(
                width=width * 6.0,
                height=20.0,
                nx=int(row['nx']),
                ny=int(row['ny']),
                foundation_width=width,
                foundation_thickness=0.5,
                foundation_density=2500,
                su=su,
                E_ratio=500,
                nu=0.495,
                rho=1600,
                use_gimp=bool(row['use_gimp']),
                ppc=4
            )

            print(f"   ✓ Mesh: {int(row['nx'])}×{int(row['ny'])}")
            print(f"   ✓ Domain: {width*6:.1f}m × 20m")

            # ================================================================
            # Run simulation
            # ================================================================

            print(f"\n[2/5] Running MPM simulation...")

            max_steps = 100000
            dt = 0.0001
            target = row['target_settlement_m']
            rate = row['rate_m_per_s']
            record_every = int(row.get('record_interval', 40))

            settlements = []
            loads = []
            step = 0

            # ✅ FIX: Set foundation velocity directly (works with all versions)
            mpm.foundation_velocity = -rate  # Negative = downward

            run_start = time.time()

            while step < max_steps:
                mpm.mpm_step(dt)
                step += 1

                current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])
                settlement = mpm.foundation_y0 - current_y

                if step % record_every == 0:
                    q = mpm.calculate_bearing_capacity_v2() / 1000  # ✅ FIX: Use v2 (reaction forces)
                    settlements.append(settlement)
                    loads.append(q)

                    if step % 1000 == 0:
                        elapsed = time.time() - run_start
                        print(f"   Step {step:5d} | s={settlement*1000:5.1f}mm | "
                              f"q={q:6.0f} kN/m | {elapsed:.0f}s")

                if settlement >= target:
                    q = mpm.calculate_bearing_capacity_v2() / 1000  # ✅ FIX: Use v2 (reaction forces)
                    settlements.append(settlement)
                    loads.append(q)
                    print(f"   ✓ Target settlement {target*1000:.0f}mm reached at step {step}")
                    break

            runtime = time.time() - run_start

            settlements = np.array(settlements)
            loads = np.array(loads)

            print(f"   ✓ Simulation complete: {runtime/60:.1f} min, {len(loads)} data points")

            # ================================================================
            # Calculate capacity using Davisson
            # ================================================================

            print(f"\n[3/5] Calculating ultimate capacity (Davisson method)...")

            capacity_result = davisson_offset_method(settlements, loads, width)
            Q_ult = capacity_result['Q_ult']
            s_ult = capacity_result.get('s_ult', 0)

            print(f"   ✓ Q_ult = {Q_ult:.0f} kN/m")
            print(f"   ✓ s_ult = {s_ult*1000:.1f} mm")

            # ================================================================
            # Save data files
            # ================================================================

            print(f"\n[4/5] Saving data files...")

            # Save to LOCAL (temporary)
            local_csv = f'{local_dir}/{run_id}_data.csv'
            local_npz = f'{local_dir}/{run_id}_data.npz'

            pd.DataFrame({
                'settlement_m': settlements,
                'load_kN_per_m': loads
            }).to_csv(local_csv, index=False)

            np.savez(local_npz,
                     settlements=settlements,
                     loads=loads,
                     width=width,
                     su=su,
                     Q_ult=Q_ult)

            print(f"   ✓ Saved locally: {run_id}_data.csv")
            print(f"   ✓ Saved locally: {run_id}_data.npz")

            # Save to GOOGLE DRIVE (persistent!)
            drive_csv = f'{drive_dir}/{run_id}_data.csv'
            drive_npz = f'{drive_dir}/{run_id}_data.npz'

            pd.DataFrame({
                'settlement_m': settlements,
                'load_kN_per_m': loads
            }).to_csv(drive_csv, index=False)

            np.savez(drive_npz,
                     settlements=settlements,
                     loads=loads,
                     width=width,
                     su=su,
                     Q_ult=Q_ult)

            print(f"   ✓ Saved to Drive: {run_id}_data.csv")
            print(f"   ✓ Saved to Drive: {run_id}_data.npz")

            # ================================================================
            # Store result and update checkpoint
            # ================================================================

            print(f"\n[5/5] Updating checkpoint...")

            result = {
                'run_id': run_id,
                'su_kPa': su / 1000,
                'width_m': width,
                'Q_ult_kN_per_m': Q_ult,
                's_ult_mm': s_ult * 1000,
                'runtime_min': runtime / 60,
                'data_points': len(loads),
                'mesh': f"{int(row['nx'])}x{int(row['ny'])}",
                'rate_m_per_s': rate,
                'target_settlement_m': target,
                'status': 'SUCCESS'
            }
            all_results.append(result)

            # Save checkpoint (can resume if disconnected)
            df_checkpoint = pd.DataFrame(all_results)
            df_checkpoint.to_csv(checkpoint_file, index=False)
            df_checkpoint.to_csv(f'{local_dir}/checkpoint.csv', index=False)

            print(f"   ✓ Checkpoint updated ({len(all_results)}/{len(df)} runs complete)")

            # ================================================================
            # Success summary for this run
            # ================================================================

            print(f"\n{'='*70}")
            print(f"✅ {run_id} COMPLETE")
            print(f"{'='*70}")
            print(f"Q_ult: {Q_ult:.0f} kN/m")
            print(f"Runtime: {runtime/60:.1f} min")
            print(f"Progress: {len(all_results)}/{len(df)} runs ({len(all_results)/len(df)*100:.0f}%)")
            print(f"Total elapsed: {(time.time()-start_time_total)/60:.1f} min")

            remaining = len(df) - len(all_results)
            if remaining > 0:
                eta_min = remaining * (runtime / 60)
                print(f"Estimated time remaining: {eta_min:.0f} min ({eta_min/60:.1f} hours)")

        except Exception as e:
            print(f"\n❌ ERROR in {run_id}: {e}")
            import traceback
            traceback.print_exc()

            # Save error to results
            all_results.append({
                'run_id': run_id,
                'su_kPa': su / 1000,
                'width_m': width,
                'status': 'FAILED',
                'error': str(e)
            })

            # Update checkpoint even with error
            df_checkpoint = pd.DataFrame(all_results)
            df_checkpoint.to_csv(checkpoint_file, index=False)

            print(f"⚠️  Error logged, continuing to next run...")

    # ========================================================================
    # STEP 4: Final summary and download
    # ========================================================================

    total_time = time.time() - start_time_total

    print(f"\n{'='*70}")
    print(f"🎉 TIER 1 PARAMETRIC STUDY COMPLETE!")
    print(f"{'='*70}")

    df_results = pd.DataFrame(all_results)

    successful = df_results[df_results['status'] == 'SUCCESS']
    failed = df_results[df_results['status'] == 'FAILED']

    print(f"\nSummary:")
    print(f"  ✅ Successful: {len(successful)}/{len(df)}")
    print(f"  ❌ Failed: {len(failed)}/{len(df)}")
    print(f"  ⏱️  Total time: {total_time/3600:.2f} hours ({total_time/60:.0f} min)")
    print(f"  📁 All data saved to: {drive_dir}")

    # Save final results
    results_file_drive = f'{drive_dir}/tier1_results.csv'
    results_file_local = f'{local_dir}/tier1_results.csv'

    df_results.to_csv(results_file_drive, index=False)
    df_results.to_csv(results_file_local, index=False)

    print(f"\n📊 Results saved:")
    print(f"  - Google Drive: {results_file_drive}")
    print(f"  - Local: {results_file_local}")

    # Download results file
    print(f"\n📥 Downloading tier1_results.csv...")
    files.download(results_file_local)

    # Optionally download all data files (compressed)
    print(f"\n📦 Creating zip archive of all data files...")

    import zipfile
    zip_file = f'{local_dir}/tier1_all_data.zip'

    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all CSV files
        for f in Path(local_dir).glob('*_data.csv'):
            zipf.write(f, f.name)
        # Add all NPZ files
        for f in Path(local_dir).glob('*_data.npz'):
            zipf.write(f, f.name)
        # Add results
        zipf.write(results_file_local, 'tier1_results.csv')

    zip_size = os.path.getsize(zip_file) / 1024 / 1024
    print(f"  ✓ Created: tier1_all_data.zip ({zip_size:.1f} MB)")

    print(f"\n📥 Downloading tier1_all_data.zip...")
    files.download(zip_file)

    print(f"\n{'='*70}")
    print(f"✅ ALL DONE!")
    print(f"{'='*70}")
    print(f"""
Your data is safe in THREE places:
1. ☁️  Google Drive: {drive_dir}
2. 💾 Downloaded zip: tier1_all_data.zip (in your Downloads folder)
3. 📊 Results CSV: tier1_results.csv (in your Downloads folder)

Even if Colab crashes, everything is in your Google Drive!

Next steps:
1. Extract tier1_all_data.zip on your computer
2. Upload tier1_results.csv and *_data.csv files back to Colab
3. Run the comparison cell to compare all 5 methods
""")

    return df_results


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    # This assumes you already have df with your TIER 1 parameters
    # Example:

    # df should have columns:
    # - run_id
    # - su_Pa
    # - width_m
    # - nx, ny
    # - rate_m_per_s
    # - target_settlement_m
    # - use_gimp
    # - record_interval

    # Run the bulletproof version
    results = run_tier1_with_drive_backup(df)

    print("\n✅ Complete! Check your Google Drive for all data files.")
