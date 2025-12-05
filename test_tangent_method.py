#!/usr/bin/env python3
"""
Test: Does tangent method reduce the 22% error?
"""

import numpy as np
from mpm_optimized import run_optimized_validation

print("="*70)
print("TESTING TANGENT METHOD vs MAX VALUE METHOD")
print("="*70)

# Run Liu case with tangent method
print("\nRunning Liu validation case...")
print("(This will take ~5-10 minutes)")

result = run_optimized_validation(
    su=30000,          # 30 kPa
    width=6.84,        # Equivalent width
    thickness=0.5,
    rate=0.01,         # Settlement rate
    target=0.5,        # 500mm settlement
    nx=80,
    ny=40,
    use_gimp=False,    # ✅ Verified correct standard MPM
    plot_results=True  # Show plots with tangent method
)

print("\n" + "="*70)
print("COMPARISON WITH PREVIOUS RESULTS")
print("="*70)
print(f"Previous (max method):  1957 kN (22% error)")
print(f"Liu et al. target:      2522 kN")
print(f"Current (tangent):      {result['ultimate_load']:.0f} kN ({result['error_percent']:.1f}% error)")
print("\n")

if result['error_percent'] < 15:
    print("✅ MAJOR IMPROVEMENT! Error reduced below 15%")
elif result['error_percent'] < 20:
    print("✅ IMPROVEMENT! Error reduced from 22%")
else:
    print("⚠️  Error still high - may need other adjustments")
