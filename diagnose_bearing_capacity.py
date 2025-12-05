#!/usr/bin/env python3
"""
Diagnose why bearing capacity returns 0
"""

import numpy as np
from mpm_optimized import MPM2D_Optimized

print("="*70)
print("BEARING CAPACITY DIAGNOSTIC")
print("="*70)

# Simple setup
su = 6000
B = 5.0
E = 100 * su
nu = 0.495
rho = 1600

mpm = MPM2D_Optimized(
    domain_x=[0, 30],
    domain_y=[0, 15],
    nx=50,
    ny=25,
    su=su,
    E=E,
    nu=nu,
    rho=rho,
    use_gimp=False
)

mpm.add_soil_block([0, 30], [0, 10], ppc=4)
mpm.add_strip_foundation(center_x=15, y_base=10, width=B, thickness=0.5, density=2500)

print(f"\nSetup:")
print(f"  Total particles: {len(mpm.particles)}")
print(f"  Foundation particles: {len(mpm.foundation_indices)}")
print(f"  Grid spacing: dx={mpm.dx:.3f}m, dy={mpm.dy:.3f}m")

# Run a few steps
dt = mpm.timestep()
mpm.foundation_velocity = -0.05

print(f"\nRunning 500 steps...")
for step in range(500):
    mpm.mpm_step(dt)

# Check foundation position
found_y = [mpm.particles[i].y for i in mpm.foundation_indices]
found_x = [mpm.particles[i].x for i in mpm.foundation_indices]
foundation_base = min(found_y)
foundation_top = max(found_y)
x_min = min(found_x)
x_max = max(found_x)
foundation_width = x_max - x_min

print(f"\nFoundation after 500 steps:")
print(f"  Base y: {foundation_base:.3f}m")
print(f"  Top y: {foundation_top:.3f}m")
print(f"  X range: {x_min:.3f} - {x_max:.3f}m")
print(f"  Width: {foundation_width:.3f}m")
print(f"  Settlement: {mpm.foundation_y0 - np.mean(found_y):.4f}m")

# Check interface
interface_thickness = 0.5 * mpm.dy
interface_y_min = foundation_base - interface_thickness
interface_y_max = foundation_base

print(f"\nInterface zone:")
print(f"  Thickness: {interface_thickness:.3f}m")
print(f"  Y range: {interface_y_min:.3f} - {interface_y_max:.3f}m")
print(f"  X range: {x_min-0.5*mpm.dx:.3f} - {x_max+0.5*mpm.dx:.3f}m")

# Find soil particles in interface
interface_particles = []
for i, mp in enumerate(mpm.particles):
    if mp.material_id == 0:  # Soil
        if (interface_y_min < mp.y < interface_y_max):
            if (x_min - 0.5*mpm.dx < mp.x < x_max + 0.5*mpm.dx):
                interface_particles.append(i)

print(f"\nSoil particles in interface: {len(interface_particles)}")

if len(interface_particles) > 0:
    print(f"\nInterface particle details:")
    print(f"  {'ID':<6} {'X(m)':<8} {'Y(m)':<8} {'syy(Pa)':<10} {'-syy>0?':<8}")
    print("-"*50)
    for i in interface_particles[:10]:  # Show first 10
        mp = mpm.particles[i]
        pressure = -mp.syy
        print(f"  {i:<6} {mp.x:<8.3f} {mp.y:<8.3f} {mp.syy:<10.1f} {pressure>0}")

    pressures = [-mpm.particles[i].syy for i in interface_particles]
    positive_pressures = [p for p in pressures if p > 0]

    print(f"\nPressure statistics:")
    print(f"  Particles with positive -syy: {len(positive_pressures)} / {len(interface_particles)}")
    if len(positive_pressures) > 0:
        print(f"  Mean pressure: {np.mean(positive_pressures):.1f} Pa")
        print(f"  Max pressure: {np.max(positive_pressures):.1f} Pa")
else:
    print("\n❌ NO PARTICLES IN INTERFACE ZONE!")
    print("\nChecking nearby soil particles...")

    # Find nearest soil particles to foundation base
    soil_particles = [(i, mp) for i, mp in enumerate(mpm.particles) if mp.material_id == 0]
    distances = [(i, abs(mp.y - foundation_base)) for i, mp in soil_particles]
    distances.sort(key=lambda x: x[1])

    print(f"\nNearest 10 soil particles to foundation base (y={foundation_base:.3f}):")
    print(f"  {'ID':<6} {'X(m)':<8} {'Y(m)':<8} {'Dist(m)':<8} {'syy(Pa)':<10}")
    print("-"*55)
    for i, dist in distances[:10]:
        mp = mpm.particles[i]
        print(f"  {i:<6} {mp.x:<8.3f} {mp.y:<8.3f} {dist:<8.4f} {mp.syy:<10.1f}")

# Try calculating bearing capacity
q = mpm.calculate_bearing_capacity()
print(f"\n{'='*70}")
print(f"BEARING CAPACITY RESULT: {q/1000:.1f} kN/m")
print(f"{'='*70}")

if q == 0:
    print("\n❌ PROBLEM IDENTIFIED:")
    if len(interface_particles) == 0:
        print("  No soil particles found in interface zone!")
        print("\nPossible causes:")
        print("  1. Interface thickness too small")
        print("  2. Soil particles displaced/crushed out of zone")
        print("  3. Foundation settled too much")
        print("\nSuggestions:")
        print("  1. Increase interface thickness (try 1.0 * dy or 1.5 * dy)")
        print("  2. Use finer mesh (more particles at interface)")
        print("  3. Check at earlier settlement (before particles displaced)")
    else:
        print("  Particles in interface but all have negative or zero stress!")
        print("\nPossible causes:")
        print("  1. Stress not properly calculated")
        print("  2. Sign convention issue")
        print("  3. Plastic failure not developing")
else:
    print(f"\n✅ Bearing capacity calculated successfully!")
    print(f"   Equivalent to {q/1000:.0f} kN/m")
