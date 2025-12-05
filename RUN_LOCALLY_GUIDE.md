# 🚀 Running MPM Simulations LOCALLY (No More Colab!)

## Why Leave Colab?

**Colab Problems:**
- ❌ Disconnects randomly (lost 467 minutes of work!)
- ❌ Limited to 12-hour sessions (Free tier)
- ❌ Slow CPU (0.5 seconds per MPM step)
- ❌ Can't save state easily
- ❌ No control over hardware

**Local Advantages:**
- ✅ Run overnight without disconnects
- ✅ Full control (pause/resume anytime)
- ✅ Faster (your own hardware)
- ✅ Easy debugging
- ✅ Can optimize code with Numba/JIT

---

## 🖥️ **Option 1: Run on Your Own Computer (BEST)**

### Requirements:
- **Python 3.8+**
- **8GB RAM minimum** (16GB recommended)
- **CPU**: Any modern multi-core processor
- **Storage**: 1-2 GB for results

### Installation (Windows/Mac/Linux):

```bash
# 1. Install Python (if not already installed)
# Windows: Download from python.org
# Mac: brew install python3
# Linux: sudo apt install python3 python3-pip

# 2. Clone your repository
git clone https://github.com/Srikanth612725/A-mat-Journal.git
cd A-mat-Journal
git checkout claude/fix-simulation-imports-01KfvymVkAdjX1vsHAmvQRLH

# 3. Create virtual environment
python3 -m venv mpm_env
source mpm_env/bin/activate  # Mac/Linux
# OR
mpm_env\Scripts\activate  # Windows

# 4. Install dependencies
pip install numpy pandas scipy matplotlib numba

# 5. Run simulations!
python3 run_tier1_local.py  # See below for this script
```

---

## 🐍 **Create run_tier1_local.py**

I'll create this for you - it's the COLAB script adapted to run locally:

