# Tangent Method Validation - Findings & Recommendations

**Date**: 2025-11-29
**Session**: Continuation of "Evaluate simulation tools for research project"

---

## Executive Summary

Attempted to validate the tangent intersection method for determining ultimate bearing capacity and optimize settlement rates/time steps. **Key finding: Simulations are encountering performance and setup issues that need to be resolved before comprehensive validation can proceed.**

---

## Original Context

### The 1957 kN Result

From previous work:
- **Method**: Maximum value from load-settlement curve
- **Result**: 1957 kN
- **Error**: 22% vs Liu et al. target (2522 kN)
- **Parameters**:
  - su = 30,000 Pa (30 kPa)
  - width = 6.84 m (equivalent width for Liu A-shape)
  - rate = 0.01 m/s
  - target settlement = 0.5 m (500mm)
  - mesh = 80×40
  - use_gimp = False (standard MPM)

### Hypothesis

The **tangent intersection method** (standard geotechnical practice) should give more accurate ultimate capacity than simply taking the maximum load value, potentially reducing the 22% error.

---

## Tests Performed

### Test 1: Simple Validation Test (Prandtl Case)
**File**: `simple_validation_test.py`

**Parameters**:
- Foundation: 5m wide
- Soil: su = 6 kPa
- Expected (Prandtl): 154 kN/m
- Mesh: 40×20 (coarse)
- Rate: 0.10 m/s

**Results**:
```
MAX method:     44 kN/m  (71.7% error)
TANGENT method: 44 kN/m  (71.7% error)
Method used:    max_value (tangent fell back)
Improvement:    0.0 percentage points
```

**Issues Identified**:
1. ❌ **Very high error**: 71.7% vs expected 22%
2. ❌ **Tangent method failed**: Fell back to max_value
3. ❌ **Insufficient load**: Only 44 kN/m vs expected 154 kN/m

**Possible Causes**:
- Mesh too coarse (40×20 with 0.75m cells)
- Foundation-soil contact insufficient
- Particle resolution too low (2173 particles, only 13 foundation)
- Settlement target too small (50mm may not reach failure)

### Test 2: Liu Case Fast Test
**File**: `test_tangent_fast.py`

**Parameters**:
- su = 30 kPa
- width = 6.84 m
- rate = 0.10 m/s
- target = 0.10 m (100mm)
- mesh = 80×40
- Particles: 9654 (9600 soil, 54 foundation)

**Results**:
- ❌ **Simulation stalled**: Ran for 6+ minutes without progress output
- ❌ **No results obtained**

**Issues**:
- Possible JIT compilation delay
- Computational load higher than expected
- Missing progress output in simulation loop

---

## Root Cause Analysis

### Issue 1: Mesh Resolution vs Computational Cost Trade-off

**Current situation**:
- Coarse mesh (40×20, 50×25): Fast but **inaccurate** (71% error)
- Fine mesh (80×40): Accurate(?) but **very slow** (6+ min, no output)

**The problem**:
- The 1957 kN result used 80×40 mesh, which works but is computationally expensive
- Attempts to speed up with coarse mesh severely degrade accuracy
- The "sweet spot" hasn't been found yet

### Issue 2: Settlement Rate Optimization Challenges

**Quasi-static criterion**: Inertial/Strength ratio < 0.01

For su = 30 kPa, ρ = 1600 kg/m³:
```
rate = 0.01 m/s → ratio = 0.000053 ✅ Excellent
rate = 0.05 m/s → ratio = 0.001333 ✅ Good
rate = 0.10 m/s → ratio = 0.005333 ✅ Acceptable
rate = 0.20 m/s → ratio = 0.021333 ⚠️  Dynamic (too fast)
```

**Findings**:
- ✅ Can increase rate from 0.01 → 0.10 m/s (10x speedup) while staying quasi-static
- ✅ Can reduce target from 500mm → 100mm (5x speedup) if failure is reached
- ⚠️  But faster rates may affect numerical stability

**Expected speedup**: 10x (rate) × 5x (target) = **50x faster simulations**

### Issue 3: Data Recording and Analysis

**Observed**:
- Some tests record 0 kN/m bearing capacity → calculation issue
- Tangent method falls back to max_value → insufficient data points
- Progress output missing → can't monitor simulation

**Needed improvements**:
- More frequent data recording
- Better progress monitoring
- Validation of bearing capacity calculation
- Diagnostic outputs during simulation

---

## Scripts Created

