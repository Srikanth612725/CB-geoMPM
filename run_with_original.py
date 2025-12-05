#!/usr/bin/env python3
"""
Run Optus's Smart Parametric Study with mpm_validation.py
(Using original Codex code that works - 22% error vs 463% in optimized)
"""

import pandas as pd
from pathlib import Path
import json
import time
from mpm_validation import run_validation_simulation, LIU_DATA, EQUIVALENT_WIDTH

print("="*70)
print("SMART PARAMETRIC STUDY - Using mpm_validation.py")
print("(Original Codex implementation - 22% error, stable)")
print("="*70)

def run_single_case(row):
    """Run a single parametric case"""

    run_id = row['run_id']
    print(f"\n{'='*70}")
    print(f"Running: {run_id}")
    print(f"Description: {row['description']}")
    print(f"{'='*70}")

    try:
        # Map parameters from study plan to mpm_validation function
        result = run_validation_simulation(
            su=int(row['su_Pa']),
            width=float(row['width_m']),
            thickness=float(row['thickness_m']),
            rate=float(row['rate_m_per_s']),
            target=float(row['target_settlement_m']),
            interval=0.02,
            max_steps=int(row.get('max_steps', 12000)),
            nx=int(row['nx']),
            ny=int(row['ny']),
            plot_results=False,
        )

        if result and len(result['loads']) > 0:
            ultimate_load = float(result['ultimate_load'])

            # Calculate Nc factor
            Nc_MPM = (ultimate_load * 1000) / (row['su_Pa'] * row['width_m'])

            # Calculate error if expected value exists
            error_pct = None
            if 'expected_Q_kN' in row and pd.notna(row['expected_Q_kN']):
                expected = float(row['expected_Q_kN'])
                error_pct = abs(ultimate_load - expected) / expected * 100

            result_dict = {
                'run_id': run_id,
                'tier': row['tier'],
                'group': row['group'],
                'success': True,
                'Q_ult_kN': ultimate_load,
                'Nc_MPM': Nc_MPM,
                'error_percent': error_pct,
                'settlements': result['settlements'].tolist() if hasattr(result['settlements'], 'tolist') else list(result['settlements']),
                'loads': result['loads'].tolist() if hasattr(result['loads'], 'tolist') else list(result['loads']),
                'times': result['times'].tolist() if hasattr(result['times'], 'tolist') else list(result['times']),
            }

            print(f"\n✅ SUCCESS!")
            print(f"   Q_ult: {ultimate_load:.0f} kN")
            print(f"   Nc: {Nc_MPM:.3f}")
            if error_pct is not None:
                print(f"   Error: {error_pct:.1f}%")

            return result_dict
        else:
            print(f"\n❌ FAILED - No results")
            return {
                'run_id': run_id,
                'tier': row['tier'],
                'group': row['group'],
                'success': False,
                'error_message': 'No results returned'
            }

    except Exception as e:
        print(f"\n❌ FAILED - Exception: {e}")
        return {
            'run_id': run_id,
            'tier': row['tier'],
            'group': row['group'],
            'success': False,
            'error_message': str(e)
        }


def run_tier(tier_number, df_plan):
    """Run all cases in a specific tier"""

    tier_cases = df_plan[df_plan['tier'] == tier_number].copy()
    print(f"\n{'='*70}")
    print(f"TIER {tier_number}: {len(tier_cases)} runs")
    print(f"{'='*70}")

    results = []
    start_time = time.time()

    for idx, row in tier_cases.iterrows():
        case_start = time.time()
        result = run_single_case(row)
        case_elapsed = time.time() - case_start

        result['elapsed_time_s'] = case_elapsed
        results.append(result)

        # Save intermediate results
        df_results = pd.DataFrame(results)
        df_results.to_csv(f'tier{tier_number}_results_partial.csv', index=False)

    total_elapsed = time.time() - start_time

    # Final save
    df_results = pd.DataFrame(results)
    df_results.to_csv(f'tier{tier_number}_results.csv', index=False)

    # Summary
    n_success = sum(1 for r in results if r['success'])
    n_failed = len(results) - n_success

    print(f"\n{'='*70}")
    print(f"TIER {tier_number} SUMMARY")
    print(f"{'='*70}")
    print(f"Total runs: {len(results)}")
    print(f"Success: {n_success}")
    print(f"Failed: {n_failed}")
    print(f"Time: {total_elapsed/60:.1f} minutes")
    print(f"Avg per run: {total_elapsed/len(results):.1f} seconds")
    print(f"Saved: tier{tier_number}_results.csv")

    return df_results


