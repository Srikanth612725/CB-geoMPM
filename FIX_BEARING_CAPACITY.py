"""
TWO FIXES FOR calculate_bearing_capacity()
===========================================

Apply BOTH fixes to mpm_optimized.py
"""

fix_option_a = """
# ==============================================================================
# FIX OPTION A: Reduce interface thickness (QUICK FIX)
# ==============================================================================
# In mpm_optimized.py, line 532, change from:
#     interface_thickness = 1.5 * self.dy
# To:
#     interface_thickness = 0.25 * self.dy
#
# This reduces sampling zone from 1.0m to 0.17m (just 1 particle layer)
"""

fix_option_b = """
# ==============================================================================
# FIX OPTION B: Use foundation reaction forces (PROPER FIX)
# ==============================================================================
# Replace the entire calculate_bearing_capacity() method (lines 519-555)
# with the following:

def calculate_bearing_capacity(self):
    '''Calculate bearing capacity using foundation reaction forces'''
    if not self.foundation_indices:
        return 0.0

    # Get foundation dimensions
    found_x = [self.particles[i].x for i in self.foundation_indices]
    found_y = [self.particles[i].y for i in self.foundation_indices]
    foundation_width = max(found_x) - min(found_x)

    # Method 1: Sum reaction forces from grid on foundation particles
    total_reaction = 0.0
    for idx in self.foundation_indices:
        mp = self.particles[idx]

        # Get shape functions for this foundation particle
        nodes, N, _, _ = self.get_shape_functions(mp)

        # Sum grid forces weighted by shape functions
        for k, node in enumerate(nodes):
            # Vertical force from grid on this particle
            # Note: grid_fy is the force, negative = upward reaction
            total_reaction += abs(N[k] * self.grid_fy[node])

    # Bearing capacity per unit out-of-plane length
    if foundation_width > 0:
        force_per_length = total_reaction / foundation_width
        return force_per_length

    return 0.0
"""

print("="*70)
print("TWO FIXES FOR BEARING CAPACITY CALCULATION")
print("="*70)

print("\n" + fix_option_a)
print("\n" + fix_option_b)

print(f"""
{'='*70}
RECOMMENDATION
{'='*70}

1. FIRST: Try Option A (quick fix)
   - Change line 532: interface_thickness = 0.25 * self.dy
   - This is 1 line change
   - Run a quick test to see if capacity is ~154 kN/m

2. IF Option A doesn't work well:
   - Implement Option B (proper fix)
   - Replace entire method (lines 519-555)
   - This directly measures reaction force on foundation
   - Should give exact bearing capacity

3. Test with ONE simulation (5 minutes instead of 4 hours!)

Let me implement BOTH fixes now...
""")