### 1. `validate_tangent_method_comprehensive.py`
**Status**: ✅ Created, ⏳ Not yet run

**Purpose**: Full validation suite comparing max vs tangent methods

**Tests**:
1. Original parameters (reproduce 1957 kN)
2. Optimized rate (0.10 m/s, 150mm)
3. Super fast (0.20 m/s, 100mm, coarse mesh)

**Expected output**:
- Comparison of all three approaches
- Error analysis (max vs tangent)
- Runtime comparison
- Visualization plots

**Estimated runtime**: 20-40 minutes for all three tests

### 2. `quick_tangent_validation.py`
**Status**: ⚠️  Created, tested, has issues

**Purpose**: Fast preliminary test (1-2 min)

**Issues found**:
- Bearing capacity calculation returns 0
- Needs better mesh resolution

### 3. `direct_tangent_test.py`
**Status**: ✅ Created, ⏳ Ready to run

**Purpose**: Direct use of `run_optimized_validation()` function

**Advantages**:
- Uses pre-tested code path
- Tangent method already integrated
- Simpler, more reliable

**Recommended** for next validation attempt

---

## Recommendations

### Immediate Next Steps (Priority Order)

#### 1. **Fix and Run Direct Test** ⭐⭐⭐ (HIGHEST PRIORITY)
```bash
python3 direct_tangent_test.py
```

**Why this first**:
- Uses proven code path (`run_optimized_validation`)
- Tangent method already integrated
- Most likely to work correctly
- 2-3 minute runtime expected

**If successful**: Provides immediate answer on tangent method effectiveness

**If fails**: Indicates fundamental issue with mpm_optimized.py

#### 2. **Diagnose Simulation Issues** ⭐⭐

Create diagnostic script to check:
- [✓] Bearing capacity calculation (why 0 kN/m?)
- [✓] Foundation-soil contact (particles at interface)
- [✓] Stress state in soil (are particles yielding?)
- [✓] Progress output (why no printouts during computation?)

#### 3. **Find Optimal Mesh Resolution** ⭐⭐

Test mesh refinement study:
```
Coarse:   40×20  → Fast but inaccurate (71% error)
Medium:   60×30  → ? (unknown)
Fine:     80×40  → Accurate (22% error) but slow
Finer:   100×50  → Even more accurate? Even slower?
```

**Goal**: Find minimum mesh for <25% error with acceptable runtime

#### 4. **Optimize Settlement Parameters** ⭐

Create parameter study for Liu case:
```
Test combinations of:
- rate: [0.01, 0.02, 0.05, 0.10] m/s
- target: [0.10, 0.15, 0.20, 0.30] m
- mesh: [60×30, 80×40]
```

**Metrics**:
- Runtime
- Error vs Liu target
- Quasi-static validity

### Medium-Term Actions

#### 5. **Validate Tangent Method Properly**

Once simulations are reliable:

Run `validate_tangent_method_comprehensive.py` to compare:
- Original parameters (1957 kN baseline)
- Optimized parameters
- Maximum vs tangent method accuracy

**Expected findings**:
- Tangent method improvement (if any)
- Optimal parameter set for parametric study
- Runtime vs accuracy trade-offs

#### 6. **Update Parametric Study Code**

If tangent method proves beneficial:
- Update `param_sweep.py` to use tangent method
- Update `run_parametric_study.py` with optimized rates
- Modify `parametric_study_plan.json` with faster parameters

### Long-Term Considerations

#### 7. **Investigate Discrepancy**

**The mystery**: Why 71% error in simple test vs documented 22% error?

