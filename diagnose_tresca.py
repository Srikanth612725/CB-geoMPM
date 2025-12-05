#!/usr/bin/env python3
"""
Diagnose Tresca Implementation
Check if plasticity is actually limiting stresses properly
"""

import numpy as np
from mpm_optimized import MPM2D_Optimized

print("="*70)
print("TRESCA DIAGNOSTIC TEST")
print("="*70)

# Test setup
su = 6000  # Pa
B = 5.0

mpm = MPM2D_Optimized(
    domain_x=[0, 30.0],
    domain_y=[0, 15.0],
    nx=60, ny=30,
    su=su, E=500*su, nu=0.495, rho=1600,
    use_gimp=True
)

mpm.add_soil_block([0, 30.0], [0, 10.0], ppc=4)
mpm.add_strip_foundation(15.0, 10.0, B, 0.5, 2500)

print(f"\nsu = {su} Pa")
print(f"Tresca limit: |σ₁-σ₂| ≤ 2·su = {2*su} Pa")
print(f"\nRunning 500 steps...")

# Run simulation
dt = mpm.timestep()
mpm.foundation_velocity = -0.05

for step in range(500):
    mpm.mpm_step(dt)

# Check soil stresses
print(f"\n" + "="*70)
print("STRESS DIAGNOSIS")
print("="*70)

soil_particles = [p for p in mpm.particles if p.material_id == 0]

# Check stress states
n_total = len(soil_particles)
n_elastic = 0
n_yielding = 0
n_violated = 0

max_tau = 0
max_syy = 0

for mp in soil_particles:
    s1 = max(mp.sxx, mp.syy)
    s2 = min(mp.sxx, mp.syy)
    tau_max = abs(s1 - s2) / 2.0

    max_tau = max(max_tau, tau_max)
    max_syy = max(max_syy, abs(mp.syy))

    # Check yield criterion
    f = abs(s1 - s2) - 2*su

    if f < -0.05*su:  # Clearly elastic
        n_elastic += 1
    elif abs(f) <= 0.05*su:  # At yield surface
        n_yielding += 1
    else:  # Violating yield criterion!
        n_violated += 1

print(f"\n📊 Soil Particles Analysis:")
print(f"   Total soil particles: {n_total}")
print(f"   Elastic (f < 0):      {n_elastic} ({100*n_elastic/n_total:.1f}%)")
print(f"   At yield (f ≈ 0):     {n_yielding} ({100*n_yielding/n_total:.1f}%)")
print(f"   VIOLATED (f > 0):     {n_violated} ({100*n_violated/n_total:.1f}%)")

print(f"\n📐 Stress Magnitudes:")
print(f"   Max τ_max:            {max_tau:.0f} Pa")
print(f"   Tresca limit (su):    {su:.0f} Pa")
print(f"   Ratio (τ_max/su):     {max_tau/su:.2f}")
print(f"   Max |σyy|:            {max_syy:.0f} Pa")

# Check interface particles specifically
found_y = [mpm.particles[i].y for i in mpm.foundation_indices]
found_x = [mpm.particles[i].x for i in mpm.foundation_indices]
foundation_base = min(found_y)
x_min_found, x_max_found = min(found_x), max(found_x)
interface_thickness = 0.5 * mpm.dy

interface_particles = []
for mp in mpm.particles:
    if mp.material_id == 0:
        if (foundation_base - interface_thickness < mp.y < foundation_base):
            if x_min_found - 0.5*mpm.dx < mp.x < x_max_found + 0.5*mpm.dx:
                interface_particles.append(mp)

print(f"\n🔍 Interface Particles (bearing capacity zone):")
print(f"   Count: {len(interface_particles)}")

if interface_particles:
    interface_pressures = [-mp.syy for mp in interface_particles]
    avg_pressure = np.mean(interface_pressures)
    max_pressure = max(interface_pressures)

    print(f"   Avg pressure:         {avg_pressure:.0f} Pa")
    print(f"   Max pressure:         {max_pressure:.0f} Pa")
    print(f"   Avg / (Nc·su):        {avg_pressure/(5.14*su):.2f}")
    print(f"   Max / (Nc·su):        {max_pressure/(5.14*su):.2f}")

    # Expected bearing pressure ≈ Nc·su = 5.14 × 6000 = 30,840 Pa
    expected_pressure = 5.14 * su
    print(f"\n   Expected (Nc·su):     {expected_pressure:.0f} Pa")
    print(f"   Ratio (actual/expected): {avg_pressure/expected_pressure:.2f}x")

# Calculate reported bearing capacity
q_2d = mpm.calculate_bearing_capacity() / 1000  # kN/m
q_expected = 5.14 * su * B / 1000  # kN/m

print(f"\n📏 Bearing Capacity:")
print(f"   Calculated Q:         {q_2d:.0f} kN/m")
print(f"   Expected Q (Prandtl): {q_expected:.0f} kN/m")
print(f"   Ratio:                {q_2d/q_expected:.2f}x")

# Assessment
print(f"\n" + "="*70)
print("ASSESSMENT")
print("="*70)

if n_violated > n_total * 0.01:  # More than 1% violated
    print(f"❌ TRESCA NOT WORKING!")
    print(f"   {n_violated} particles ({100*n_violated/n_total:.1f}%) violate yield criterion")
    print(f"   tresca_return_mapping() is NOT limiting stresses properly")
elif max_tau > 1.1 * su:
    print(f"⚠️  TRESCA PARTIALLY WORKING")
    print(f"   Some particles exceed su by {(max_tau/su-1)*100:.1f}%")
elif avg_pressure > 10 * su:
    print(f"⚠️  BEARING PRESSURE TOO HIGH")
    print(f"   Interface pressure {avg_pressure/su:.1f}×su (expected ≈5×su)")
    print(f"   Problem in bearing capacity calculation or stress integration")
else:
    print(f"✅ TRESCA APPEARS TO BE WORKING")
    print(f"   Stresses properly limited to ≤ su")
    print(f"   Check bearing capacity calculation separately")
