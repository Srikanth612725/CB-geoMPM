#!/usr/bin/env python3
"""
Smart Parametric Study for Mat Foundation Capacity
==================================================

Based on Optus's physics-based design with 3 tiers:

TIER 1: Validation (12 runs) - Mesh independence, time step, benchmarks
TIER 2: Soil Heterogeneity (30 runs) - κ = kB/su0 study (NOVEL!)
TIER 3: Combined V-H-M Loading (40 runs) - Failure envelope (HIGH IMPACT!)

Total: 82 runs (~40 hours sequential, ~10 hours on 4 cores)

This is ML-ready with meaningful non-dimensional parameters.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import json
from typing import Dict, List, Tuple
from scipy.stats import qmc
import itertools

print("="*70)
print("SMART PARAMETRIC STUDY DESIGN")
print("Physics-Based Sampling for Offshore Mat Foundations")
print("="*70)

# ============================================================================
# TIER 1: VALIDATION MATRIX
# ============================================================================

def tier1_validation() -> pd.DataFrame:
    """
    TIER 1: Validation runs (12 total)

    Purpose:
    - Mesh independence study
    - Time step sensitivity
    - Prandtl benchmark (Nc = 5.14)
    - Liu et al. replication

    Output: Verification of numerical implementation
    """
    print("\n" + "="*70)
    print("TIER 1: VALIDATION MATRIX")
    print("="*70)

    runs = []

    # A. Mesh independence (strip footing - Prandtl)
    print("\n📐 A. Mesh Independence (Prandtl Strip Benchmark)")
    for i, (nx, ny) in enumerate([(60, 30), (80, 40), (100, 50)], 1):
        runs.append({
            'tier': 1,
            'group': 'mesh_independence',
            'run_id': f'T1_mesh_{i}',
            'description': f'Prandtl strip, mesh {nx}×{ny}',
            'geometry': 'strip',
            'width_m': 5.0,
            'thickness_m': 0.5,
            'su_Pa': 6000,
            'su_profile': 'uniform',
            'k_Pa_per_m': 0.0,
            'E_su_ratio': 500,
            'nu': 0.495,
            'nx': nx,
            'ny': ny,
            'dt_s': 1e-5,
            'rate_m_per_s': 0.02,
            'target_settlement_m': 0.15,
            'use_gimp': True,
            'expected_Nc': 5.14,
            'expected_Q_kN': 5.14 * 6000 * 5.0 / 1000,  # Nc * su * B / 1000
        })
    print(f"   Generated {len([r for r in runs if r['group'] == 'mesh_independence'])} runs")

    # B. Liu et al. replication (A-shaped equivalent)
    print("\n📊 B. Liu et al. Replication (Baseline Validation)")
    for i, (nx, ny) in enumerate([(60, 30), (80, 40), (100, 50)], 1):
        EQUIVALENT_WIDTH = 68.4 / 10.0  # Liu foundation
        runs.append({
            'tier': 1,
            'group': 'liu_replication',
            'run_id': f'T1_liu_{i}',
            'description': f'Liu A-shape equiv, mesh {nx}×{ny}',
            'geometry': 'strip_equivalent',
            'width_m': EQUIVALENT_WIDTH,
            'thickness_m': 0.5,
            'su_Pa': 6000,
            'su_profile': 'uniform',
            'k_Pa_per_m': 0.0,
            'E_su_ratio': 500,
            'nu': 0.495,
            'nx': nx,
            'ny': ny,
            'dt_s': 1e-5,
            'rate_m_per_s': 0.01,
            'target_settlement_m': 0.5,
            'use_gimp': True,
            'expected_Q_kN': 2522,  # Liu et al. test result
            'liu_FEM_kN': 2524,
        })
    print(f"   Generated {len([r for r in runs if r['group'] == 'liu_replication'])} runs")

    # C. Time step sensitivity
    print("\n⏱️  C. Time Step Sensitivity")
    for i, dt in enumerate([5e-6, 1e-5, 2e-5], 1):
        runs.append({
            'tier': 1,
            'group': 'timestep_sensitivity',
            'run_id': f'T1_dt_{i}',
            'description': f'Strip footing, dt={dt:.1e}s',
            'geometry': 'strip',
            'width_m': 5.0,
            'thickness_m': 0.5,
            'su_Pa': 6000,
            'su_profile': 'uniform',
            'k_Pa_per_m': 0.0,
            'E_su_ratio': 500,
            'nu': 0.495,
            'nx': 80,
            'ny': 40,
            'dt_s': dt,
            'rate_m_per_s': 0.02,
            'target_settlement_m': 0.15,
            'use_gimp': True,
            'expected_Nc': 5.14,
        })
    print(f"   Generated {len([r for r in runs if r['group'] == 'timestep_sensitivity'])} runs")

    # D. Interface roughness (bonus - optional)
    print("\n🔧 D. Interface Roughness (if time permits)")
    for i, alpha in enumerate([0.0, 0.5, 1.0], 1):
        runs.append({
            'tier': 1,
            'group': 'interface_roughness',
            'run_id': f'T1_alpha_{i}',
            'description': f'Strip footing, α={alpha:.1f}',
            'geometry': 'strip',
            'width_m': 5.0,
            'thickness_m': 0.5,
            'su_Pa': 6000,
            'su_profile': 'uniform',
            'k_Pa_per_m': 0.0,
            'E_su_ratio': 500,
            'nu': 0.495,
            'nx': 80,
            'ny': 40,
            'dt_s': 1e-5,
            'rate_m_per_s': 0.02,
            'target_settlement_m': 0.15,
            'use_gimp': True,
            'interface_roughness': alpha,
            'expected_Nc': 5.14,  # May vary with roughness
        })
    print(f"   Generated {len([r for r in runs if r['group'] == 'interface_roughness'])} runs")

    df = pd.DataFrame(runs)
    print(f"\n✅ TIER 1 Total: {len(df)} validation runs")
    return df


# ============================================================================
# TIER 2: SOIL HETEROGENEITY STUDY (NOVEL!)
# ============================================================================

def tier2_heterogeneity(n_samples=30) -> pd.DataFrame:
    """
    TIER 2: Soil heterogeneity study (30 runs)

    Novel Contribution: MPM for non-homogeneous soil!

    Physical basis:
        su(z) = su0 + k·z

    Non-dimensional group:
        κ = kB/su0  (heterogeneity factor)

    Range: κ ∈ [0, 6] covers field conditions:
        κ = 0: Uniform soil
        κ = 1-2: Typical normally consolidated clay
        κ = 3-6: Strong heterogeneity

    Sampling: Latin Hypercube for efficient coverage

    Output: Nc vs κ design chart for practitioners
    """
    print("\n" + "="*70)
    print("TIER 2: SOIL HETEROGENEITY STUDY (Novel Contribution)")
    print("="*70)

    # Parameter bounds (non-dimensional)
    param_bounds = {
        'kappa': (0.0, 6.0),           # κ = kB/su0 (heterogeneity)
        'su0_norm': (0.5, 2.0),         # su0/su_ref (normalized strength)
        'E_su_ratio': (200, 800),       # E/su (stiffness ratio)
    }

    print(f"\n📊 Latin Hypercube Sampling:")
    print(f"   Parameters: κ (heterogeneity), su0 (normalized), E/su (stiffness)")
    print(f"   Samples: {n_samples}")
    print(f"   Method: Latin Hypercube (efficient space-filling)")

    # Latin Hypercube Sampling
    sampler = qmc.LatinHypercube(d=3)
    lhs_samples = sampler.random(n=n_samples)

    # Scale to parameter bounds
    kappa_samples = lhs_samples[:, 0] * 6.0
    su0_norm_samples = 0.5 + lhs_samples[:, 1] * 1.5
    E_ratio_samples = 200 + lhs_samples[:, 2] * 600

    # Reference values
    su_ref = 6000  # Pa (Liu baseline)
    B_ref = 6.84   # m (equivalent width)

    runs = []
    for i in range(n_samples):
        kappa = kappa_samples[i]
        su0 = su0_norm_samples[i] * su_ref
        k = kappa * su0 / B_ref  # Pa/m
        E = E_ratio_samples[i] * su0

        runs.append({
            'tier': 2,
            'group': 'heterogeneity',
            'run_id': f'T2_hetero_{i+1:02d}',
            'description': f'Heterogeneous, κ={kappa:.2f}',
            'geometry': 'strip_equivalent',
            'width_m': B_ref,
            'thickness_m': 0.5,
            'su_Pa': su0,  # Mudline strength
            'su_profile': 'linear',
            'k_Pa_per_m': k,
            'kappa': kappa,
            'su0_normalized': su0_norm_samples[i],
            'E_su_ratio': E_ratio_samples[i],
            'E_Pa': E,
            'nu': 0.495,
            'nx': 80,
            'ny': 40,
            'dt_s': 1e-5,
            'rate_m_per_s': 0.02,
            'target_settlement_m': 0.15,
            'use_gimp': True,
        })

    df = pd.DataFrame(runs)

    # Summary statistics
    print(f"\n📈 Parameter Ranges:")
    print(f"   κ (heterogeneity): [{kappa_samples.min():.2f}, {kappa_samples.max():.2f}]")
    print(f"   su0 (normalized): [{su0_norm_samples.min():.2f}, {su0_norm_samples.max():.2f}]")
    print(f"   E/su ratio: [{E_ratio_samples.min():.0f}, {E_ratio_samples.max():.0f}]")

    print(f"\n✅ TIER 2 Total: {len(df)} heterogeneity runs")
    print(f"   Output: Nc vs κ design chart")
    return df


# ============================================================================
# TIER 3: COMBINED V-H-M LOADING (HIGH IMPACT!)
# ============================================================================

def tier3_vhm_envelope(n_angles=8, n_v_levels=5) -> pd.DataFrame:
    """
    TIER 3: Combined V-H-M loading failure envelope (40 runs)

    High Impact: What offshore designers actually need!

    Method: Probe tests (displacement-controlled)
    - Apply vertical preload V/V_max
    - Probe in H-M space at different angles
    - Record ultimate H and M at each direction

    Output: 3D failure envelope for design
        - V-H plane (vertical + horizontal)
        - V-M plane (vertical + moment)
        - H-M plane (horizontal + moment)
        - 3D surface for multi-directional loading
    """
    print("\n" + "="*70)
    print("TIER 3: COMBINED V-H-M LOADING (Failure Envelope)")
    print("="*70)

    # V-H-M loading matrix
    V_ratios = np.linspace(0, 1.0, n_v_levels)  # V/V_max
    angles = np.linspace(0, 360, n_angles, endpoint=False)  # Direction in H-M space

    runs = []
    B_ref = 6.84  # m
    su_ref = 6000  # Pa

    print(f"\n🎯 Probe Test Matrix:")
    print(f"   Vertical load levels: {n_v_levels} (V/V_max = {V_ratios.min():.1f} to {V_ratios.max():.1f})")
    print(f"   Probe directions: {n_angles} (0° to 360°)")
    print(f"   Total combinations: {n_v_levels * n_angles}")

    for i_v, V_ratio in enumerate(V_ratios):
        for i_angle, theta_deg in enumerate(angles):
            runs.append({
                'tier': 3,
                'group': 'vhm_envelope',
                'run_id': f'T3_VHM_V{i_v}_θ{i_angle:02d}',
                'description': f'VHM probe: V/Vmax={V_ratio:.2f}, θ={theta_deg:.0f}°',
                'geometry': 'strip_equivalent',
                'width_m': B_ref,
                'thickness_m': 0.5,
                'su_Pa': su_ref,
                'su_profile': 'uniform',
                'k_Pa_per_m': 0.0,
                'E_su_ratio': 500,
                'nu': 0.495,
                'nx': 80,
                'ny': 40,
                'dt_s': 1e-5,
                'use_gimp': True,
                # Loading protocol
                'V_Vmax_ratio': V_ratio,
                'probe_angle_deg': theta_deg,
                'probe_dH_m_per_step': 0.001 * np.cos(np.radians(theta_deg)),
                'probe_dM_rad_per_step': 0.0001 * np.sin(np.radians(theta_deg)),
                'target_settlement_m': 0.2,
                'loading_type': 'probe_test',
            })

    df = pd.DataFrame(runs)
    print(f"\n✅ TIER 3 Total: {len(df)} V-H-M probe runs")
    print(f"   Output: 3D failure envelope for multi-directional loading")
    return df


# ============================================================================
# COMPLETE STUDY ASSEMBLY
# ============================================================================

def generate_complete_study(
    tier1=True,
    tier2=True,
    tier2_samples=30,
    tier3=True,
    tier3_angles=8,
    tier3_v_levels=5
) -> pd.DataFrame:
    """
    Generate complete parametric study

    Returns DataFrame with all runs ready for execution
    """
    print("\n" + "="*70)
    print("COMPLETE PARAMETRIC STUDY GENERATION")
    print("="*70)

    all_runs = []

    if tier1:
        df1 = tier1_validation()
        all_runs.append(df1)

    if tier2:
        df2 = tier2_heterogeneity(n_samples=tier2_samples)
        all_runs.append(df2)

    if tier3:
        df3 = tier3_vhm_envelope(n_angles=tier3_angles, n_v_levels=tier3_v_levels)
        all_runs.append(df3)

    df_complete = pd.concat(all_runs, ignore_index=True)

    # Add sequential run number
    df_complete['run_number'] = range(1, len(df_complete) + 1)

    # Summary
    print("\n" + "="*70)
    print("STUDY SUMMARY")
    print("="*70)

    print(f"\n📊 Breakdown by Tier:")
    for tier in sorted(df_complete['tier'].unique()):
        tier_df = df_complete[df_complete['tier'] == tier]
        print(f"   TIER {tier}: {len(tier_df)} runs")
        for group in tier_df['group'].unique():
            group_count = len(tier_df[tier_df['group'] == group])
            print(f"      └─ {group}: {group_count} runs")

    print(f"\n🎯 Total Runs: {len(df_complete)}")

    # Computational cost estimate
    avg_time_per_run = 0.5  # hours (conservative)
    total_sequential = len(df_complete) * avg_time_per_run
    total_parallel_4 = total_sequential / 4

    print(f"\n⏱️  Estimated Computational Cost:")
    print(f"   Sequential (1 core):  {total_sequential:.1f} hours")
    print(f"   Parallel (4 cores):   {total_parallel_4:.1f} hours")
    print(f"   Average per run:      {avg_time_per_run*60:.0f} minutes")

    return df_complete


# ============================================================================
# ML FEATURE ENGINEERING
# ============================================================================

def prepare_ml_features(df_results: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare features for ML surrogate model

    Input: Results dataframe with simulation outputs
    Output: Feature matrix ready for GPR/XGBoost
    """
    print("\n" + "="*70)
    print("ML FEATURE ENGINEERING")
    print("="*70)

    features = df_results.copy()

    # Non-dimensional groups
    features['t_over_B'] = features['thickness_m'] / features['width_m']
    features['Nc'] = features['Q_ult_kN'] * 1000 / (features['su_Pa'] * features['width_m'])

    # Normalized settlement
    features['delta_u_B'] = features['settlement_at_peak_m'] / features['width_m']

    print(f"\n📊 Feature Set:")
    print(f"   Input Features:")
    print(f"      - κ (kappa): Heterogeneity factor")
    print(f"      - su0_normalized: Normalized mudline strength")
    print(f"      - E_su_ratio: Stiffness ratio")
    print(f"      - V_Vmax_ratio: Vertical load ratio (Tier 3)")
    print(f"      - probe_angle_deg: Loading direction (Tier 3)")

    print(f"\n   Target Variables:")
    print(f"      - Nc: Bearing capacity factor")
    print(f"      - delta_u_B: Normalized settlement")
    print(f"      - Q_ult_kN: Ultimate capacity")

    return features


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Generate complete study
    df_study = generate_complete_study(
        tier1=True,
        tier2=True,
        tier2_samples=30,
        tier3=True,
        tier3_angles=8,
        tier3_v_levels=5
    )

    # Save to file
    output_path = Path('parametric_study_plan.csv')
    df_study.to_csv(output_path, index=False)
    print(f"\n💾 Saved study plan: {output_path}")

    # Also save as JSON for easy reading
    json_path = Path('parametric_study_plan.json')
    df_study.to_json(json_path, orient='records', indent=2)
    print(f"💾 Saved study plan: {json_path}")

    # Create execution script template
    print(f"\n📝 Creating execution script template...")
    with open('run_parametric_study.py', 'w') as f:
        f.write('''#!/usr/bin/env python3
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
    print(f"\\nRunning {run_id} ({idx+1}/{len(df_plan)})...")

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
print(f"\\n✅ Completed! Results saved to parametric_study_results.csv")
''')

    print(f"💾 Created: run_parametric_study.py")

    print(f"\n" + "="*70)
    print("✅ STUDY PLAN GENERATED!")
    print("="*70)
    print(f"\nNext steps:")
    print(f"1. Review: parametric_study_plan.csv")
    print(f"2. Run validation: python3 run_parametric_study.py (filter tier==1)")
    print(f"3. If validation passes: Run full study")
    print(f"4. Train ML surrogate on results")
    print(f"5. Generate design charts")
