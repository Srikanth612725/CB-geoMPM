#!/usr/bin/env python3
"""
FAST Test: Tangent Method with Optimized Parameters
- Rate: 0.10 m/s (10x faster, still quasi-static)
- Target: 0.10 m (100mm, sufficient for failure)
- Steps: ~3,700 instead of 186,000!
"""

import numpy as np
from mpm_optimized import run_optimized_validation

print("="*70)
print("FAST TANGENT METHOD TEST (Optimized Parameters)")
print("="*70)

# Run Liu case with FAST optimized parameters
print("\nRunning Liu validation case with optimized settings...")
print("  Rate: 0.10 m/s (10x faster)")
print("  Target: 0.10 m (100mm settlement)")
print("  Expected: ~2-3 minutes\n")

result = run_optimized_validation(
    su=30000,          # 30 kPa
    width=6.84,        # Equivalent width
    thickness=0.5,
    rate=0.10,         # ← 10x FASTER!
    target=0.10,       # ← 5x LESS! (100mm sufficient)
    nx=80,
    ny=40,
    use_gimp=False,    # ✅ Verified correct standard MPM
    plot_results=True  # Show plots with tangent method
)

print("\n" + "="*70)
print("TANGENT METHOD RESULTS")
print("="*70)
print(f"Previous (max method):  1957 kN (22% error)")
print(f"Liu et al. target:      2522 kN")
print(f"Current (tangent):      {result['ultimate_load']:.0f} kN ({result['error_percent']:.1f}% error)")

# Check improvement
old_error = 22.0
new_error = result['error_percent']
improvement = old_error - new_error

print("\n" + "="*70)
print("ERROR REDUCTION ANALYSIS")
print("="*70)
print(f"Old error (max method):     {old_error:.1f}%")
print(f"New error (tangent method): {new_error:.1f}%")
print(f"Improvement:                {improvement:.1f} percentage points")

if new_error < 10:
    print("\n🎯 SUCCESS! Error < 10% achieved!")
    print("   Tangent method is THE solution!")
elif new_error < 15:
    print("\n✅ MAJOR IMPROVEMENT! Error < 15%")
    print("   Tangent method significantly helps")
    print("   Minor tuning (E/su ratio, mesh) could get to <10%")
elif new_error < 20:
    print("\n✅ GOOD IMPROVEMENT! Error reduced")
    print("   Tangent method helps")
    print("   Additional calibration needed for <10%")
else:
    print("\n⚠️  Tangent method alone not sufficient")
    print("   Need additional fixes (mesh, material params, etc.)")

print("\n" + "="*70)
