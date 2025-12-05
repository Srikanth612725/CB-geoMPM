#!/usr/bin/env python3
"""
Execute Parametric Study
========================

Runs all simulations defined in parametric_study_plan.csv
"""

import pandas as pd
from pathlib import Path
from mpm_optimized import run_optimized_validation
import json

# Load study plan
df_plan = pd.read_csv('parametric_study_plan.csv')

print(f"Loaded {len(df_plan)} runs from study plan")

# Execute each run
results = []

for idx, row in df_plan.iterrows():
    run_id = row['run_id']
    print(f"\nRunning {run_id} ({idx+1}/{len(df_plan)})...")

    try:
        # Run simulation
        result = run_optimized_validation(
            su=row['su_Pa'],
            width=row['width_m'],
            thickness=row['thickness_m'],
            rate=row['rate_m_per_s'],
            target=row['target_settlement_m'],
            nx=int(row['nx']),
            ny=int(row['ny']),
            use_gimp=row['use_gimp'],
            plot_results=False
        )

        # Store results
        results.append({
            'run_id': run_id,
            'tier': row['tier'],
            'group': row['group'],
            'Q_ult_kN': result['ultimate_load'],
            'error_percent': result.get('error_percent', None),
            'success': True
        })

    except Exception as e:
        print(f"ERROR in {run_id}: {e}")
        results.append({
            'run_id': run_id,
            'tier': row['tier'],
            'group': row['group'],
            'success': False,
            'error': str(e)
        })

# Save results
df_results = pd.DataFrame(results)
df_results.to_csv('parametric_study_results.csv', index=False)
print(f"\n✅ Completed! Results saved to parametric_study_results.csv")
