#!/usr/bin/env python3
"""
Prandtl Benchmark Test - Verify Tresca Plasticity
==================================================

Tests undrained clay bearing capacity against Prandtl analytical solution:
    q_ult = su * Nc
    Nc = 2 + π = 5.14 for strip foundation on undrained clay (φ=0)

This validates:
1. Tresca plasticity is working correctly
2. Stress integration is accurate
3. Bearing capacity calculation is correct
"""

import numpy as np
import matplotlib.pyplot as plt
from mpm_optimized import MPM2D_Optimized, LIU_DATA
import time

print("="*70)
print("PRANDTL BENCHMARK TEST")
print("Testing: Strip Foundation on Uniform Undrained Clay")
print("="*70)

# Analytical solution
def prandtl_strip_undrained(su, B, L=1.0):
    """
    Prandtl bearing capacity for strip foundation on undrained clay

    q_ult = su * Nc
    Nc = 2 + π = 5.14 for undrained conditions (φ=0)

    Returns ultimate load per unit length (kN/m)
    """
    Nc = 2.0 + np.pi
    q_ult = su * Nc  # Pa
    Q_per_length = q_ult * B / 1000  # kN/m
    return Q_per_length, Nc

# Test parameters
su_test = 6000  # Pa (same as Liu et al.)
B_test = 5.0    # m (strip width)
E_test = 500 * su_test
nu_test = 0.495

# Analytical prediction
Q_prandtl, Nc_theory = prandtl_strip_undrained(su_test, B_test)
print(f"\n📐 ANALYTICAL SOLUTION (Prandtl):")
print(f"   su = {su_test/1000:.1f} kPa")
print(f"   B = {B_test} m")
print(f"   Nc (theory) = {Nc_theory:.3f}")
print(f"   q_ult = su × Nc = {su_test * Nc_theory / 1000:.1f} kPa")
print(f"   Q_ult = {Q_prandtl:.0f} kN/m")

# MPM simulation
print(f"\n🖥️  MPM SIMULATION:")
print(f"   Mesh: 80×40")
print(f"   Particles per cell: 4")
print(f"   GIMP: Enabled")

# Create MPM solver
domain_width = B_test * 6.0
domain_height = 15.0
soil_surface = 10.0

mpm = MPM2D_Optimized(
    domain_x=[0, domain_width],
    domain_y=[0, domain_height],
    nx=80,
    ny=40,
    su=su_test,
    E=E_test,
    nu=nu_test,
    rho=1600,
    use_gimp=True
)

# Add soil
mpm.add_soil_block([0, domain_width], [0, soil_surface], ppc=4)

# Add strip foundation
center_x = domain_width / 2.0
mpm.add_strip_foundation(
    center_x=center_x,
    y_base=soil_surface,
    width=B_test,
    thickness=0.5,
    density=2500
)

print(f"\n   Total particles: {len(mpm.particles)}")
print(f"   Starting simulation...")

# Run test with moderate parameters
dt = mpm.timestep()
print(f"   Time step: {dt:.6f} s")

settlement_rate = 0.02  # m/s (faster)
target_settlement = 0.15  # m (moderate)
mpm.foundation_velocity = -settlement_rate

settlements = []
loads = []
times = []
next_out = 0.0
interval = 0.01

print(f"   Settlement rate: {settlement_rate} m/s")
print(f"   Target settlement: {target_settlement} m")

t0 = time.time()
step = 0
max_steps = 10000

# Check for plasticity activation
plasticity_active = False
first_plastic_settlement = None

while step < max_steps:
    mpm.mpm_step(dt)
    step += 1

    current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])
    settlement = mpm.foundation_y0 - current_y

    if mpm.time >= next_out:
        q_2d = mpm.calculate_bearing_capacity() / 1000  # kN/m
        settlements.append(settlement)
        loads.append(q_2d)
        times.append(mpm.time)
        next_out += interval

        # Check if any soil particles are yielding
        if not plasticity_active:
            for mp in mpm.particles:
                if mp.material_id == 0:  # Soil
                    s1 = max(mp.sxx, mp.syy)
                    s2 = min(mp.sxx, mp.syy)
                    tau_max = abs(s1 - s2) / 2.0
                    if tau_max >= 0.95 * su_test:  # Nearly yielding
                        plasticity_active = True
                        first_plastic_settlement = settlement
                        print(f"\n   ✓ Plasticity activated at settlement = {settlement*1000:.1f} mm")
                        break

        if step % 200 == 0:
            print(f"   Step {step:5d} | s={settlement*1000:.1f}mm | q={q_2d:.0f} kN/m", end='\r')

    if settlement >= target_settlement:
        print(f"\n   ✓ Target settlement reached")
        break

