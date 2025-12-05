#!/usr/bin/env python3
"""
Test: Verify standard MPM (use_gimp=False) gives correct Liu case result
"""

import numpy as np
from mpm_optimized import MPM2D_Optimized
import time

print("="*70)
print("LIU CASE TEST - Standard MPM vs GIMP")
print("="*70)

# Liu et al. (2020) validation case
su = 30000  # Pa (30 kPa)
width = 6.84  # m (equivalent width for A-mat: 68.4m²/10m = 6.84m)
thickness = 0.5  # m
E = 100 * su  # Stiffness
nu = 0.495  # Nearly incompressible
rho_soil = 1600  # kg/m³

# Expected results
Q_target = 2522  # kN (from Liu et al.)
Q_validation = 1957  # kN (from mpm_validation.py - 22% error)

print(f"\nValidation Case:")
print(f"  Foundation: {width}m x {thickness}m")
print(f"  Soil: su = {su/1000:.0f} kPa, E = {E/1e6:.0f} MPa")
print(f"\nExpected Results:")
print(f"  Liu et al. target: {Q_target} kN")
print(f"  mpm_validation.py: {Q_validation} kN (22% error)")

def run_liu_test(use_gimp=False):
    """Run Liu case with specified MPM variant"""

    print(f"\n{'='*70}")
    print(f"Testing with {'GIMP' if use_gimp else 'Standard MPM'}")
    print(f"{'='*70}")

    # Domain setup (scaled for faster testing)
    Lx, Ly = 30.0, 15.0
    nx, ny = 60, 30  # Coarse for speed

    mpm = MPM2D_Optimized(
        domain_x=[0, Lx],
        domain_y=[0, Ly],
        nx=nx,
        ny=ny,
        su=su,
        E=E,
        nu=nu,
        rho=rho_soil,
        use_gimp=use_gimp
    )

    # Add soil block
    mpm.add_soil_block([0, Lx], [0, 10.0], ppc=4)

    # Add foundation
    mpm.add_strip_foundation(
        center_x=Lx/2,
        y_base=10.0,
        width=width,
        thickness=thickness,
        density=2500
    )

    print(f"   Particles: {len(mpm.particles)} ({len(mpm.foundation_indices)} foundation)")

    # Run simulation
    dt = mpm.timestep()
    mpm.foundation_velocity = -0.0025  # Moderate settlement rate

    max_steps = 5000
    target_settlement = 0.05  # 50mm

    settlements = []
    loads = []
    step = 0

    print(f"\n   Running simulation...")
    t0 = time.time()

    while step < max_steps:
        mpm.mpm_step(dt)
        step += 1

        # Track settlement
        current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])
        settlement = mpm.foundation_y0 - current_y

        if step % 1000 == 0:
            q = mpm.calculate_bearing_capacity() / 1000  # kN/m
            settlements.append(settlement)
            loads.append(q)
            print(f"   Step {step:4d} | s={settlement*1000:.1f}mm | q={q:.0f} kN/m")

        if settlement >= target_settlement:
            break

    elapsed = time.time() - t0

    if loads:
        q_ult = max(loads)
        error_vs_target = abs(q_ult - Q_target) / Q_target * 100
        error_vs_validation = abs(q_ult - Q_validation) / Q_validation * 100

        print(f"\n   Results:")
        print(f"      Q_ultimate: {q_ult:.0f} kN/m")
        print(f"      Error vs Liu target: {error_vs_target:.0f}%")
        print(f"      Error vs validation: {error_vs_validation:.0f}%")
        print(f"      Time: {elapsed:.1f}s")

        return q_ult
    else:
        print(f"\n   ❌ No results")
        return None

# Test 1: Standard MPM
print(f"\n{'='*70}")
print("TEST 1: STANDARD MPM (use_gimp=False)")
print(f"{'='*70}")
q_standard = run_liu_test(use_gimp=False)

# Test 2: GIMP
print(f"\n{'='*70}")
print("TEST 2: GIMP (use_gimp=True)")
print(f"{'='*70}")
q_gimp = run_liu_test(use_gimp=True)

# Summary
print(f"\n{'='*70}")
print("RESULTS SUMMARY")
print(f"{'='*70}")
print(f"\nLiu et al. target:     {Q_target} kN")
print(f"mpm_validation.py:     {Q_validation} kN (22% error)")

if q_standard:
    err_std = abs(q_standard - Q_target) / Q_target * 100
    match_validation = abs(q_standard - Q_validation) / Q_validation * 100
    print(f"Standard MPM:          {q_standard:.0f} kN ({err_std:.0f}% error)")
    print(f"  → Matches validation: {match_validation:.0f}% difference")

if q_gimp:
    err_gimp = abs(q_gimp - Q_target) / Q_target * 100
    print(f"GIMP:                  {q_gimp:.0f} kN ({err_gimp:.0f}% error)")

# Diagnosis
print(f"\n{'='*70}")
print("DIAGNOSIS")
print(f"{'='*70}")

if q_standard and q_gimp:
    if abs(q_standard - Q_validation) / Q_validation < 0.10:
        print(f"✅ Standard MPM matches mpm_validation.py (within 10%)")
        print(f"✅ SAFE TO USE for parametric study!")
    else:
        print(f"⚠️  Standard MPM differs from mpm_validation.py")
        print(f"   Need to investigate further")

    if q_gimp > Q_target * 1.2:
        print(f"❌ GIMP still shows overcapacity issue")
    else:
        print(f"✅ GIMP working correctly")

print(f"\n{'='*70}")
