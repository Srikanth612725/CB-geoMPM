#!/usr/bin/env python3
"""
Diagnostic: Check GIMP shape function values and gradients
"""

import numpy as np
from mpm_optimized import gimp_shape_function_1d, shape_function_1d

print("="*70)
print("GIMP SHAPE FUNCTION DIAGNOSTIC")
print("="*70)

# Grid parameters
h = 0.5  # Cell size
lp = h / 4  # Particle half-length (for ppc=4)

# Test at various positions relative to node
x_node = 5.0
x_positions = np.linspace(x_node - h, x_node + h, 21)

print(f"\nCell size: h = {h}m")
print(f"Particle half-length: lp = {lp}m (= h/{h/lp:.1f})")
print(f"Node position: x = {x_node}m")
print(f"\n{'x':>6} | {'ξ':>6} | {'N_std':>8} | {'dN_std':>10} | {'N_gimp':>8} | {'dN_gimp':>10} | {'Ratio N':>8} | {'Ratio dN':>10}")
print("-"*100)

sum_N_std = 0
sum_N_gimp = 0

for x in x_positions:
    xi = (x - x_node) / h

    # Standard shape function
    N_std, dN_std = shape_function_1d(x, x_node, h)

    # GIMP shape function
    N_gimp, dN_gimp = gimp_shape_function_1d(x, x_node, h, lp)

    sum_N_std += N_std
    sum_N_gimp += N_gimp

    # Ratios
    ratio_N = N_gimp / N_std if abs(N_std) > 1e-12 else 0
    ratio_dN = dN_gimp / dN_std if abs(dN_std) > 1e-12 else 0

    print(f"{x:6.2f} | {xi:6.2f} | {N_std:8.4f} | {dN_std:10.4f} | {N_gimp:8.4f} | {dN_gimp:10.4f} | {ratio_N:8.4f} | {ratio_dN:10.4f}")

print(f"\nSum of N values:")
print(f"  Standard: {sum_N_std:.6f}")
print(f"  GIMP: {sum_N_gimp:.6f}")
print(f"  Ratio: {sum_N_gimp/sum_N_std:.6f}")

# Check partition of unity at particle position
print(f"\n{'='*70}")
print("PARTITION OF UNITY CHECK")
print(f"{'='*70}")

# Particle in center of cell
x_particle = x_node + h/2
print(f"\nParticle at x = {x_particle}m (center between nodes)")

# Get shape functions for 2 neighboring nodes
nodes = [x_node, x_node + h]
sum_N_std_2d = 0
sum_N_gimp_2d = 0

print(f"\n{'Node x':>8} | {'N_std':>10} | {'N_gimp':>10}")
print("-"*35)

for x_n in nodes:
    N_std, _ = shape_function_1d(x_particle, x_n, h)
    N_gimp, _ = gimp_shape_function_1d(x_particle, x_n, h, lp)

    sum_N_std_2d += N_std
    sum_N_gimp_2d += N_gimp

    print(f"{x_n:8.2f} | {N_std:10.6f} | {N_gimp:10.6f}")

print(f"\nSum (should be 1.0):")
print(f"  Standard: {sum_N_std_2d:.6f}")
print(f"  GIMP: {sum_N_gimp_2d:.6f}")

if abs(sum_N_std_2d - 1.0) > 0.01:
    print(f"  ⚠️  Standard MPM partition of unity VIOLATED!")
if abs(sum_N_gimp_2d - 1.0) > 0.01:
    print(f"  ⚠️  GIMP partition of unity VIOLATED!")

# 2D check
print(f"\n{'='*70}")
print("2D SHAPE FUNCTION VALUES (4 nodes)")
print(f"{'='*70}")

x_particle = 5.25
y_particle = 5.25
x_nodes = [5.0, 5.5]
y_nodes = [5.0, 5.5]

sum_N_std_2d = 0
sum_N_gimp_2d = 0

print(f"\nParticle at ({x_particle:.2f}, {y_particle:.2f})")
print(f"\n{'Node':>10} | {'N_std_2d':>12} | {'N_gimp_2d':>12}")
print("-"*40)

for x_n in x_nodes:
    for y_n in y_nodes:
        # Standard
        Nx_std, _ = shape_function_1d(x_particle, x_n, h)
        Ny_std, _ = shape_function_1d(y_particle, y_n, h)
        N_std_2d = Nx_std * Ny_std

        # GIMP
        Nx_gimp, _ = gimp_shape_function_1d(x_particle, x_n, h, lp)
        Ny_gimp, _ = gimp_shape_function_1d(y_particle, y_n, h, lp)
        N_gimp_2d = Nx_gimp * Ny_gimp

        sum_N_std_2d += N_std_2d
        sum_N_gimp_2d += N_gimp_2d

        print(f"({x_n:.1f}, {y_n:.1f}) | {N_std_2d:12.6f} | {N_gimp_2d:12.6f}")

print(f"\nSum (should be 1.0):")
print(f"  Standard: {sum_N_std_2d:.6f}")
print(f"  GIMP: {sum_N_gimp_2d:.6f}")

if abs(sum_N_gimp_2d - 1.0) > 0.01:
    print(f"  ❌ GIMP 2D partition of unity VIOLATED by {(sum_N_gimp_2d-1.0)*100:.1f}%")
    print(f"  This would cause mass/momentum conservation errors!")
else:
    print(f"  ✅ Partition of unity satisfied")

print(f"\n{'='*70}")
