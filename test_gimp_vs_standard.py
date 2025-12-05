#!/usr/bin/env python3
"""
Test: GIMP vs Standard MPM for Prandtl Benchmark
Isolate whether GIMP implementation is causing overcapacity bug
"""

import numpy as np
from mpm_optimized import MPM2D_Optimized
import time

print("="*70)
print("GIMP vs STANDARD MPM COMPARISON")
print("="*70)

# Prandtl analytical solution
su = 6000  # Pa
B = 5.0    # m
Nc_prandtl = 2 + np.pi  # 5.142
Q_analytical = su * B * Nc_prandtl / 1000  # kN/m
print(f"\n📐 Analytical (Prandtl):")
print(f"   Nc = {Nc_prandtl:.3f}")
print(f"   Q = {Q_analytical:.0f} kN/m")

def run_test(use_gimp=True, max_steps=400):
    """Run Prandtl test with specified MPM variant"""

    print(f"\n{'='*70}")
    print(f"Testing with {'GIMP' if use_gimp else 'Standard MPM'}")
    print(f"{'='*70}")

    mpm = MPM2D_Optimized(
        domain_x=[0, 30.0],
        domain_y=[0, 15.0],
        nx=60,
        ny=30,
        su=su,
        E=500*su,
        nu=0.495,
        rho=1600,
        use_gimp=use_gimp
    )

    # Add soil
    mpm.add_soil_block([0, 30.0], [0, 10.0], ppc=4)

    # Add foundation
    mpm.add_strip_foundation(
        center_x=15.0,
        y_base=10.0,
        width=B,
        thickness=0.5,
        density=2500
    )

    # Run simulation
    dt = mpm.timestep()
    mpm.foundation_velocity = -0.05  # Fast settlement

    settlements = []
    loads = []
    step = 0

    t0 = time.time()
    while step < max_steps:
        mpm.mpm_step(dt)
        step += 1

        current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])
        settlement = mpm.foundation_y0 - current_y

        if step % 100 == 0:
            q_2d = mpm.calculate_bearing_capacity() / 1000
            settlements.append(settlement)
            loads.append(q_2d)
            print(f"   Step {step:4d} | s={settlement*1000:.1f}mm | q={q_2d:.0f} kN/m")

        if settlement >= 0.05:  # Stop at 50mm
            break

    elapsed = time.time() - t0

    if loads:
        q_ult = max(loads)
        Nc_mpm = (q_ult * 1000) / (su * B)

        # Check plasticity
        n_plastic = 0
        for mp in mpm.particles:
            if mp.material_id == 0:
                s1 = max(mp.sxx, mp.syy)
                s2 = min(mp.sxx, mp.syy)
                if abs(s1 - s2) >= 0.95 * 2 * su:
                    n_plastic += 1

        print(f"\n   Results:")
        print(f"      Q_MPM: {q_ult:.0f} kN/m (Nc={Nc_mpm:.3f})")
        print(f"      Error: {abs(q_ult-Q_analytical)/Q_analytical*100:.0f}%")
        print(f"      Plastic particles: {n_plastic}")
        print(f"      Time: {elapsed:.1f}s")

        return q_ult, Nc_mpm, n_plastic
    else:
        print(f"\n   ❌ No results")
        return None, None, None

# Test 1: Standard MPM
q_standard, Nc_standard, plastic_standard = run_test(use_gimp=False, max_steps=400)

# Test 2: GIMP
q_gimp, Nc_gimp, plastic_gimp = run_test(use_gimp=True, max_steps=400)

# Comparison
print(f"\n{'='*70}")
print("RESULTS COMPARISON")
print(f"{'='*70}")
print(f"\nAnalytical (Prandtl):")
print(f"   Q = {Q_analytical:.0f} kN/m")
print(f"   Nc = {Nc_prandtl:.3f}")

if q_standard:
    print(f"\nStandard MPM:")
    print(f"   Q = {q_standard:.0f} kN/m (Nc={Nc_standard:.3f})")
    print(f"   Error: {abs(q_standard-Q_analytical)/Q_analytical*100:.0f}%")
    print(f"   Plastic particles: {plastic_standard}")

if q_gimp:
    print(f"\nGIMP:")
    print(f"   Q = {q_gimp:.0f} kN/m (Nc={Nc_gimp:.3f})")
    print(f"   Error: {abs(q_gimp-Q_analytical)/Q_analytical*100:.0f}%")
    print(f"   Plastic particles: {plastic_gimp}")

# Diagnosis
print(f"\n{'='*70}")
print("DIAGNOSIS")
print(f"{'='*70}")

if q_standard and q_gimp:
    err_standard = abs(q_standard - Q_analytical) / Q_analytical * 100
    err_gimp = abs(q_gimp - Q_analytical) / Q_analytical * 100

    if err_standard < err_gimp * 0.8:
        print(f"🔍 GIMP is making it worse!")
        print(f"   Standard MPM error: {err_standard:.0f}%")
        print(f"   GIMP error: {err_gimp:.0f}%")
        print(f"   → Bug is GIMP-specific")
    elif err_gimp < err_standard * 0.8:
        print(f"🔍 GIMP is better (but both wrong)")
        print(f"   Standard MPM error: {err_standard:.0f}%")
        print(f"   GIMP error: {err_gimp:.0f}%")
        print(f"   → Bug is in base MPM, not GIMP")
    else:
        print(f"🔍 Both methods have similar error")
        print(f"   Standard MPM error: {err_standard:.0f}%")
        print(f"   GIMP error: {err_gimp:.0f}%")
        print(f"   → Bug affects both equally")

    if min(q_standard, q_gimp) > Q_analytical * 2:
        print(f"\n⚠️  Both methods show >2x overcapacity!")
        print(f"   Root cause is NOT the interpolation scheme")
        print(f"\nLikely issues:")
        print(f"   1. Elastic stress update formula")
        print(f"   2. Tresca return mapping")
        print(f"   3. Initial stress state")
        print(f"   4. Material stiffness (K, G calculation)")
        print(f"   5. Stress integration order")
else:
    print("Insufficient data for diagnosis")

print(f"\n{'='*70}")
