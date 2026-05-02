# 09_rock_physics — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `notebooks/09_rock_physics.ipynb` — Vs modelling via Dvorkin-Nur contact cement calibration, producing a `VS_RPM` log and calibration crossplots.

**Architecture:** Build the notebook JSON incrementally using Python insertion scripts, mirroring the approach used in 06–08. Each task adds one or two cells and verifies their output by running the notebook. All rock physics via `qsi` (at `/Users/abd/Developer/qsi`).

**Tech Stack:** Python 3, numpy, scipy.optimize, matplotlib, qsi (contact_cement, cemented_sand, soft_sediments, brine_properties, voigt_reuss_hill), Jupyter notebook JSON manipulation.

---

## Pre-flight: Verified API Behaviour

These were confirmed before writing the plan — do not re-test:

- `brine_properties(sal_ppm, P_MPa, T_C)` → `(vp km/s, rho g/cc, k GPa)` — multiply by `1e3/1e3/1e9` for SI
- `voigt_reuss_hill([f1,f2], [k1,k2], [g1,g2])` → `(k_v, k_r, k_hill, g_v, g_r, g_hill)` — scalars only; use manual numpy VRH for arrays
- `contact_cement(phi, phi_c, coord, g_grain, k_grain, g_cem, k_cem, k_fl, scheme)` — accepts array `k_grain`/`g_grain`; **always zero `g_frame[-1]`** → append a dummy endpoint and strip it
- `cemented_sand(clay, phi_c, f_cement, k_fl, rho_fl)` → 14 arrays: `(phi_cem, vp_sat, vs_sat, rho_sat, vp_dry, vs_dry, rho_dry, phi_sort, vp_sat_sort, ...)`
- `soft_sediments(clay, pressure, phi_c, coord, k_fl, rho_fl)` → 7 arrays: `(phi, vp_dry, vs_dry, rho_dry, vp_sat, vs_sat, rho_sat)` — `pressure` in Pa

---

## File to Create

`notebooks/09_rock_physics.ipynb` — new notebook, built cell-by-cell via Python scripts below.

---

## Task 1: Create notebook skeleton with imports and config

**Files:**
- Create: `notebooks/09_rock_physics.ipynb`

- [ ] **Step 1: Create the notebook JSON with header markdown + imports cell**

```python
# run from /Users/abd/Developer/petro-rock
import json
from pathlib import Path

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                 "language_info": {"name": "python", "version": "3.11.0"}},
    "cells": []
}

def md(cell_id, src): return {"cell_type":"markdown","id":cell_id,"metadata":{},"source":src}
def code(cell_id, src): return {"cell_type":"code","execution_count":None,"id":cell_id,"metadata":{},"outputs":[],"source":src}

nb["cells"].append(md("cell-0", [
    "# Phase 9 — Rock Physics Modelling: Vs from Contact Cement\n\n",
    "**Field**: Dvalin, Norwegian Sea\n\n",
    "Builds a **VS_RPM** log using the Dvorkin-Nur contact cement model calibrated per formation.\n",
    "Inputs: VP_OK, PHIT, RHOB_OK, VWCL, DIFF_PRESS from previous pipeline phases.\n\n",
    "- **Step 9.1** — Load data\n",
    "- **Step 9.2** — VRH mineral mixing (quartz + clay using VWCL)\n",
    "- **Step 9.3** — Per-formation calibration of critical porosity φ_c\n",
    "- **Step 9.4** — Apply model → VS_RPM log\n",
    "- **Step 9.5** — Log display: VS_RPM vs VS_OK vs VS_Castagna\n",
    "- **Step 9.6** — Vp–Vs crossplot with cement trend lines\n",
    "- **Step 9.7** — Vp–φ crossplot with cement trend lines\n",
    "- **Step 9.8** — Save output\n"
]))

nb["cells"].append(code("cell-1", [
    "import sys\n",
    "sys.path.insert(0, '/Users/abd/Developer/qsi')\n",
    "sys.path.insert(0, '..')\n",
    "\n",
    "import numpy as np\n",
    "import pandas as pd\n",
    "import matplotlib.pyplot as plt\n",
    "import matplotlib.ticker as ticker\n",
    "import matplotlib.patches as mpatches\n",
    "from matplotlib.lines import Line2D\n",
    "from matplotlib.transforms import blended_transform_factory\n",
    "from pathlib import Path\n",
    "from scipy.optimize import minimize_scalar\n",
    "import lasio, importlib\n",
    "\n",
    "import well_config; importlib.reload(well_config)\n",
    "from well_config import get_cfg, set_plot_style, load_tops, form_colours, ACTIVE_WELL\n",
    "\n",
    "from qsi.models.cement       import contact_cement\n",
    "from qsi.models.cemented_sand import cemented_sand\n",
    "from qsi.models.soft_sediments import soft_sediments\n",
    "from qsi.moduli.bounds       import voigt_reuss_hill\n",
    "from qsi.moduli.gassmann     import gassmann_sat\n",
    "from qsi.fluids.batzle_wang  import brine_properties\n",
    "\n",
    "# ── Well selection ────────────────────────────────────────────────────────────\n",
    "WELL_NAME = ACTIVE_WELL\n",
    "cfg       = get_cfg(WELL_NAME)\n",
    "set_plot_style()\n",
    "\n",
    "# ── Paths ─────────────────────────────────────────────────────────────────────\n",
    "WELL_FILE   = Path('..') / cfg['las_file']\n",
    "TOPS_FILE   = Path('..') / cfg['tops_file']\n",
    "ELASTIC_IN  = Path(f'../wells/{WELL_NAME}_elastic.parquet')\n",
    "RHOB_IN     = Path(f'../wells/{WELL_NAME}_rhob_ok.parquet')\n",
    "COMPUTED_IN = Path(f'../wells/{WELL_NAME}_computed.parquet')\n",
    "FAUST_IN    = Path(f'../wells/{WELL_NAME}_faust.parquet')\n",
    "OUT_FILE    = Path(f'../wells/{WELL_NAME}_rockphysics.parquet')\n",
    "\n",
    "# ── Mineral end-members (Pa, kg/m³) ──────────────────────────────────────────\n",
    "K_QUARTZ  = 36.6e9;  G_QUARTZ  = 45.0e9;  RHO_QUARTZ  = 2650.0\n",
    "K_CLAY    = 25.0e9;  G_CLAY    = 9.0e9;   RHO_CLAY    = 2580.0\n",
    "K_CEMENT  = 36.6e9;  G_CEMENT  = 45.0e9   # quartz cement\n",
    "\n",
    "# ── Contact cement model defaults ─────────────────────────────────────────────\n",
    "PHI_C_GLOBAL = 0.40   # calibrated per formation in Step 9.3\n",
    "CN           = 8.0    # coordination number (explore later)\n",
    "SCHEME       = 2      # cement uniformly on grain surface\n",
    "\n",
    "print('qsi imports OK')\n",
    "print(f'Well: {WELL_NAME}')\n"
]))

Path('notebooks/09_rock_physics.ipynb').write_text(json.dumps(nb, indent=1))
print("Created notebooks/09_rock_physics.ipynb")
```

