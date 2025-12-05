#!/usr/bin/env python3
"""
Check if settlement rate is quasi-static (no dynamic effects)

Criterion: Inertial forces << Soil strength
F_inertial / F_soil << 1

F_inertial = ρ * volume * acceleration = ρ * A * L * (v²/L) = ρ * A * v²
F_soil = su * A

Ratio = (ρ * v²) / su << 1

For quasi-static: Ratio < 0.01 (1% of soil strength)
"""

import numpy as np

# Soil properties
su = 30000  # Pa (30 kPa)
rho = 1600  # kg/m³

print("="*70)
print("QUASI-STATIC SETTLEMENT RATE CHECK")
print("="*70)

print(f"\nSoil properties:")
print(f"  Undrained strength: {su/1000:.0f} kPa")
print(f"  Density: {rho} kg/m³")

# Test different settlement rates
rates = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]

print(f"\n{'Rate (m/s)':<12} {'Inertial/Strength':<20} {'Status':<20}")
print("-"*70)

for v in rates:
    # Inertial stress = ρ * v²
    inertial_stress = rho * v**2

    # Ratio to soil strength
    ratio = inertial_stress / su

    # Quasi-static criterion
    if ratio < 0.001:
        status = "✅ Excellent (QS)"
    elif ratio < 0.01:
        status = "✅ Good (QS)"
    elif ratio < 0.05:
        status = "⚠️  Marginal"
    else:
        status = "❌ Dynamic!"

    print(f"{v:<12.3f} {ratio:<20.6f} {status:<20}")

print("\n" + "="*70)
print("RECOMMENDATION")
print("="*70)

# Find maximum quasi-static rate
v_max_excellent = np.sqrt(0.001 * su / rho)
v_max_good = np.sqrt(0.01 * su / rho)

print(f"\nMaximum quasi-static rates:")
print(f"  Excellent (ratio < 0.001): v < {v_max_excellent:.3f} m/s")
print(f"  Good (ratio < 0.01):       v < {v_max_good:.3f} m/s")

print(f"\nCurrent rates in code:")
print(f"  Prandtl test: 0.02 m/s  → Ratio = {rho*0.02**2/su:.6f} (✅ Good)")
print(f"  Liu test:     0.01 m/s  → Ratio = {rho*0.01**2/su:.6f} (✅ Excellent)")

print(f"\nRecommended FASTER rate:")
print(f"  Try: {v_max_good:.3f} m/s (10x speedup!)")
print(f"  This maintains quasi-static conditions")

# Time calculation
target_settlement = 0.15  # m (150mm for Prandtl)

print(f"\n{'='*70}")
print("TIME TO REACH {target_settlement*1000:.0f}mm SETTLEMENT")
print("="*70)

for rate in [0.01, 0.02, 0.05, 0.1, v_max_good]:
    time_real = target_settlement / rate  # seconds
    dt = 0.0006  # timestep
    num_steps = int(time_real / dt)

    # Estimate computational time (rough: 0.01s per step for 10k particles)
    comp_time = num_steps * 0.01 / 60  # minutes

    print(f"\nRate = {rate:.3f} m/s:")
    print(f"  Real time: {time_real:.1f}s")
    print(f"  Steps needed: {num_steps:,}")
    print(f"  Computation: ~{comp_time:.1f} min")