```python
"""
Run TIER 1 Parametric Study LOCALLY
===================================
No Google Drive, no disconnects, full control!
"""

import numpy as np
import pandas as pd
import time
import os
from pathlib import Path

# Import your MPM solver
from mpm_optimized import MPM2D_Optimized
from standard_capacity_methods import davisson_offset_method

print("✅ Starting LOCAL TIER 1 simulation")

# ====================================================================
# CREATE OUTPUT DIRECTORY
# ====================================================================

results_dir = Path("./tier1_results_local")
results_dir.mkdir(exist_ok=True)
print(f"📁 Results will be saved to: {results_dir}")

# ====================================================================
# LOAD OR CREATE PLAN
# ====================================================================

plan_file = "tier1_plan.csv"

if os.path.exists(plan_file):
    df = pd.read_csv(plan_file)
    print(f"✅ Loaded plan: {len(df)} runs")
else:
    # Create default TIER 1 plan (12 runs)
    plan_data = []
    for width in [5.0, 6.84]:
        for su in [6000, 10000]:
            for rep in range(3):
                plan_data.append({
                    'run_id': f'T1_R{len(plan_data)+1:02d}_B{width}_su{int(su/1000)}',
                    'su_Pa': su,
                    'width_m': width,
                    'nx': 60,
                    'ny': 30,
                    'rate_m_per_s': 0.10,  # Faster for testing
                    'target_settlement_m': 0.10,  # Less settlement
                    'use_gimp': False,
                    'record_interval': 200  # Less frequent
                })
    df = pd.DataFrame(plan_data)
    df.to_csv(plan_file, index=False)
    print(f"✅ Created plan: {len(df)} runs")

# ====================================================================
# CHECK FOR CHECKPOINT
# ====================================================================

checkpoint_file = results_dir / "checkpoint.csv"

if checkpoint_file.exists():
    df_completed = pd.read_csv(checkpoint_file)
    if 'status' in df_completed.columns:
        df_successful = df_completed[df_completed['status'] == 'SUCCESS']
        completed_ids = set(df_successful['run_id'].values)
    else:
        completed_ids = set(df_completed['run_id'].values)

    df_remaining = df[~df['run_id'].isin(completed_ids)]
    all_results = df_completed.to_dict('records')

    print(f"⚠️  CHECKPOINT FOUND!")
    print(f"   Successful: {len(completed_ids)} runs")
    if 'status' in df_completed.columns:
        failed = len(df_completed[df_completed['status'] == 'FAILED'])
        print(f"   Failed (will retry): {failed} runs")
    print(f"   Remaining: {len(df_remaining)} runs")
else:
    print("🆕 No checkpoint - starting fresh")
    all_results = []
    df_remaining = df

# ====================================================================
# RUN SIMULATIONS
# ====================================================================

print(f"\n{'='*70}")
print(f"EXECUTING TIER 1 ({len(df_remaining)} runs)")
print(f"{'='*70}\n")

start_total = time.time()

for idx, row in df_remaining.iterrows():
    run_id = row['run_id']
    print(f"\n{'#'*70}")
    print(f"# {len(all_results)+1}/{len(df)}: {run_id}")
    print(f"{'#'*70}")

    try:
        # CREATE MPM SOLVER
        domain_width = row['width_m'] * 6.0
        domain_height = 20.0
        E = row['su_Pa'] * 500

        mpm = MPM2D_Optimized(
            domain_x=(0, domain_width),
            domain_y=(0, domain_height),
            nx=int(row['nx']),
            ny=int(row['ny']),
            su=row['su_Pa'],
            E=E,
            nu=0.495,
            rho=1600,
            use_gimp=bool(row['use_gimp'])
        )

        # ADD SOIL AND FOUNDATION
        mpm.add_soil_block((0, domain_width), (0, 15.0), ppc=4)
        mpm.add_strip_foundation(domain_width/2, 15.0, row['width_m'], 0.5, 2500)

        print(f"✓ Setup complete")

        # RUN SIMULATION
        print(f"Running simulation...")

        settlements, loads = [], []
        mpm.foundation_velocity = -row['rate_m_per_s']
        dt = 0.0001
        step = 0
        run_start = time.time()

        while step < 100000:
            mpm.mpm_step(dt)
            step += 1

            current_y = np.mean([mpm.particles[i].y for i in mpm.foundation_indices])
            if mpm.foundation_y0 is None:
                mpm.foundation_y0 = current_y
            settlement = mpm.foundation_y0 - current_y

            if step % int(row['record_interval']) == 0:
                q = mpm.calculate_bearing_capacity() / 1000
                settlements.append(settlement)
                loads.append(q)

                if step % 1000 == 0:
                    print(f"  Step {step:5d} | s={settlement*1000:5.1f}mm | q={q:6.0f} kN/m", end='\r')

            if settlement >= row['target_settlement_m']:
                break

        runtime = time.time() - run_start

        settlements = np.array(settlements)
        loads = np.array(loads)

        # CALCULATE CAPACITY
        try:
            result = davisson_offset_method(settlements, loads, row['width_m'])
            Q_davisson = result['Q_ult']
        except:
            Q_davisson = np.nan

        Nc = 2 + np.pi
        Q_expected = (row['su_Pa'] / 1000) * row['width_m'] * Nc

        # SAVE DATA
        pd.DataFrame({
            'settlement_m': settlements,
            'load_kN_per_m': loads
        }).to_csv(results_dir / f"{run_id}_data.csv", index=False)

        # STORE RESULT
        all_results.append({
            'run_id': run_id,
            'su_kPa': row['su_Pa'] / 1000,
            'width_m': row['width_m'],
            'Q_expected_kN_per_m': Q_expected,
            'Q_davisson_kN_per_m': Q_davisson,
            'Q_max_kN_per_m': np.max(loads),
            'error_%': abs(Q_davisson - Q_expected) / Q_expected * 100 if not np.isnan(Q_davisson) else np.nan,
            'runtime_min': runtime / 60,
            'status': 'SUCCESS'
        })

        # UPDATE CHECKPOINT
        pd.DataFrame(all_results).to_csv(checkpoint_file, index=False)

        print(f"\n✅ {run_id} complete ({runtime/60:.1f} min)")
        print(f"   Q_davisson: {Q_davisson:.0f} kN/m (expected: {Q_expected:.0f})")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

        all_results.append({
            'run_id': run_id,
            'su_kPa': row['su_Pa'] / 1000,
            'width_m': row['width_m'],
            'status': 'FAILED',
            'error': str(e)
        })

        pd.DataFrame(all_results).to_csv(checkpoint_file, index=False)

# ====================================================================
# FINAL SUMMARY
# ====================================================================

total_time = time.time() - start_total
df_results = pd.DataFrame(all_results)
successful = df_results[df_results['status'] == 'SUCCESS']

print(f"\n{'='*70}")
print(f"🎉 TIER 1 COMPLETE!")
print(f"{'='*70}")
print(f"  ✅ Successful: {len(successful)}/{len(df)}")
print(f"  ⏱️  Total time: {total_time/3600:.2f} hours")
print(f"  📁 Results: {results_dir}")

df_results.to_csv(results_dir / "tier1_results_FINAL.csv", index=False)
print(f"\n✅ Saved: tier1_results_FINAL.csv")
```