- [ ] **Step 2: Verify the file exists and parses**

```bash
python3 -c "import json; nb=json.load(open('notebooks/09_rock_physics.ipynb')); print(f'{len(nb[\"cells\"])} cells OK')"
```
Expected: `2 cells OK`

---

## Task 2: Data loading cell

**Files:**
- Modify: `notebooks/09_rock_physics.ipynb` (append 2 cells)

- [ ] **Step 1: Append the markdown + data-load code cell**

```python
import json
from pathlib import Path

nb = json.loads(Path('notebooks/09_rock_physics.ipynb').read_text())

def md(cell_id, src): return {"cell_type":"markdown","id":cell_id,"metadata":{},"source":src}
def code(cell_id, src): return {"cell_type":"code","execution_count":None,"id":cell_id,"metadata":{},"outputs":[],"source":src}

nb["cells"].append(md("cell-2", ["## Step 9.1 — Load Data\n"]))

nb["cells"].append(code("cell-3", [
    "# ── Load LAS (for PHIT, VWCL not yet in any parquet) ────────────────────────\n",
    "las = lasio.read(WELL_FILE)\n",
    "df  = las.df()\n",
    "df.replace(-999.25, np.nan, inplace=True)\n",
    "df.rename(columns=cfg.get('curve_map', {}), inplace=True)\n",
    "df.index.name = 'DEPTH_MD'\n",
    "\n",
    "# ── Join all pipeline parquets ────────────────────────────────────────────────\n",
    "for pq_path in [ELASTIC_IN, RHOB_IN, COMPUTED_IN, FAUST_IN]:\n",
    "    tmp = pd.read_parquet(pq_path)\n",
    "    df  = df.join(tmp[[c for c in tmp.columns if c not in df.columns]], how='left')\n",
    "\n",
    "LOG_TOP  = cfg['log_top']  if cfg['log_top']  is not None else df.index[0]\n",
    "LOG_BASE = cfg['log_base'] if cfg['log_base'] is not None else df.index[-1]\n",
    "sub = df.loc[LOG_TOP:LOG_BASE].copy()\n",
    "\n",
    "# ── Formation assignment ──────────────────────────────────────────────────────\n",
    "f1a = load_tops(TOPS_FILE, cfg['tops_well_id'])\n",
    "TOPS_MD       = dict(zip(f1a['PICKS'], f1a['DEPTH'])) if not f1a.empty else {}\n",
    "FORM_COLORS   = form_colours(TOPS_MD.keys())\n",
    "RESERVOIR_TOP = f1a.iloc[-1]['PICKS'] if not f1a.empty else None\n",
    "top_list      = sorted(TOPS_MD.items(), key=lambda x: x[1])\n",
    "sub['FORMATION'] = 'Other'\n",
    "for _name, _md_top in top_list:\n",
    "    sub.loc[sub.index >= _md_top, 'FORMATION'] = _name\n",
    "\n",
    "# ── Confirm key columns ───────────────────────────────────────────────────────\n",
    "print(f'Interval: {LOG_TOP}–{LOG_BASE} m MD  ({len(sub):,} samples)')\n",
    "print()\n",
    "for col in ['VP_OK','VS','VS_OK','RHOB_OK','PHIT','VWCL',\n",
    "            'DIFF_PRESS','ELASTIC_EDIT','VP_SOURCE']:\n",
    "    n = int(sub[col].notna().sum()) if col in sub.columns else -1\n",
    "    tag = f'{n:,} valid' if n >= 0 else 'MISSING'\n",
    "    print(f'  {col:<18}: {tag}')\n"
]))

Path('notebooks/09_rock_physics.ipynb').write_text(json.dumps(nb, indent=1))
print("Appended data-load cells")
```

- [ ] **Step 2: Run cell-3 in Jupyter and check for MISSING columns**

Expected output (approximate):
```
Interval: 0–4589 m MD  (30,119 samples)
  VP_OK             : 26,548 valid
  VS                : 15,378 valid
  VS_OK             : 26,613 valid
  RHOB_OK           : 26,566 valid
  PHIT              : ~20,000 valid
  VWCL              : ~20,000 valid
  DIFF_PRESS        : 30,119 valid
  ELASTIC_EDIT      : 30,119 valid
  VP_SOURCE         : 30,119 valid
```
If any required column shows MISSING, check the join logic.

---

## Task 3: VRH mineral mixing cell

**Files:**
- Modify: `notebooks/09_rock_physics.ipynb` (append 2 cells)

- [ ] **Step 1: Append markdown + VRH code cell**