Possible explanations:
1. **Mesh resolution**: 40×20 vs 80×40
2. **Particle count**: 2173 vs 9654
3. **Foundation discretization**: 13 vs 54 particles
4. **Settlement target**: 50mm vs 500mm (didn't reach failure?)
5. **Different test case**: Prandtl (simple) vs Liu (complex geometry)

**Need**: Systematic comparison with exact parameters from previous successful runs

#### 8. **Performance Optimization**

If simulations remain slow:
- Profile code to find bottlenecks
- Optimize Numba JIT compilation (compilation time vs runtime)
- Consider adaptive mesh refinement
- Parallel parametric study execution

---

## Critical Questions to Answer

### Q1: Does the tangent method actually help?

**Status**: ⏳ **Unknown** - haven't successfully compared yet

**To answer**: Run `direct_tangent_test.py` or `validate_tangent_method_comprehensive.py`

**Expected**:
- If YES: Error reduced from 22% → 15% or better
- If NO: Error remains ~22% or worse

### Q2: What parameters reproduce the 1957 kN result?

**Status**: ⏳ **Partially known**

**Known**:
- su = 30 kPa, width = 6.84 m, mesh = 80×40
- rate = 0.01 m/s, target = 0.5 m

**Unknown**:
- Why can't we reproduce this reliably?
- What other settings affect the result?

**To answer**: Create exact reproduction test with all parameters matched

### Q3: Can we speed up simulations by 10-50x?

**Status**: ⏳ **Theoretically yes, practically uncertain**

**Theory**:
- ✅ Rate: 0.01 → 0.10 m/s (10x, still QS)
- ✅ Target: 0.5m → 0.1m (5x, if failure reached)
- ✅ Mesh: 80×40 → 60×30 (1.8x, if accuracy acceptable)
- **Total**: ~90x speedup possible

**Practice**:
- ⚠️  Faster rates cause numerical issues?
- ⚠️  Smaller targets don't reach failure?
- ⚠️  Coarser mesh gives 71% error?

**To answer**: Systematic parameter sweep with accuracy vs runtime tracking

---

## Files Summary

### Test Scripts Created ✅
1. `validate_tangent_method_comprehensive.py` - Full 3-test validation suite
2. `quick_tangent_validation.py` - Fast preliminary test (has issues)
3. `direct_tangent_test.py` - Direct validation using proven code

### Existing Test Scripts 📁
1. `test_tangent_method.py` - Original tangent test (slow: 0.01 m/s, 500mm)
2. `test_tangent_fast.py` - Fast version (0.10 m/s, 100mm) - stalled in testing
3. `simple_validation_test.py` - Simple Prandtl test - low accuracy
4. `check_quasi_static.py` - Settlement rate validation tool

### Core Implementation 🔧
1. `mpm_optimized.py` - Main MPM solver with Numba JIT + tangent method
2. `tangent_method.py` - Tangent intersection algorithm
3. `mpm_validation.py` - Original MPM (no optimization)

---

## Next Session Checklist

When continuing this work:

**Immediate**:
- [ ] Run `python3 direct_tangent_test.py`
- [ ] Check if tangent method provides improvement
- [ ] Verify bearing capacity calculation works

**Debugging** (if direct test fails):
- [ ] Add diagnostic prints to mpm_optimized.py
- [ ] Check particle-foundation contact
- [ ] Verify stress calculations
- [ ] Test with known-good parameters

**Optimization** (if direct test succeeds):
- [ ] Find optimal mesh resolution (60×30 vs 80×40)
- [ ] Test settlement rate range (0.05-0.10 m/s)
- [ ] Determine minimum target settlement for failure
- [ ] Run full comprehensive validation

**Documentation**:
- [ ] Record actual errors achieved
- [ ] Compare with 1957 kN baseline
- [ ] Update parametric study parameters
- [ ] Commit optimized settings

---

## Key Takeaways

### ✅ What We Know

1. **Tangent method is implemented** in `mpm_optimized.py`
2. **Settlement rates can be increased** 10x (0.01 → 0.10 m/s) while staying quasi-static
3. **Target settlement can be reduced** 5x (500mm → 100mm) potentially
4. **Mesh resolution critically affects accuracy** (40×20 gives 71% error)
5. **Original 1957 kN parameters** are documented

### ⚠️  What We Don't Know

1. **Does tangent method actually improve** the 22% error?
2. **Why are simulations stalling** at 80×40 resolution?
3. **What's the optimal mesh** for speed vs accuracy?
4. **Can we reliably reproduce** the 1957 kN result?
5. **What parameters** should be used for parametric study?

### 🎯 Critical Path Forward

**Step 1**: Get ONE successful tangent method test → `direct_tangent_test.py`

**Step 2**: If successful, run comprehensive validation → `validate_tangent_method_comprehensive.py`

**Step 3**: Optimize parameters based on results → mesh + rate + target tuning

**Step 4**: Update parametric study with optimized settings → production runs

---

**Status**: ⏳ Validation in progress, simulations encountering issues
**Blocker**: Need to successfully run at least one tangent method test
**Next Action**: Run `direct_tangent_test.py` and diagnose any failures
**Time Invested**: ~1 hour (setup + test attempts)
**Time Needed**: ~2-3 hours more (debugging + validation + optimization)

