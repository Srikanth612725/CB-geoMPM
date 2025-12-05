#!/usr/bin/env python3
"""
Tangent Intersection Method for Ultimate Bearing Capacity
==========================================================

Standard geotechnical method for determining ultimate capacity from
load-settlement curves, as used by Liu et al. (2020) and others.

References:
- ASTM D1143 (Standard Test Methods for Deep Foundations)
- Chin, F.K. (1970). "Estimation of the ultimate load of piles not carried to failure"
- De Beer, E.E. (1970). "Experimental determination of the shape factors"
- Liu et al. (2020). FE analysis of offshore foundations
"""

import numpy as np
from scipy.optimize import curve_fit
from scipy import stats
import matplotlib.pyplot as plt

def tangent_intersection_method(settlements, loads, plot=False):
    """
    Determine ultimate bearing capacity using tangent intersection method.

    Method:
    1. Identify initial linear portion (elastic region)
    2. Fit tangent line to initial portion
    3. Identify final linear portion (plastic flow/failure)
    4. Fit tangent line to final portion
    5. Find intersection of two tangent lines
    6. Ultimate capacity = load at intersection point

    Parameters:
    -----------
    settlements : array-like
        Settlement values (m)
    loads : array-like
        Load values (kN or kN/m)
    plot : bool
        If True, create diagnostic plot

    Returns:
    --------
    dict with:
        'Q_ult' : Ultimate bearing capacity at tangent intersection
        'Q_max' : Maximum load (for comparison)
        's_ult' : Settlement at ultimate capacity
        'method' : Method used
    """

    settlements = np.array(settlements)
    loads = np.array(loads)

    # Remove any NaN or zero values
    mask = ~np.isnan(settlements) & ~np.isnan(loads) & (loads > 0)
    settlements = settlements[mask]
    loads = loads[mask]

    if len(settlements) < 10:
        # Not enough data, fall back to max
        idx_max = np.argmax(loads)
        return {
            'Q_ult': loads[idx_max],
            'Q_max': loads[idx_max],
            's_ult': settlements[idx_max],
            'method': 'max_value'
        }

    # METHOD 1: Tangent Intersection (Standard Method)
    # -------------------------------------------------

    # Step 1: Identify initial linear portion (first 10-20% of data)
    n_initial = min(int(len(settlements) * 0.15), 20)
    s_initial = settlements[:n_initial]
    q_initial = loads[:n_initial]

    # Fit linear regression to initial portion
    if len(s_initial) >= 3:
        slope1, intercept1, r1, _, _ = stats.linregress(s_initial, q_initial)

        # Step 2: Identify final linear portion (last 20-30% of data)
        # Look for region where dQ/ds is relatively constant (plastic flow)
        n_final = min(int(len(settlements) * 0.25), 30)
        s_final = settlements[-n_final:]
        q_final = loads[-n_final:]

        # Fit linear regression to final portion
        if len(s_final) >= 3:
            slope2, intercept2, r2, _, _ = stats.linregress(s_final, q_final)

            # Step 3: Find intersection of two tangent lines
            # Line 1: q = slope1*s + intercept1
            # Line 2: q = slope2*s + intercept2
            # Intersection: slope1*s + intercept1 = slope2*s + intercept2

            if abs(slope1 - slope2) > 1e-6:  # Lines not parallel
                s_intersection = (intercept2 - intercept1) / (slope1 - slope2)
                q_intersection = slope1 * s_intersection + intercept1

                # Validate intersection is within data range
                if s_intersection >= 0 and s_intersection <= settlements[-1] * 1.5:
                    if plot:
                        plot_tangent_method(settlements, loads,
                                          s_initial, q_initial, slope1, intercept1,
                                          s_final, q_final, slope2, intercept2,
                                          s_intersection, q_intersection)

                    return {
                        'Q_ult': q_intersection,
                        'Q_max': np.max(loads),
                        's_ult': s_intersection,
                        'method': 'tangent_intersection',
                        'initial_slope': slope1,
                        'final_slope': slope2,
                        'r_initial': r1,
                        'r_final': r2
                    }

    # METHOD 2: Offset Method (Fallback)
    # -----------------------------------
    # If tangent method fails, use offset method: Q at settlement = 10% of width
    # This is conservative and commonly used

    # For now, fall back to max if tangent fails
    idx_max = np.argmax(loads)

    if plot:
        plt.figure(figsize=(10, 6))
        plt.plot(settlements, loads, 'b-', linewidth=2, label='MPM simulation')
        plt.axvline(settlements[idx_max], color='r', linestyle='--',
                   label=f'Max load: {loads[idx_max]:.0f} kN')
        plt.xlabel('Settlement (m)')
        plt.ylabel('Load (kN/m)')
        plt.title('Load-Settlement Curve (Max Value Method - Tangent Failed)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.show()

    return {
        'Q_ult': loads[idx_max],
        'Q_max': loads[idx_max],
        's_ult': settlements[idx_max],
        'method': 'max_value'
    }


def plot_tangent_method(settlements, loads,
                       s_initial, q_initial, slope1, intercept1,
                       s_final, q_final, slope2, intercept2,
                       s_ult, q_ult):
    """Create diagnostic plot showing tangent method"""

    fig, ax = plt.subplots(figsize=(12, 8))

    # Plot main curve
    ax.plot(settlements, loads, 'b-', linewidth=2, label='MPM simulation', zorder=3)

    # Plot initial data points
    ax.plot(s_initial, q_initial, 'go', markersize=8,
            label='Initial elastic region', zorder=4)

    # Plot final data points
    ax.plot(s_final, q_final, 'mo', markersize=8,
            label='Final plastic region', zorder=4)

    # Plot tangent lines (extended)
    s_range = np.linspace(0, settlements[-1] * 1.2, 100)
    q_tangent1 = slope1 * s_range + intercept1
    q_tangent2 = slope2 * s_range + intercept2

    ax.plot(s_range, q_tangent1, 'g--', linewidth=2, alpha=0.7,
            label=f'Initial tangent (slope={slope1:.0f})')
    ax.plot(s_range, q_tangent2, 'm--', linewidth=2, alpha=0.7,
            label=f'Final tangent (slope={slope2:.0f})')

    # Mark intersection point (ultimate capacity)
    ax.plot(s_ult, q_ult, 'r*', markersize=20,
            label=f'Ultimate capacity: {q_ult:.0f} kN', zorder=5)

    # Mark maximum load for comparison
    idx_max = np.argmax(loads)
    ax.plot(settlements[idx_max], loads[idx_max], 'kx', markersize=15,
            label=f'Maximum load: {loads[idx_max]:.0f} kN', zorder=5)

    ax.set_xlabel('Settlement (m)', fontsize=12)
    ax.set_ylabel('Load (kN/m)', fontsize=12)
    ax.set_title('Tangent Intersection Method for Ultimate Bearing Capacity',
                fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, loc='best')
    ax.grid(True, alpha=0.3)

    # Add text box with results
    textstr = f'Q_ult (tangent): {q_ult:.0f} kN/m\n'
    textstr += f'Q_max (peak): {loads[idx_max]:.0f} kN/m\n'
    textstr += f'Ratio: {q_ult/loads[idx_max]:.2f}'
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes,
            fontsize=11, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.show()


def chin_method(settlements, loads):
    """
    Chin's hyperbolic method for ultimate capacity.

    Based on: Chin, F.K. (1970)
    Plots s/Q vs s and fits a straight line.
    Ultimate capacity = 1 / slope

    This method works when load-settlement follows hyperbolic relationship:
    s/Q = a + b*s
    Then: Q_ult = 1/b
    """

    settlements = np.array(settlements)
    loads = np.array(loads)

    # Remove zero loads
    mask = loads > 0
    s = settlements[mask]
    q = loads[mask]

    if len(s) < 5:
        return None

    # Calculate s/Q
    s_over_q = s / q

    # Linear regression
    slope, intercept, r_value, _, _ = stats.linregress(s, s_over_q)

    if slope > 0:
        Q_ult = 1.0 / slope

        return {
            'Q_ult': Q_ult,
            'method': 'chin_hyperbolic',
            'r_squared': r_value**2
        }

    return None


# Example usage and validation
if __name__ == "__main__":
    # Test with synthetic data
    s = np.linspace(0, 0.15, 100)

    # Hyperbolic load-settlement (typical foundation behavior)
    # Q = s / (a + b*s)
    a = 0.001
    b = 0.0008
    q = s / (a + b * s)

    # Add some noise
    q += np.random.normal(0, 50, len(q))

    # Test tangent method
    result = tangent_intersection_method(s, q, plot=True)

    print("\n" + "="*60)
    print("TANGENT INTERSECTION METHOD RESULTS")
    print("="*60)
    print(f"Method used: {result['method']}")
    print(f"Ultimate capacity (tangent): {result['Q_ult']:.0f} kN/m")
    print(f"Maximum load (peak): {result['Q_max']:.0f} kN/m")
    print(f"Settlement at Q_ult: {result['s_ult']*1000:.1f} mm")
    print(f"Ratio (Q_ult/Q_max): {result['Q_ult']/result['Q_max']:.2f}")

    if result['method'] == 'tangent_intersection':
        print(f"\nInitial tangent slope: {result['initial_slope']:.0f} kN/m²")
        print(f"Final tangent slope: {result['final_slope']:.0f} kN/m²")
        print(f"R² (initial fit): {result['r_initial']**2:.3f}")
        print(f"R² (final fit): {result['r_final']**2:.3f}")

    # Test Chin's method
    chin_result = chin_method(s, q)
    if chin_result:
        print(f"\nChin's method Q_ult: {chin_result['Q_ult']:.0f} kN/m")
        print(f"R² (Chin): {chin_result['r_squared']:.3f}")