```python
import json
import numpy as np
from pathlib import Path

nb = json.loads(Path('notebooks/09_rock_physics.ipynb').read_text())

def md(cell_id, src): return {"cell_type":"markdown","id":cell_id,"metadata":{},"source":src}
def code(cell_id, src): return {"cell_type":"code","execution_count":None,"id":cell_id,"metadata":{},"outputs":[],"source":src}

nb["cells"].append(md("cell-4", [
    "## Step 9.2 — VRH Mineral Mixing\n\n",
    "Hill average of quartz and clay using VWCL. `voigt_reuss_hill` from qsi is scalar-only,\n",
    "so VRH is computed manually element-wise.\n"
]))

nb["cells"].append(code("cell-5", [
    "# ── VRH mineral mixing (element-wise, quartz + clay) ─────────────────────────\n",
    "vwcl = np.clip(sub['VWCL'].values.astype(float), 1e-6, 1.0 - 1e-6)\n",
    "vwcl = np.where(np.isnan(sub['VWCL'].values), np.nan, vwcl)\n",
    "vqtz = 1.0 - np.where(np.isnan(vwcl), np.nan, vwcl)\n",
    "\n",
    "# Voigt (upper)\n",
    "k_v = vwcl * K_CLAY + vqtz * K_QUARTZ\n",
    "g_v = vwcl * G_CLAY + vqtz * G_QUARTZ\n",
    "# Reuss (lower)\n",
    "k_r = 1.0 / (vwcl / K_CLAY + vqtz / K_QUARTZ)\n",
    "g_r = 1.0 / (vwcl / G_CLAY + vqtz / G_QUARTZ)\n",
    "# Hill average\n",
    "sub['K_MIN'] = 0.5 * (k_v + k_r)\n",
    "sub['G_MIN'] = 0.5 * (g_v + g_r)\n",
    "sub['RHO_MIN'] = vwcl * RHO_CLAY + vqtz * RHO_QUARTZ\n",
    "\n",
    "print('VRH mineral mixing complete')\n",
    "print(f\"  K_min range: {sub['K_MIN'].min()/1e9:.2f}–{sub['K_MIN'].max()/1e9:.2f} GPa\")\n",
    "print(f\"  G_min range: {sub['G_MIN'].min()/1e9:.2f}–{sub['G_MIN'].max()/1e9:.2f} GPa\")\n",
    "print(f\"  Valid samples: {sub['K_MIN'].notna().sum():,}\")\n",
    "\n",
    "# ── Quick verification: K_min vs VWCL scatter ─────────────────────────────────\n",
    "fig, ax = plt.subplots(figsize=(6, 4))\n",
    "form_order = [n for n,_ in top_list]\n",
    "for fname in form_order:\n",
    "    fd = sub[sub['FORMATION'] == fname]\n",
    "    ax.scatter(fd['VWCL'], fd['K_MIN']/1e9, s=2, alpha=0.3,\n",
    "               color=FORM_COLORS.get(fname,'#888'), label=fname, rasterized=True)\n",
    "ax.set_xlabel('VWCL (vol frac)', fontsize=9)\n",
    "ax.set_ylabel('K_min Hill (GPa)', fontsize=9)\n",
    "ax.set_title('VRH mineral mixing verification', fontsize=9, fontweight='bold')\n",
    "ax.legend(fontsize=7, markerscale=4)\n",
    "ax.grid(True, alpha=0.2)\n",
    "plt.tight_layout(); plt.show()\n"
]))

Path('notebooks/09_rock_physics.ipynb').write_text(json.dumps(nb, indent=1))
print("Appended VRH cells")
```

- [ ] **Step 2: Run cell-5 and verify**

Expected output:
```
VRH mineral mixing complete
  K_min range: 25.xx–36.60 GPa   (25 = pure clay, 36.6 = pure quartz)
  G_min range: 9.xx–45.00 GPa
  Valid samples: ~20,000+
```
The scatter should show a monotonically decreasing K_min as VWCL increases, from ~36.6 GPa (clean sand) toward ~25 GPa (shale).

---

## Task 4: Per-formation φ_c calibration cell

**Files:**
- Modify: `notebooks/09_rock_physics.ipynb` (append 2 cells)

- [ ] **Step 1: Append markdown + calibration code cell**