elapsed = time.time() - t0
print(f"\n   Completed in {elapsed:.1f}s ({step/elapsed:.1f} steps/s)")

# Analysis
settlements = np.array(settlements)
loads = np.array(loads)

# Ultimate load (peak or plateau)
q_ult_mpm = np.max(loads)
Nc_mpm = (q_ult_mpm * 1000) / (su_test * B_test)

# Error
error_pct = abs(q_ult_mpm - Q_prandtl) / Q_prandtl * 100

# Results
print(f"\n" + "="*70)
print("RESULTS")
print("="*70)
print(f"\n📊 Bearing Capacity:")
print(f"   Prandtl (analytical): {Q_prandtl:.0f} kN/m")
print(f"   MPM (numerical):      {q_ult_mpm:.0f} kN/m")
print(f"   Error:                {error_pct:.1f}%")

print(f"\n📐 Bearing Capacity Factor:")
print(f"   Nc (theory):  {Nc_theory:.3f}")
print(f"   Nc (MPM):     {Nc_mpm:.3f}")
print(f"   Ratio:        {Nc_mpm/Nc_theory:.3f}")

if plasticity_active:
    print(f"\n✅ Plasticity Status:")
    print(f"   Activated: YES")
    print(f"   First yield at: {first_plastic_settlement*1000:.1f} mm settlement")
else:
    print(f"\n❌ Plasticity Status:")
    print(f"   Activated: NO (PROBLEM!)")
    print(f"   This suggests purely elastic behavior")

# Assessment
print(f"\n🎯 Assessment:")
if error_pct < 5:
    print(f"   ✅ EXCELLENT agreement (<5% error)")
    print(f"   ✅ Tresca plasticity working correctly")
elif error_pct < 10:
    print(f"   ✓  GOOD agreement (<10% error)")
    print(f"   ✓  Acceptable for MPM discretization")
elif error_pct < 20:
    print(f"   ⚠️  MODERATE error (10-20%)")
    print(f"   → May need finer mesh or parameter tuning")
else:
    print(f"   ❌ LARGE error (>20%)")
    print(f"   → Check Tresca implementation or mesh quality")

# Plot
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Load-settlement curve
ax1 = axes[0]
ax1.plot(settlements * 1000, loads, 'b-', lw=2, label='MPM')
ax1.axhline(Q_prandtl, color='r', ls='--', lw=2, label=f'Prandtl ({Q_prandtl:.0f} kN/m)')
ax1.axvline(first_plastic_settlement * 1000 if plasticity_active else 0,
            color='orange', ls=':', lw=1.5, alpha=0.7, label='Plasticity onset')
ax1.set_xlabel('Settlement (mm)', fontweight='bold')
ax1.set_ylabel('Load (kN/m)', fontweight='bold')
ax1.set_title('Load-Settlement Curve', fontweight='bold')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Normalized curve
ax2 = axes[1]
ax2.plot(settlements / B_test, loads / Q_prandtl, 'b-', lw=2)
ax2.axhline(1.0, color='r', ls='--', lw=2, label='Prandtl prediction')
ax2.set_xlabel('Settlement / B', fontweight='bold')
ax2.set_ylabel('q / q_Prandtl', fontweight='bold')
ax2.set_title('Normalized Bearing Capacity', fontweight='bold')
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('prandtl_benchmark.png', dpi=150, bbox_inches='tight')
print(f"\n💾 Saved: prandtl_benchmark.png")

# Save results
results = {
    'test': 'Prandtl strip foundation benchmark',
    'su_Pa': su_test,
    'B_m': B_test,
    'Nc_theory': float(Nc_theory),
    'Nc_MPM': float(Nc_mpm),
    'Q_Prandtl_kN_per_m': float(Q_prandtl),
    'Q_MPM_kN_per_m': float(q_ult_mpm),
    'error_percent': float(error_pct),
    'plasticity_activated': plasticity_active,
    'first_plastic_settlement_m': float(first_plastic_settlement) if plasticity_active else None,
}

import json
with open('prandtl_benchmark_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"💾 Saved: prandtl_benchmark_results.json")

# Return code based on accuracy
if error_pct < 10:
    print(f"\n✅ BENCHMARK PASSED (error < 10%)")
    exit(0)
elif error_pct < 20:
    print(f"\n⚠️  BENCHMARK MARGINAL (10% < error < 20%)")
    exit(1)
else:
    print(f"\n❌ BENCHMARK FAILED (error > 20%)")
    exit(2)
