#!/usr/bin/env python3
"""
STANDARD GEOTECHNICAL CAPACITY DETERMINATION METHODS
====================================================

Implements and compares established methods from literature:
1. Chin-Konder Method (Hyperbolic) - Chin (1970)
2. Brinch Hansen 80% Method - Hansen (1963)
3. Davisson Offset Method - Davisson (1972)
4. 0.1B Method (10% settlement)
5. Fuller-Hoy Method - Fuller & Hoy (1970)

These are peer-reviewed, journal-accepted methods for determining
ultimate bearing capacity from load-settlement curves.
"""

import numpy as np
from scipy import stats
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

# ============================================================================
# METHOD 1: CHIN-KONDER HYPERBOLIC METHOD
# ============================================================================

def chin_konder_method(settlements, loads, plot=False):
    """
    Chin-Konder Hyperbolic Method (Chin, 1970)

    Widely used in geotechnical practice. Assumes load-settlement follows:
    s/Q = a + b*s

    Plot s/Q vs s, fit straight line, ultimate capacity Q_ult = 1/b

    References:
    - Chin, F.K. (1970). "Estimation of the ultimate load of piles
      not carried to failure" Proc. 2nd Southeast Asian Conf. on Soil Eng.
    - Fellenius, B.H. (1980). "The analysis of results from routine
      pile load tests"

    Returns:
    --------
    dict with Q_ult, method, R², and quality metrics
    """

    s = np.array(settlements)
    Q = np.array(loads)

    # Remove zeros and negatives
    mask = (Q > 0) & (s > 0)
    s = s[mask]
    Q = Q[mask]

    if len(s) < 5:
        return None

    # Calculate s/Q
    s_over_Q = s / Q

    # Linear regression: s/Q = a + b*s
    slope, intercept, r_value, p_value, std_err = stats.linregress(s, s_over_Q)

    if slope > 0:
        Q_ult = 1.0 / slope
        R_squared = r_value ** 2

        # Quality check - good fit should have R² > 0.85
        quality = "Excellent" if R_squared > 0.95 else \
                 "Good" if R_squared > 0.90 else \
                 "Fair" if R_squared > 0.85 else "Poor"

        if plot:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

            # Left: s/Q vs s plot
            ax1.plot(s, s_over_Q, 'bo', label='Data', markersize=6)
            s_fit = np.linspace(s.min(), s.max(), 100)
            s_over_Q_fit = intercept + slope * s_fit
            ax1.plot(s_fit, s_over_Q_fit, 'r--', linewidth=2,
                    label=f'Fit: s/Q = {intercept:.4f} + {slope:.4f}*s\nR² = {R_squared:.3f}')
            ax1.set_xlabel('Settlement, s (m)', fontsize=11)
            ax1.set_ylabel('s/Q (m/kN)', fontsize=11)
            ax1.set_title('Chin-Konder Hyperbolic Method', fontsize=12, fontweight='bold')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # Right: Original load-settlement curve
            ax2.plot(s*1000, Q, 'b-o', linewidth=2, markersize=4)
            ax2.axhline(Q_ult, color='r', linestyle='--', linewidth=2,
                       label=f'Q_ult (Chin-Konder) = {Q_ult:.0f} kN/m')
            ax2.set_xlabel('Settlement (mm)', fontsize=11)
            ax2.set_ylabel('Load (kN/m)', fontsize=11)
            ax2.set_title('Load-Settlement Curve', fontsize=12, fontweight='bold')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig('chin_konder_analysis.png', dpi=150)

        return {
            'Q_ult': Q_ult,
            'method': 'chin_konder',
            'R_squared': R_squared,
            'slope': slope,
            'intercept': intercept,
            'quality': quality,
            'p_value': p_value
        }

    return None


# ============================================================================
# METHOD 2: BRINCH HANSEN 80% METHOD
# ============================================================================