```python
import json
from pathlib import Path

nb = json.loads(Path('notebooks/09_rock_physics.ipynb').read_text())

def md(cell_id, src): return {"cell_type":"markdown","id":cell_id,"metadata":{},"source":src}
def code(cell_id, src): return {"cell_type":"code","execution_count":None,"id":cell_id,"metadata":{},"outputs":[],"source":src}

nb["cells"].append(md("cell-6", [
    "## Step 9.3 — Per-Formation Calibration of φ_c\n\n",
    "In `contact_cement`, cement fraction = φ_c − φ is computed internally — φ_c is the only\n",
    "free calibration parameter. Minimise RMS(VS_pred − VS_meas) per formation using\n",
    "`scipy.optimize.minimize_scalar`.\n\n",
    "**Calibration domain**: samples with measured DTS (`VS.notna()`), measured Vp\n",
    "(`VP_SOURCE==0`), no elastic edits (`ELASTIC_EDIT==0`), and valid PHIT/RHOB_OK/DIFF_PRESS.\n\n",
    "**contact_cement note**: `g_frame[-1]` is always zeroed internally. Fix: append a dummy\n",
    "endpoint so the zeroing only affects the dummy, then strip it.\n"
]))

nb["cells"].append(code("cell-7", [
    "# ── Brine properties (median T/P for calibration) ────────────────────────────\n",
    "med_T = float(sub['TEMP'].median())\n",
    "med_P = float(sub['DIFF_PRESS'].median())\n",
    "SAL   = cfg.get('salinity_ppm', 35000)\n",
    "_vp_br, _rho_br, _k_br = brine_properties(sal=SAL, P=med_P, T=med_T)\n",
    "K_BRINE_MED  = float(_k_br)  * 1e9   # GPa → Pa\n",
    "RHO_BRINE_MED = float(_rho_br) * 1e3  # g/cc → kg/m³\n",
    "print(f'Brine  T={med_T:.1f}°C  P={med_P:.1f} MPa  sal={SAL} ppm')\n",
    "print(f'       K={_k_br:.3f} GPa  rho={_rho_br:.3f} g/cc  Vp={_vp_br*1e3:.0f} m/s')\n",
    "\n",
    "# ── Helper: VS from contact cement (vectorised, array k/g_grain) ──────────────\n",
    "def cement_vs(phi_arr, k_min_arr, g_min_arr, rho_sat_arr, phi_c_val):\n",
    "    \"\"\"Return VS_pred (m/s) for each sample; NaN where phi >= phi_c.\"\"\"\n",
    "    valid = (phi_arr < phi_c_val) & (phi_arr > 0) & np.isfinite(phi_arr)\n",
    "    vs_out = np.full(len(phi_arr), np.nan)\n",
    "    if valid.sum() == 0:\n",
    "        return vs_out\n",
    "    pv = phi_arr[valid]\n",
    "    kv = k_min_arr[valid]\n",
    "    gv = g_min_arr[valid]\n",
    "    rv = rho_sat_arr[valid] * 1000.0   # g/cc → kg/m³\n",
    "    # Append dummy endpoint so contact_cement's [-1]=0 only hits the dummy\n",
    "    phi_in = np.append(pv, phi_c_val * 0.999)\n",
    "    k_in   = np.append(kv, kv[-1])\n",
    "    g_in   = np.append(gv, gv[-1])\n",
    "    _, g_frame = contact_cement(phi_in, phi_c_val, CN, g_in, k_in,\n",
    "                                 G_CEMENT, K_CEMENT, K_BRINE_MED, SCHEME)\n",
    "    gf = g_frame[:-1]   # strip dummy\n",
    "    vs_out[valid] = np.sqrt(np.where(gf > 0, gf / rv, np.nan))\n",
    "    return vs_out\n",
    "\n",
    "# ── Per-formation calibration ─────────────────────────────────────────────────\n",
    "phi_c_dict   = {}\n",
    "calib_rows   = []\n",
    "\n",
    "print()\n",
    "print(f\"{'Formation':<20} {'n_cal':>7} {'phi_c':>7} {'RMS (m/s)':>10} {'RMS%':>7}\")\n",
    "print('─' * 60)\n",
    "\n",
    "for i, (fname, md_top) in enumerate(top_list):\n",
    "    md_base = top_list[i+1][1] if i+1 < len(top_list) else LOG_BASE\n",
    "    fm = sub.loc[md_top:md_base]\n",
    "\n",
    "    cmask = (\n",
    "        fm['VS'].notna() &\n",
    "        (fm.get('VP_SOURCE',   pd.Series(0, index=fm.index)) == 0) &\n",
    "        (fm.get('ELASTIC_EDIT', pd.Series(0, index=fm.index)) == 0) &\n",
    "        fm['PHIT'].notna() & fm['RHOB_OK'].notna() &\n",
    "        fm['DIFF_PRESS'].notna() & fm['K_MIN'].notna()\n",
    "    )\n",
    "    n_cal = int(cmask.sum())\n",
    "\n",
    "    if n_cal < 30:\n",
    "        phi_c_dict[fname] = PHI_C_GLOBAL\n",
    "        print(f\"{fname:<20} {n_cal:>7,}    —        —       < 30 pts → global {PHI_C_GLOBAL:.2f}\")\n",
    "        continue\n",
    "\n",
    "    phi_c   = fm.loc[cmask, 'PHIT'].values.astype(float)\n",
    "    k_min_c = fm.loc[cmask, 'K_MIN'].values.astype(float)\n",
    "    g_min_c = fm.loc[cmask, 'G_MIN'].values.astype(float)\n",
    "    rho_c   = fm.loc[cmask, 'RHOB_OK'].values.astype(float)\n",
    "    vs_meas = fm.loc[cmask, 'VS'].values.astype(float)\n",
    "\n",
    "    def rms_fn(phi_c_trial):\n",
    "        vs_p  = cement_vs(phi_c, k_min_c, g_min_c, rho_c, phi_c_trial)\n",
    "        ok    = np.isfinite(vs_p) & np.isfinite(vs_meas)\n",
    "        return float(np.sqrt(np.mean((vs_p[ok] - vs_meas[ok])**2))) if ok.sum() > 5 else 1e6\n",
    "\n",
    "    res       = minimize_scalar(rms_fn, bounds=(0.30, 0.50), method='bounded')\n",
    "    phi_c_cal = float(res.x)\n",
    "    rms_cal   = float(res.fun)\n",
    "    rms_pct   = 100.0 * rms_cal / float(np.nanmean(vs_meas))\n",
    "\n",
    "    phi_c_dict[fname] = phi_c_cal\n",
    "    calib_rows.append(dict(formation=fname, n_cal=n_cal, phi_c=phi_c_cal,\n",
    "                           rms_ms=rms_cal, rms_pct=rms_pct))\n",
    "    print(f\"{fname:<20} {n_cal:>7,} {phi_c_cal:>7.3f} {rms_cal:>10.0f} {rms_pct:>7.1f}%\")\n",
    "\n",
    "calib_df = pd.DataFrame(calib_rows)\n",
    "print(f'\\nCalibrated {len(calib_rows)} formation(s); {len(phi_c_dict)} total (incl. fallbacks)')\n"
]))

Path('notebooks/09_rock_physics.ipynb').write_text(json.dumps(nb, indent=1))
print("Appended calibration cells")
```

- [ ] **Step 2: Run cell-7 and verify**

Expected: table with per-formation phi_c between 0.30 and 0.50, RMS typically 50–200 m/s (5–15% of mean VS ~1500–2000 m/s). Formations with < 30 calibration points show "global 0.40".

---

## Task 5: VS_RPM log generation cell

**Files:**
- Modify: `notebooks/09_rock_physics.ipynb` (append 2 cells)

- [ ] **Step 1: Append markdown + VS_RPM code cell**

