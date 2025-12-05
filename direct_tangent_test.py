#!/usr/bin/env python3
"""
DIRECT TANGENT METHOD TEST
===========================

Directly use run_optimized_validation which has tangent method built-in.
Tests with optimized parameters for faster execution.
"""

print("="*70)
print("DIRECT TANGENT METHOD VALIDATION")
print("="*70)

from mpm_optimized import run_optimized_validation

# Test with optimized parameters (should complete in 2-3 minutes)
print("\nRunning Liu validation case with tangent method...")
print("Parameters:")
print("  su = 30 kPa")
print("  width = 6.84 m (Liu equivalent width)")
print("  rate = 0.10 m/s (10x faster, still quasi-static)")
print("  target = 0.10 m (100mm settlement)")
print("  mesh = 60x30 (coarser for speed)")
print("\nExpected runtime: ~2-3 minutes\n")

result = run_optimized_validation(
    su=30000,          # 30 kPa (Liu case)
    width=6.84,        # Equivalent width
    thickness=0.5,
    rate=0.10,         # Fast but quasi-static
    target=0.10,       # 100mm settlement
    interval=0.02,     # Record every 20mm
    max_steps=5000,
    nx=60,             # Coarser mesh for speed
    ny=30,
    use_gimp=False,    # Standard MPM
    plot_results=True  # Show plots
)

print("\n" + "="*70)
print("ANALYSIS")
print("="*70)

if result:
    Q_ult = result['ultimate_load']
    Q_max = result.get('max_load', Q_ult)
    error = result['error_percent']
    method = result.get('method', 'unknown')

    print(f"\nMethod used: {method}")
    print(f"Ultimate load (tangent): {Q_ult:.0f} kN")
    if 'max_load' in result and Q_max != Q_ult:
        print(f"Maximum load (peak):     {Q_max:.0f} kN")
        print(f"Ratio (tangent/max):     {Q_ult/Q_max:.3f}")

    print(f"\nTarget (Liu et al.): 2522 kN")
    print(f"Error: {error:.1f}%")

    print(f"\nComparison to previous results:")
    print(f"  Previous (max method): 1957 kN (22% error)")
    print(f"  Current (tangent):     {Q_ult:.0f} kN ({error:.1f}% error)")

    improvement = 22.0 - error
    print(f"\n  Improvement: {improvement:.1f} percentage points")

    if error < 15:
        print("\n✅ SUCCESS! Error < 15% achieved!")
        print("   Tangent method with optimized parameters works well!")
    elif error < 20:
        print("\n✅ GOOD! Error reduced from 22%")
        print("   Tangent method shows improvement")
    elif error < 25:
        print("\n⚠️  Modest results. Error similar to baseline")
        print("   May need additional parameter tuning")
    else:
        print("\n⚠️  Error higher than baseline")
        print("   Check simulation parameters")
else:
    print("\n❌ Simulation failed to return results")
    print("   Check error messages above")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