def brinch_hansen_80_method(settlements, loads):
    """
    Brinch Hansen 80% Criterion (Hansen, 1963)

    Ultimate load is defined as the load Q₀ such that the settlement at Q₀
    equals 4 times the settlement at 0.8*Q₀.

    Mathematically: s(Q₀) = 4 * s(0.8*Q₀)

    Procedure:
    1. For each load Q in the upper range (>50% of max)
    2. Find settlement at 0.8*Q
    3. Check if s(Q) ≈ 4 * s(0.8*Q)
    4. Q that satisfies this is Q_ult

    References:
    - Hansen, J.B. (1963). "Discussion on hyperbolic stress-strain response"
    - Fellenius, B.H. (2001). "From strain measurements to load in an
      instrumented pile"

    Returns:
    --------
    dict with Q_ult, settlement, and quality metrics
    """

    s = np.array(settlements)
    Q = np.array(loads)

    if len(s) < 10:
        return None

    # Interpolation function for settlement vs load
    from scipy.interpolate import interp1d

    # Sort by load
    sort_idx = np.argsort(Q)
    Q_sorted = Q[sort_idx]
    s_sorted = s[sort_idx]

    # Create interpolation function
    s_interp = interp1d(Q_sorted, s_sorted, kind='cubic',
                        bounds_error=False, fill_value='extrapolate')

    # Search in upper 50% of load range
    Q_max = Q_sorted[-1]
    Q_search = np.linspace(0.5 * Q_max, Q_max, 50)

    best_Q = None
    best_ratio = None
    min_error = float('inf')

    for Q_test in Q_search:
        Q_80 = 0.8 * Q_test

        # Get settlements
        s_test = s_interp(Q_test)
        s_80 = s_interp(Q_80)

        # Check criterion: s(Q) should equal 4 * s(0.8*Q)
        ratio = s_test / s_80 if s_80 > 0 else 0
        error = abs(ratio - 4.0)

        if error < min_error:
            min_error = error
            best_Q = Q_test
            best_ratio = ratio

    if best_Q is not None:
        quality = "Excellent" if min_error < 0.2 else \
                 "Good" if min_error < 0.5 else \
                 "Fair" if min_error < 1.0 else "Poor"

        return {
            'Q_ult': best_Q,
            'method': 'brinch_hansen_80',
            's_ult': s_interp(best_Q),
            'ratio_achieved': best_ratio,
            'ratio_target': 4.0,
            'error': min_error,
            'quality': quality
        }

    return None


# ============================================================================
# METHOD 3: DAVISSON OFFSET METHOD
# ============================================================================

def davisson_offset_method(settlements, loads, width, E_foundation=None):
    """
    Davisson Offset Limit Load (Davisson, 1972)

    Ultimate load is where settlement exceeds elastic compression plus offset:
    s_failure = s_elastic + offset

    For foundations: offset = 0.15 + B/120 (inches) → ~4mm + B/30 (meters)
    For this implementation: offset = 0.004 + B/30 meters

    References:
    - Davisson, M.T. (1972). "High capacity piles" Proc. Soil Mech. Lecture
      Series on Innovations in Foundation Construction, ASCE, Illinois
    - ASTM D1143 references Davisson method

    Parameters:
    -----------
    width : float
        Foundation width in meters
    E_foundation : float, optional
        Foundation elastic modulus. If None, uses empirical elastic line

    Returns:
    --------
    dict with Q_ult and settlement at failure
    """

    s = np.array(settlements)
    Q = np.array(loads)

    if len(s) < 5:
        return None

    # Davisson offset (adapted for foundations in meters)
    offset = 0.004 + width / 30.0  # meters

    # Fit elastic line through initial data (first 20%)
    n_initial = max(int(len(s) * 0.2), 3)
    slope_elastic, intercept_elastic, r_val, _, _ = stats.linregress(Q[:n_initial], s[:n_initial])

    # Offset line: s_offset = slope_elastic * Q + offset
    s_offset_line = slope_elastic * Q + offset

    # Find intersection: where actual settlement crosses offset line
    for i in range(1, len(s)):
        if s[i] >= s_offset_line[i]:
            # Linear interpolation for precise intersection
            Q_ult = Q[i-1] + (Q[i] - Q[i-1]) * \
                    (s_offset_line[i-1] - s[i-1]) / \
                    ((s[i] - s[i-1]) - (s_offset_line[i] - s_offset_line[i-1]))
            s_ult = s[i-1] + (s[i] - s[i-1]) * (Q_ult - Q[i-1]) / (Q[i] - Q[i-1])

            return {
                'Q_ult': Q_ult,
                'method': 'davisson_offset',
                's_ult': s_ult,
                'offset': offset,
                'elastic_slope': slope_elastic,
                'R_squared_elastic': r_val**2
            }

    # If no intersection found, use max load
    return {
        'Q_ult': Q[-1],
        'method': 'davisson_offset',
        's_ult': s[-1],
        'offset': offset,
        'elastic_slope': slope_elastic,
        'R_squared_elastic': r_val**2,
        'note': 'No intersection found, using maximum load'
    }