```python
import json
from pathlib import Path

nb = json.loads(Path('notebooks/09_rock_physics.ipynb').read_text())

def md(cell_id, src): return {"cell_type":"markdown","id":cell_id,"metadata":{},"source":src}
def code(cell_id, src): return {"cell_type":"code","execution_count":None,"id":cell_id,"metadata":{},"outputs":[],"source":src}

nb["cells"].append(md("cell-8", [
    "## Step 9.4 — Apply Model: VS_RPM Log\n\n",
    "Apply the per-formation calibrated φ_c to every sample with valid PHIT and RHOB_OK.\n",
    "Samples with PHIT ≥ φ_c (above suspension limit) receive NaN.\n"
]))

nb["cells"].append(code("cell-9", [
    "# ── Apply calibrated cement model to full logging interval ───────────────────\n",
    "vs_rpm   = np.full(len(sub), np.nan)\n",
    "phi_c_log = np.full(len(sub), np.nan)   # which phi_c was used per sample\n",
    "\n",
    "for i, (fname, md_top) in enumerate(top_list):\n",
    "    md_base  = top_list[i+1][1] if i+1 < len(top_list) else LOG_BASE\n",
    "    phi_c_fm = phi_c_dict.get(fname, PHI_C_GLOBAL)\n",
    "\n",
    "    fm      = sub.loc[md_top:md_base]\n",
    "    fm_idx  = fm.index\n",
    "    valid   = (\n",
    "        fm['PHIT'].notna() & fm['RHOB_OK'].notna() & fm['K_MIN'].notna() &\n",
    "        (fm['PHIT'] < phi_c_fm) & (fm['PHIT'] > 0)\n",
    "    )\n",
    "    if valid.sum() == 0:\n",
    "        continue\n",
    "\n",
    "    phi_v   = fm.loc[valid, 'PHIT'].values.astype(float)\n",
    "    k_min_v = fm.loc[valid, 'K_MIN'].values.astype(float)\n",
    "    g_min_v = fm.loc[valid, 'G_MIN'].values.astype(float)\n",
    "    rho_v   = fm.loc[valid, 'RHOB_OK'].values.astype(float)\n",
    "\n",
    "    vs_v = cement_vs(phi_v, k_min_v, g_min_v, rho_v, phi_c_fm)\n",
    "\n",
    "    # Write back using integer positional indexing\n",
    "    global_pos = sub.index.get_indexer(fm_idx[valid])\n",
    "    vs_rpm[global_pos]    = vs_v\n",
    "    phi_c_log[global_pos] = phi_c_fm\n",
    "\n",
    "sub['VS_RPM']     = vs_rpm\n",
    "sub['PHI_C_CEMENT'] = phi_c_log\n",
    "\n",
    "# ── Summary ───────────────────────────────────────────────────────────────────\n",
    "n_rpm       = int(np.isfinite(vs_rpm).sum())\n",
    "n_vs_meas   = int(sub['VS'].notna().sum())\n",
    "n_vs_ok     = int(sub['VS_OK'].notna().sum())\n",
    "\n",
    "print('VS_RPM coverage summary:')\n",
    "print(f'  VS_RPM          : {n_rpm:,} samples ({100*n_rpm/len(sub):.1f}%)')\n",
    "print(f'  VS (measured)   : {n_vs_meas:,} samples ({100*n_vs_meas/len(sub):.1f}%)')\n",
    "print(f'  VS_OK (w/ cast.): {n_vs_ok:,} samples ({100*n_vs_ok/len(sub):.1f}%)')\n",
    "print(f'  VS_RPM range    : {np.nanmin(vs_rpm):.0f}–{np.nanmax(vs_rpm):.0f} m/s')\n",
    "\n",
    "# Quick sanity: VS_RPM vs VS_OK where both valid\n",
    "both = sub['VS_OK'].notna() & sub['VS_RPM'].notna()\n",
    "if both.sum() > 0:\n",
    "    rms_vs = float(np.sqrt(np.mean((sub.loc[both,'VS_RPM'] - sub.loc[both,'VS_OK'])**2)))\n",
    "    print(f'  RMS(VS_RPM − VS_OK) where both valid: {rms_vs:.0f} m/s')\n"
]))

Path('notebooks/09_rock_physics.ipynb').write_text(json.dumps(nb, indent=1))
print("Appended VS_RPM cells")
```

- [ ] **Step 2: Run cell-9 and verify**

Expected:
```
VS_RPM coverage summary:
  VS_RPM          : ~18,000–22,000 samples (60–75%)
  VS (measured)   : 15,378 samples (51.1%)
  VS_OK (w/ cast.): 26,613 samples (88.4%)
  VS_RPM range    : ~800–3000 m/s
  RMS(VS_RPM − VS_OK) where both valid: varies
```
If VS_RPM range is wildly outside 700–3500 m/s, check the `* 1000` conversion for g/cc → kg/m³.

---

## Task 6: Log display cell

**Files:**
- Modify: `notebooks/09_rock_physics.ipynb` (append 2 cells)

- [ ] **Step 1: Append markdown + log display code cell**