---

## ⚡ **Option 2: Cloud VM (If Your Computer is Slow)**

### **Google Cloud Platform (GCP)**

**Advantages:**
- No disconnects
- Pay only for what you use (~$0.10/hour for n1-standard-4)
- Can run 24/7
- SSH access for debugging

**Setup:**

```bash
# 1. Create GCP account (free $300 credit)
# 2. Create VM instance:
#    - Machine type: n1-standard-4 (4 vCPUs, 15GB RAM)
#    - Boot disk: Ubuntu 20.04 LTS (20GB)
#    - Allow HTTP/HTTPS traffic

# 3. SSH into VM
gcloud compute ssh your-vm-name

# 4. Install Python and dependencies
sudo apt update
sudo apt install python3-pip python3-venv git
git clone https://github.com/Srikanth612725/A-mat-Journal.git
cd A-mat-Journal
python3 -m venv mpm_env
source mpm_env/bin/activate
pip install numpy pandas scipy matplotlib numba

# 5. Run simulations
nohup python3 run_tier1_local.py > tier1.log 2>&1 &

# 6. Monitor progress
tail -f tier1.log

# 7. Download results when done
gcloud compute scp your-vm-name:~/A-mat-Journal/tier1_results_local/* ./
```

**Cost estimate:**
- 12 runs × 4 hours × $0.10/hour = **$4.80 total**

---

### **AWS EC2**

Similar to GCP, slightly different pricing:
- Instance type: t3.large (2 vCPUs, 8GB RAM)
- Cost: ~$0.08/hour
- Total: ~$3.84 for 12 runs

---

## 🎯 **My Recommendation**

**For you: Run LOCALLY on your own computer**

Why?
1. ✅ Free (no cloud costs)
2. ✅ Full control
3. ✅ Easy debugging
4. ✅ Can pause/resume
5. ✅ No network issues

Just let it run overnight!

**Expected performance:**
- If your computer has 4+ CPU cores: ~2-3 hours total
- If slower (2 cores): ~6-8 hours total
- Still much better than Colab (disconnects!)

---

## 📊 **Monitoring Progress**

While running locally, you can:

```bash
# Monitor in real-time
tail -f tier1.log  # If running with `nohup python3 run_tier1_local.py > tier1.log 2>&1 &`

# Check checkpoint
cat tier1_results_local/checkpoint.csv

# Count completed runs
grep "SUCCESS" tier1_results_local/checkpoint.csv | wc -l
```

---

## 🐛 **If Something Goes Wrong**

The checkpoint system will save your progress!

Just re-run:
```bash
python3 run_tier1_local.py
```

It will:
- ✅ Load the checkpoint
- ✅ Skip completed runs
- ✅ Retry failed runs
- ✅ Continue from where it left off

---

## ❓ **Questions?**

**Q: My computer is too slow?**
A: Use the cloud VM option above (~$5 total)

**Q: Can I speed it up?**
A: Yes! Install Numba for 10-100× speedup:
```python
pip install numba
```

**Q: Can I use my GPU?**
A: Not directly with this code, but possible with CuPy/JAX

**Q: How do I transfer results?**
A: They're saved in `tier1_results_local/` - just copy the folder!

---

Would you like me to create the `run_tier1_local.py` script for you?
