#!/usr/bin/env python3
"""
Quick Prandtl Test - Faster version for immediate verification
"""

import numpy as np
from mpm_optimized import MPM2D_Optimized
import time

print("="*70)
print("QUICK PRANDTL VERIFICATION TEST")
print("="*70)

# Analytical solution
su = 6000  # Pa
B = 5.0    # m
Nc_theory = 2.0 + np.pi
Q_prandtl = su * Nc_theory * B / 1000  # kN/m

print(f"\n📐 Analytical: Q = {Q_prandtl:.0f} kN/m (Nc = {Nc_theory:.3f})")

# Coarser/faster MPM simulation
print(f"\n🖥️  MPM Simulation (coarse/fast):")

mpm = MPM2D_Optimized(
    domain_x=[0, 30.0],
    domain_y=[0, 15.0],
    nx=60,  # Coarser
    ny=30,  # Coarser
    su=su,
    E=500*su,
    nu=0.495,
    rho=1600,
    use_gimp=True
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

print(f"   Particles: {len(mpm.particles)}")

# Run with faster rate
dt = mpm.timestep()
mpm.foundation_velocity = -0.05  # FAST settlement rate

settlements = []
loads = []
step = 0
max_steps = 2000

print(f"\n   Running {max_steps} steps...")
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
print(f"\n   Done in {elapsed:.1f}s")

# Results
if loads:
    q_ult = max(loads)
    Nc_mpm = (q_ult * 1000) / (su * B)
    error = abs(q_ult - Q_prandtl) / Q_prandtl * 100

    print(f"\n📊 RESULTS:")
    print(f"   Q_prandtl: {Q_prandtl:.0f} kN/m")
    print(f"   Q_MPM:     {q_ult:.0f} kN/m")
    print(f"   Nc_theory: {Nc_theory:.3f}")
    print(f"   Nc_MPM:    {Nc_mpm:.3f}")
    print(f"   Error:     {error:.1f}%")

    # Check for plasticity
    n_plastic = 0
    for mp in mpm.particles:
        if mp.material_id == 0:
            s1 = max(mp.sxx, mp.syy)
            s2 = min(mp.sxx, mp.syy)
            if abs(s1 - s2) >= 0.95 * 2 * su:
                n_plastic += 1

    print(f"\n🔍 Plasticity Check:")
    print(f"   Yielded particles: {n_plastic}/{sum(1 for p in mpm.particles if p.material_id==0)}")
    print(f"   Plasticity active: {'YES' if n_plastic > 10 else 'NO'}")

    if error < 15:
        print(f"\n✅ TEST PASSED! Tresca is working.")
    else:
        print(f"\n⚠️  TEST MARGINAL - Error >15%")
else:
    print(f"\n❌ NO RESULTS - Check bearing capacity calculation")