```python
import json
from pathlib import Path

nb = json.loads(Path('notebooks/09_rock_physics.ipynb').read_text())

def md(cell_id, src): return {"cell_type":"markdown","id":cell_id,"metadata":{},"source":src}
def code(cell_id, src): return {"cell_type":"code","execution_count":None,"id":cell_id,"metadata":{},"outputs":[],"source":src}

nb["cells"].append(md("cell-10", [
    "## Step 9.5 — Log Display: VS Comparison\n\n",
    "Four-track display: GR, RHOB_OK, VP_OK, and shear velocity comparison.\n",
    "VS_RPM (cement model) vs VS (measured) vs VS_OK (Castagna-filled).\n"
]))

nb["cells"].append(code("cell-11", [
    "depth = sub.index.values\n",
    "fig, axes = plt.subplots(1, 4, figsize=(16, 14), sharey=True,\n",
    "                          gridspec_kw={'width_ratios': [0.8, 0.9, 1.0, 1.4]})\n",
    "fig.subplots_adjust(top=0.93, bottom=0.06, left=0.07, right=0.98, wspace=0.07)\n",
    "\n",
    "def _top_axis(ax, label, color):\n",
    "    ax.xaxis.tick_top(); ax.xaxis.set_label_position('top')\n",
    "    ax.set_xlabel(label, color=color, fontsize=8, labelpad=4)\n",
    "    ax.tick_params(axis='x', colors=color, labelsize=7)\n",
    "    ax.grid(True, alpha=0.2)\n",
    "\n",
    "# Track 1: GR\n",
    "ax = axes[0]\n",
    "ax.plot(sub['GR'], depth, color='#4A7C40', lw=0.8)\n",
    "ax.fill_betweenx(depth, sub['GR'], 75, where=sub['GR']>75,  color='#6B8E5A', alpha=0.4)\n",
    "ax.fill_betweenx(depth, sub['GR'], 75, where=sub['GR']<=75, color='#F0D060', alpha=0.4)\n",
    "ax.set_xlim(0, 150); _top_axis(ax, 'GR (API)', '#4A7C40')\n",
    "ax.set_ylabel('Depth (m MD)', fontsize=10)\n",
    "ax.set_title('GR', fontsize=10, fontweight='bold', pad=14)\n",
    "ax.invert_yaxis()\n",
    "ax.yaxis.set_major_locator(ticker.MultipleLocator(100))\n",
    "ax.yaxis.set_minor_locator(ticker.MultipleLocator(50))\n",
    "\n",
    "# Track 2: RHOB_OK\n",
    "ax = axes[1]\n",
    "ax.plot(sub['RHOB_OK'], depth, color='#8B0000', lw=0.9)\n",
    "ax.set_xlim(1.6, 3.0); _top_axis(ax, 'RHOB_OK (g/cc)', '#8B0000')\n",
    "ax.set_title('Density', fontsize=10, fontweight='bold', pad=14)\n",
    "\n",
    "# Track 3: VP_OK\n",
    "ax = axes[2]\n",
    "ax.plot(sub['VP_OK'], depth, color='#1B2631', lw=0.9)\n",
    "ax.set_xlim(1000, 6000); _top_axis(ax, 'VP_OK (m/s)', '#1B2631')\n",
    "ax.set_title('Vp', fontsize=10, fontweight='bold', pad=14)\n",
    "\n",
    "# Track 4: VS comparison\n",
    "ax = axes[3]\n",
    "if 'VS_CASTAGNA' in sub.columns:\n",
    "    ax.plot(sub['VS_CASTAGNA'], depth, color='#AAB7B8', lw=0.7,\n",
    "            ls='--', alpha=0.6, label='Castagna (NB08)')\n",
    "ax.plot(sub['VS_OK'],  depth, color='#2E86C1', lw=0.8, alpha=0.7, label='VS_OK')\n",
    "ax.plot(sub['VS_RPM'], depth, color='#E74C3C', lw=1.0, alpha=0.9, label='VS_RPM (cement)')\n",
    "ax.plot(sub['VS'],     depth, color='#1B2631', lw=1.2, alpha=0.6, label='VS (measured)')\n",
    "ax.set_xlim(400, 3500); _top_axis(ax, 'Vs (m/s)', '#1B2631')\n",
    "ax.set_title('Shear velocity', fontsize=10, fontweight='bold', pad=14)\n",
    "ax.legend(fontsize=7.5, loc='lower right', framealpha=0.85)\n",
    "\n",
    "# Formation tops on all tracks\n",
    "label_trans = blended_transform_factory(axes[0].transAxes, axes[0].transData)\n",
    "for _name, _md_top in TOPS_MD.items():\n",
    "    if not (depth.min() <= _md_top <= depth.max()): continue\n",
    "    lc = '#1A5276' if _name == RESERVOIR_TOP else '#5D4E37'\n",
    "    for ax in axes:\n",
    "        ax.axhline(_md_top, color=lc, lw=0.85, ls=(0,(7,4)), alpha=0.85, zorder=4)\n",
    "    axes[0].text(0.02, _md_top-(depth[-1]-depth[0])*0.003, _name,\n",
    "                 transform=label_trans, fontsize=6.5, va='bottom', color=lc,\n",
    "                 fontweight='bold' if _name == RESERVOIR_TOP else 'normal',\n",
    "                 bbox=dict(facecolor='white', alpha=0.75, edgecolor='none', pad=1.2), zorder=5)\n",
    "\n",
    "fig.suptitle(f'{WELL_NAME} — VS comparison: measured vs cement model vs Castagna',\n",
    "             fontsize=11, fontweight='bold')\n",
    "plt.show()\n"
]))

Path('notebooks/09_rock_physics.ipynb').write_text(json.dumps(nb, indent=1))
print("Appended log display cells")
```

- [ ] **Step 2: Run cell-11 and verify** — four-track log renders without errors; VS_RPM (red) tracks measured VS (black) broadly and diverges from Castagna (grey dashed) in reservoir sections.

---

## Task 7: Vp–Vs crossplot with cement trend lines

**Files:**
- Modify: `notebooks/09_rock_physics.ipynb` (append 2 cells)

- [ ] **Step 1: Append markdown + crossplot code cell**

```python
import json
from pathlib import Path

nb = json.loads(Path('notebooks/09_rock_physics.ipynb').read_text())

def md(cell_id, src): return {"cell_type":"markdown","id":cell_id,"metadata":{},"source":src}
def code(cell_id, src): return {"cell_type":"code","execution_count":None,"id":cell_id,"metadata":{},"outputs":[],"source":src}

nb["cells"].append(md("cell-12", [
    "## Step 9.6 — Vp–Vs Crossplot with Cement Trend Lines\n\n",
    "Measured data (VP_OK, VS) coloured by formation. Cement model trend lines at\n",
    "f_cement = 0.0, 0.02, 0.05, 0.10 (using mean VWCL for the whole interval).\n",
    "Soft-sediments (uncemented) lower bound shown as dashed grey.\n"
]))

nb["cells"].append(code("cell-13", [
    "# ── Brine for trend lines ─────────────────────────────────────────────────────\n",
    "_vp_br, _rho_br, _k_br = brine_properties(sal=SAL, P=med_P, T=med_T)\n",
    "k_fl_trend  = float(_k_br)  * 1e9\n",
    "rho_fl_trend = float(_rho_br) * 1e3\n",
    "mean_vwcl   = float(sub['VWCL'].median())\n",
    "mean_phi_c  = float(np.mean(list(phi_c_dict.values())))\n",
    "\n",
    "# ── Cement trend lines at varying f_cement ────────────────────────────────────\n",
    "F_CEMENT_VALS = [0.0, 0.02, 0.05, 0.10]\n",
    "trend_colors  = ['#2E86C1', '#27AE60', '#E67E22', '#C0392B']\n",
    "\n",
    "fig, ax = plt.subplots(figsize=(9, 7))\n",
    "fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.10)\n",
    "\n",
    "# Measured data coloured by formation\n",
    "meas_mask = sub['VP_OK'].notna() & sub['VS'].notna()\n",
    "for fname in [n for n,_ in top_list]:\n",
    "    fd = sub[meas_mask & (sub['FORMATION'] == fname)]\n",
    "    if len(fd) == 0: continue\n",
    "    ax.scatter(fd['VP_OK'], fd['VS'], s=3, alpha=0.4,\n",
    "               color=FORM_COLORS.get(fname,'#888'), rasterized=True, label=fname)\n",
    "\n",
    "# Cement model trend lines\n",
    "for f_cem, col in zip(F_CEMENT_VALS, trend_colors):\n",
    "    try:\n",
    "        out = cemented_sand(clay=mean_vwcl, phi_c=mean_phi_c, f_cement=f_cem,\n",
    "                            k_fl=k_fl_trend, rho_fl=rho_fl_trend)\n",
    "        phi_tr, vp_tr, vs_tr = out[0], out[1], out[2]\n",
    "        ax.plot(vp_tr, vs_tr, color=col, lw=1.8, zorder=5,\n",
    "                label=f'Cement f={f_cem:.2f}')\n",
    "    except Exception as e:\n",
    "        print(f'cemented_sand f={f_cem} failed: {e}')\n",
    "\n",
    "# Soft-sediments (uncemented) lower bound\n",
    "try:\n",
    "    out_ss = soft_sediments(clay=mean_vwcl, pressure=med_P*1e6,\n",
    "                             phi_c=mean_phi_c, coord=CN,\n",
    "                             k_fl=k_fl_trend, rho_fl=rho_fl_trend)\n",
    "    ax.plot(out_ss[4], out_ss[5], color='#888', lw=1.2, ls='--',\n",
    "            zorder=4, label='Soft sediment (HM+HS)')\n",
    "except Exception as e:\n",
    "    print(f'soft_sediments failed: {e}')\n",
    "\n",
    "ax.set_xlim(1200, 5500); ax.set_ylim(400, 3200)\n",
    "ax.set_xlabel('Vp (m/s)', fontsize=10)\n",
    "ax.set_ylabel('Vs (m/s)', fontsize=10)\n",
    "ax.legend(fontsize=7.5, loc='upper left', framealpha=0.85)\n",
    "ax.grid(True, alpha=0.2)\n",
    "ax.set_title(f'{WELL_NAME} — Vp–Vs crossplot with cement model trends\\n'\n",
    "             f'(clay={mean_vwcl:.2f}, φ_c={mean_phi_c:.3f}, Cn={CN})',\n",
    "             fontsize=9, fontweight='bold')\n",
    "plt.show()\n"
]))

Path('notebooks/09_rock_physics.ipynb').write_text(json.dumps(nb, indent=1))
print("Appended Vp-Vs crossplot cells")
```