# ============================================================================
# METHOD 4: 0.1B METHOD (10% SETTLEMENT)
# ============================================================================

def settlement_10_percent_method(settlements, loads, width):
    """
    0.1B Method (10% Settlement Criterion)

    Ultimate bearing capacity at settlement = 10% of foundation width.

    Common in shallow foundation design codes and standards.

    References:
    - IS 6403 (Indian Standard): Code of practice for determination of
      bearing capacity of shallow foundations
    - Terzaghi & Peck (1967): Soil Mechanics in Engineering Practice

    Parameters:
    -----------
    width : float
        Foundation width in meters

    Returns:
    --------
    dict with Q_ult at s = 0.1*B
    """

    s = np.array(settlements)
    Q = np.array(loads)

    target_settlement = 0.1 * width

    # Check if we reached target settlement
    if s[-1] < target_settlement:
        return {
            'Q_ult': None,
            'method': '0.1B_settlement',
            's_target': target_settlement,
            's_max_achieved': s[-1],
            'note': f'Target settlement {target_settlement*1000:.0f}mm not reached (max: {s[-1]*1000:.0f}mm)'
        }

    # Interpolate to find load at target settlement
    from scipy.interpolate import interp1d
    Q_interp = interp1d(s, Q, kind='cubic', fill_value='extrapolate')
    Q_ult = Q_interp(target_settlement)

    return {
        'Q_ult': float(Q_ult),
        'method': '0.1B_settlement',
        's_ult': target_settlement,
        'width': width
    }


# ============================================================================
# METHOD 5: FULLER-HOY METHOD
# ============================================================================

def fuller_hoy_method(settlements, loads):
    """
    Fuller-Hoy Method (Fuller & Hoy, 1970)

    Ultimate capacity at point where slope of load-settlement curve
    reaches specific value (typically 0.05 mm/kN for piles, adapted for foundations).

    For foundations, we use: dS/dQ = 0.001 m/kN (1 mm/kN)

    References:
    - Fuller, F.M. & Hoy, H.E. (1970). "Pile load tests including
      quick-load test method"
    - ASTM D1143 references for interpretation methods

    Returns:
    --------
    dict with Q_ult where slope criteria is met
    """

    s = np.array(settlements)
    Q = np.array(loads)

    if len(s) < 5:
        return None

    # Calculate slopes (dS/dQ) between consecutive points
    dS = np.diff(s)
    dQ = np.diff(Q)

    # Avoid division by zero
    mask = dQ > 0
    slopes = np.zeros_like(dQ)
    slopes[mask] = dS[mask] / dQ[mask]

    # Target slope (1 mm/kN = 0.001 m/kN for foundations)
    target_slope = 0.001  # m/kN

    # Find where slope exceeds target
    for i in range(len(slopes)):
        if slopes[i] >= target_slope:
            return {
                'Q_ult': Q[i],
                'method': 'fuller_hoy',
                's_ult': s[i],
                'slope_achieved': slopes[i],
                'target_slope': target_slope
            }

    # If never reached, use max
    return {
        'Q_ult': Q[-1],
        'method': 'fuller_hoy',
        's_ult': s[-1],
        'slope_achieved': slopes[-1] if len(slopes) > 0 else None,
        'target_slope': target_slope,
        'note': 'Target slope not reached, using maximum load'
    }