def main():
    """Main execution"""

    # Load study plan
    plan_file = Path('parametric_study_plan.csv')

    if not plan_file.exists():
        print("❌ ERROR: parametric_study_plan.csv not found!")
        print("Run smart_parametric_study.py first to generate the plan.")
        return

    df_plan = pd.read_csv(plan_file)
    print(f"\nLoaded study plan: {len(df_plan)} total runs")

    # Ask which tier to run
    print(f"\nAvailable tiers:")
    for tier in sorted(df_plan['tier'].unique()):
        tier_df = df_plan[df_plan['tier'] == tier]
        print(f"  TIER {tier}: {len(tier_df)} runs")
        for group in tier_df['group'].unique():
            group_count = len(tier_df[tier_df['group'] == group])
            print(f"    └─ {group}: {group_count} runs")

    # For now, run TIER 1 (validation)
    print(f"\n{'='*70}")
    print("STARTING WITH TIER 1 (VALIDATION)")
    print("{'='*70}")

    tier1_results = run_tier(1, df_plan)

    # Analysis of TIER 1
    print(f"\n{'='*70}")
    print("TIER 1 ANALYSIS")
    print(f"{'='*70}")

    successful = tier1_results[tier1_results['success'] == True]

    if len(successful) > 0:
        # Mesh independence check
        mesh_cases = successful[successful['group'] == 'mesh_independence']
        if len(mesh_cases) >= 2:
            Nc_values = mesh_cases['Nc_MPM'].values
            Nc_mean = Nc_values.mean()
            Nc_std = Nc_values.std()
            print(f"\n📐 Mesh Independence:")
            print(f"   Nc values: {Nc_values}")
            print(f"   Mean: {Nc_mean:.3f}")
            print(f"   Std: {Nc_std:.3f}")
            print(f"   Convergence: {Nc_std/Nc_mean*100:.1f}% variation")

            if Nc_std/Nc_mean < 0.05:  # <5% variation
                print(f"   ✅ CONVERGED!")
            else:
                print(f"   ⚠️  NOT FULLY CONVERGED")

        # Liu replication check
        liu_cases = successful[successful['group'] == 'liu_replication']
        if len(liu_cases) > 0:
            liu_Q = liu_cases['Q_ult_kN'].values
            liu_target = 2522
            liu_errors = [abs(q - liu_target)/liu_target*100 for q in liu_Q]
            print(f"\n📊 Liu Replication:")
            print(f"   Q values: {liu_Q}")
            print(f"   Target: {liu_target} kN")
            print(f"   Errors: {liu_errors}")
            print(f"   Mean error: {sum(liu_errors)/len(liu_errors):.1f}%")

            if sum(liu_errors)/len(liu_errors) < 25:
                print(f"   ✅ ACCEPTABLE (<25% error)")
            else:
                print(f"   ⚠️  HIGH ERROR")

    print(f"\n{'='*70}")
    print("TIER 1 COMPLETE!")
    print(f"{'='*70}")
    print(f"\nNext steps:")
    print(f"1. Review tier1_results.csv")
    print(f"2. If validation looks good, run TIER 2 (heterogeneity)")
    print(f"3. Then run TIER 3 (V-H-M loading)")


if __name__ == "__main__":
    main()