- [ ] **Step 2: Run cell-13 and verify** — scatter data appears with formation colours; four trend lines overlay in blue/green/orange/red from stiff to soft; soft-sediments dashed line below data. If `cemented_sand` fails, check `k_fl` units (must be Pa).

---

## Task 8: Vp–φ crossplot with cement trend lines

**Files:**
- Modify: `notebooks/09_rock_physics.ipynb` (append 2 cells)

- [ ] **Step 1: Append markdown + Vp–φ code cell**

```python
import json
from pathlib import Path

nb = json.loads(Path('notebooks/09_rock_physics.ipynb').read_text())

def md(cell_id, src): return {"cell_type":"markdown","id":cell_id,"metadata":{},"source":src}
def code(cell_id, src): return {"cell_type":"code","execution_count":None,"id":cell_id,"metadata":{},"outputs":[],"source":src}

nb["cells"].append(md("cell-14", [
    "## Step 9.7 — Vp–φ Crossplot with Cement Trend Lines\n\n",
    "Measured VP_OK vs PHIT. Cement model Vp–φ curves at the same f_cement values.\n",
    "The `cemented_sand` function returns saturated Vp directly (Gassmann applied internally).\n"
]))

nb["cells"].append(code("cell-15", [
    "fig, ax = plt.subplots(figsize=(9, 6))\n",
    "fig.subplots_adjust(left=0.09, right=0.97, top=0.90, bottom=0.10)\n",
    "\n",
    "# Measured VP_OK vs PHIT coloured by formation\n",
    "meas_phi_mask = sub['VP_OK'].notna() & sub['PHIT'].notna()\n",
    "for fname in [n for n,_ in top_list]:\n",
    "    fd = sub[meas_phi_mask & (sub['FORMATION'] == fname)]\n",
    "    if len(fd) == 0: continue\n",
    "    ax.scatter(fd['PHIT'], fd['VP_OK'], s=3, alpha=0.4,\n",
    "               color=FORM_COLORS.get(fname,'#888'), rasterized=True, label=fname)\n",
    "\n",
    "# Cement Vp–φ trend lines (phi_cem is x-axis, vp_sat is y-axis)\n",
    "for f_cem, col in zip(F_CEMENT_VALS, trend_colors):\n",
    "    try:\n",
    "        out = cemented_sand(clay=mean_vwcl, phi_c=mean_phi_c, f_cement=f_cem,\n",
    "                            k_fl=k_fl_trend, rho_fl=rho_fl_trend)\n",
    "        phi_tr, vp_tr = out[0], out[1]\n",
    "        ax.plot(phi_tr, vp_tr, color=col, lw=1.8, zorder=5,\n",
    "                label=f'Cement f={f_cem:.2f}')\n",
    "    except Exception as e:\n",
    "        print(f'cemented_sand f={f_cem} failed: {e}')\n",
    "\n",
    "# Soft-sediments lower bound\n",
    "try:\n",
    "    out_ss = soft_sediments(clay=mean_vwcl, pressure=med_P*1e6,\n",
    "                             phi_c=mean_phi_c, coord=CN,\n",
    "                             k_fl=k_fl_trend, rho_fl=rho_fl_trend)\n",
    "    ax.plot(out_ss[0], out_ss[4], color='#888', lw=1.2, ls='--',\n",
    "            zorder=4, label='Soft sediment (HM+HS)')\n",
    "except Exception as e:\n",
    "    print(f'soft_sediments failed: {e}')\n",
    "\n",
    "ax.set_xlim(0, 0.45); ax.set_ylim(1200, 5500)\n",
    "ax.set_xlabel('PHIT (vol frac)', fontsize=10)\n",
    "ax.set_ylabel('VP_OK (m/s)', fontsize=10)\n",
    "ax.legend(fontsize=7.5, loc='upper right', framealpha=0.85)\n",
    "ax.grid(True, alpha=0.2)\n",
    "ax.set_title(f'{WELL_NAME} — Vp–φ crossplot with cement model trends\\n'\n",
    "             f'(clay={mean_vwcl:.2f}, brine: T={med_T:.1f}°C P={med_P:.1f} MPa sal={SAL} ppm)',\n",
    "             fontsize=9, fontweight='bold')\n",
    "plt.show()\n"
]))

Path('notebooks/09_rock_physics.ipynb').write_text(json.dumps(nb, indent=1))
print("Appended Vp-phi crossplot cells")
```