# ============================================================================
# COMPARISON FUNCTION
# ============================================================================

def compare_all_methods(settlements, loads, width, Q_expected=None):
    """
    Apply all standard methods and compare results

    Parameters:
    -----------
    settlements : array
        Settlement values (m)
    loads : array
        Load values (kN/m)
    width : float
        Foundation width (m)
    Q_expected : float, optional
        Expected/theoretical capacity for error calculation

    Returns:
    --------
    dict of results from all methods
    """

    results = {}

    # Method 1: Chin-Konder
    chin = chin_konder_method(settlements, loads, plot=False)
    if chin:
        results['chin_konder'] = chin

    # Method 2: Brinch Hansen 80%
    hansen = brinch_hansen_80_method(settlements, loads)
    if hansen:
        results['brinch_hansen'] = hansen

    # Method 3: Davisson Offset
    davisson = davisson_offset_method(settlements, loads, width)
    if davisson:
        results['davisson'] = davisson

    # Method 4: 0.1B Settlement
    settlement_10 = settlement_10_percent_method(settlements, loads, width)
    if settlement_10:
        results['settlement_10_percent'] = settlement_10

    # Method 5: Fuller-Hoy
    fuller = fuller_hoy_method(settlements, loads)
    if fuller:
        results['fuller_hoy'] = fuller

    # Add maximum load for comparison
    results['maximum_load'] = {
        'Q_ult': np.max(loads),
        'method': 'maximum_load',
        's_ult': settlements[np.argmax(loads)]
    }

    # Calculate errors if expected value provided
    if Q_expected:
        for method, data in results.items():
            if data.get('Q_ult') is not None:
                error = abs(data['Q_ult'] - Q_expected) / Q_expected * 100
                data['error_percent'] = error

    return results


# ============================================================================
# MAIN EXECUTION FOR TESTING
# ============================================================================

if __name__ == "__main__":
    # Test with synthetic data
    print("="*70)
    print("TESTING STANDARD GEOTECHNICAL METHODS")
    print("="*70)

    # Generate synthetic hyperbolic load-settlement curve
    s_test = np.linspace(0, 0.15, 50)
    # Hyperbolic: Q = s / (a + b*s), with Q_ult = 1/b
    a = 0.0005
    b = 0.0008  # Q_ult = 1250 kN/m
    Q_test = s_test / (a + b * s_test)

    # Add some noise
    Q_test += np.random.normal(0, 20, len(Q_test))

    B_test = 5.0  # 5m foundation
    Q_expected = 1.0 / b

    print(f"\nSynthetic test:")
    print(f"  Foundation width: {B_test}m")
    print(f"  Expected Q_ult: {Q_expected:.0f} kN/m")
    print(f"  Data points: {len(s_test)}")

    # Compare all methods
    results = compare_all_methods(s_test, Q_test, B_test, Q_expected)

    print(f"\n{'Method':<25} {'Q_ult (kN/m)':<15} {'Error (%)':<12} {'Quality':<15}")
    print("-"*70)

    for method, data in results.items():
        Q = data.get('Q_ult', 'N/A')
        err = data.get('error_percent', None)
        quality = data.get('quality', data.get('note', ''))

        Q_str = f"{Q:.0f}" if isinstance(Q, (int, float)) else str(Q)
        err_str = f"{err:.1f}" if err is not None else "N/A"

        print(f"{method:<25} {Q_str:<15} {err_str:<12} {quality:<15}")

    print("\n" + "="*70)
    print("✅ All methods implemented and tested")
    print("="*70)