- [ ] **Step 2: Run cell-15 and verify** — scatter shows formation clouds; trend lines decrease Vp with increasing φ (as expected for cemented sand). Higher f_cement lines sit above lower f_cement (stiffer at same φ). Soft-sediment dashed line is the lowest (softest) trend.

---

## Task 9: Save output cell

**Files:**
- Modify: `notebooks/09_rock_physics.ipynb` (append 2 cells)

- [ ] **Step 1: Append markdown + save cell**

```python
import json
from pathlib import Path

nb = json.loads(Path('notebooks/09_rock_physics.ipynb').read_text())

def md(cell_id, src): return {"cell_type":"markdown","id":cell_id,"metadata":{},"source":src}
def code(cell_id, src): return {"cell_type":"code","execution_count":None,"id":cell_id,"metadata":{},"outputs":[],"source":src}

nb["cells"].append(md("cell-16", ["## Step 9.8 — Save Output\n"]))

nb["cells"].append(code("cell-17", [
    "out_cols = ['VS_RPM', 'PHI_C_CEMENT', 'K_MIN', 'G_MIN']\n",
    "out_full = sub[out_cols].reindex(df.index)\n",
    "out_full.to_parquet(OUT_FILE)\n",
    "\n",
    "print(f'Saved : {OUT_FILE}')\n",
    "print(f'Columns: {out_cols}')\n",
    "print(f'Rows   : {len(out_full):,}')\n",
    "print()\n",
    "print('VS_RPM statistics:')\n",
    "print(sub['VS_RPM'].describe().round(1).to_string())\n",
    "\n",
    "# ── Phase summary markdown table ──────────────────────────────────────────────\n",
    "print()\n",
    "print('Phase 9 Summary')\n",
    "print('─' * 60)\n",
    "print(f'  Mineral mixing  : VRH (quartz + clay via VWCL)')\n",
    "print(f'  Cement model    : Dvorkin-Nur contact cement (scheme {SCHEME})')\n",
    "print(f'  Coord number Cn : {CN} (fixed)')\n",
    "print(f'  Calibration     : phi_c per formation (min 30 pts)')\n",
    "for fname, phi_c_v in phi_c_dict.items():\n",
    "    print(f'    {fname:<20}: phi_c = {phi_c_v:.3f}')\n",
    "print(f'  VS_RPM valid    : {sub[\"VS_RPM\"].notna().sum():,} samples')\n",
    "print(f'  Output          : {OUT_FILE}')\n"
]))

nb["cells"].append(md("cell-18", [
    "---\n## Phase 9 Summary\n\n",
    "| Item | Value |\n",
    "|------|-------|\n",
    "| Mineral mixing | VRH Hill average, quartz + clay |\n",
    "| Cement model | Dvorkin-Nur contact cement (qsi), scheme 2 |\n",
    "| Calibration parameter | φ_c per formation (scipy minimize_scalar, bounds 0.30–0.50) |\n",
    "| Coordination number | 8.0 (fixed; explore later) |\n",
    "| Fluid (for trend lines) | Batzle-Wang brine (qsi.fluids) at median T/P |\n",
    "| VS_RPM valid | See Step 9.4 output |\n",
    "| Output | `wells/{WELL_NAME}_rockphysics.parquet` |\n\n",
    "**Next**: Notebook `10_` — fluid substitution (Gassmann) using VS_RPM + calibrated φ_c.\n"
]))

Path('notebooks/09_rock_physics.ipynb').write_text(json.dumps(nb, indent=1))
print("Appended save cells")
```

- [ ] **Step 2: Run cell-17 and verify**

Expected:
```
Saved : ../wells/65077-15S_rockphysics.parquet
Columns: ['VS_RPM', 'PHI_C_CEMENT', 'K_MIN', 'G_MIN']
Rows   : 30,119
```
Then confirm the file exists: `ls -lh wells/*_rockphysics.parquet`

---

## Task 10: Full notebook run verification

- [ ] **Step 1: Restart kernel and run all cells**

In Jupyter: Kernel → Restart & Run All. All cells should complete without errors.

- [ ] **Step 2: Verify final cell count and output file**

```bash
python3 -c "
import json
nb = json.load(open('notebooks/09_rock_physics.ipynb'))
print(f'Cells: {len(nb[\"cells\"])}')
import pandas as pd, glob
files = glob.glob('wells/*_rockphysics.parquet')
for f in files:
    df = pd.read_parquet(f)
    print(f'{f}: {len(df):,} rows, cols={list(df.columns)}, VS_RPM valid={df[\"VS_RPM\"].notna().sum():,}')
"
```

Expected:
```
Cells: 19
wells/65077-15S_rockphysics.parquet: 30,119 rows, cols=['VS_RPM', 'PHI_C_CEMENT', 'K_MIN', 'G_MIN'], VS_RPM valid: ~18,000+
```

- [ ] **Step 3: Commit**

```bash
git add notebooks/09_rock_physics.ipynb wells/*_rockphysics.parquet
git commit -m "$(cat <<'EOF'
feat: add 09_rock_physics notebook — Vs modelling via Dvorkin-Nur cement model

Calibrates critical porosity phi_c per formation on measured DTS intervals,
produces VS_RPM log using qsi contact_cement + VRH mineral mixing (VWCL).
Includes Vp-Vs and Vp-phi crossplots with cemented_sand trend lines.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Against Spec

| Spec requirement | Task |
|-----------------|------|
| 9.1 Load LAS for PHIT, VWCL; join parquets; assign FORMATION | Task 2 |
| 9.2 VRH mineral mixing (Hill), K_MIN, G_MIN, RHO_MIN | Task 3 |
| 9.3 Per-formation phi_c calibration on measured VS only | Task 4 |
| 9.4 VS_RPM log; coverage summary | Task 5 |
| 9.5 4-track log display with VS comparison | Task 6 |
| 9.6 Vp-Vs crossplot + cement trend lines + soft sediment bound | Task 7 |
| 9.7 Vp-φ crossplot + cement trend lines | Task 8 |
| 9.8 Save VS_RPM, PHI_C_CEMENT, K_MIN, G_MIN to parquet | Task 9 |
| qsi import, no rockphypy | Tasks 1–9 all use qsi |
| contact_cement [-1]=0 bug fixed via dummy endpoint | Task 4, `cement_vs()` |
| brine units: GPa→Pa, g/cc→kg/m³ | Task 4, Task 7, Task 8 |
