# 09_rock_physics.ipynb — Design Spec

**Date**: 2026-05-02
**Pipeline position**: After 08_elastic_qc (VP_OK, VS_OK produced)
**Goal**: Vs modelling via patchy cement model calibration → VS_RPM log

---

## Context

Notebook 08 synthesises VS_OK using the Castagna mudrock line — a purely empirical Vp–Vs relation with no rock physics basis. This notebook replaces that with the **Dvorkin-Nur contact cement model** (`qsi.models.cement.contact_cement`), which honours the physics of grain cementation, coordination number, and mineralogy. The result is a VS_RPM log calibrated per formation and a set of calibrated `phi_c` values that can seed fluid substitution later.

**Library**: `qsi` project at `/Users/abd/Developer/qsi` — no new dependencies needed.

---

## Key qsi API Calls

| Function | Module | Used for |
|----------|--------|----------|
| `contact_cement(phi, phi_c, coord, g_grain, k_grain, g_cement, k_cement, k_fluid)` | `qsi.models.cement` | Per-sample K_sat + G_frame; Vs = √(G_frame/ρ) |
| `cemented_sand(clay, feldspar, calcite, phi_c, f_cement, k_fl, rho_fl)` | `qsi.models.cemented_sand` | Generate trend lines (Vp,Vs) vs φ at varying f_cement |
| `soft_sediments(clay, ..., pressure, phi_c, coord, k_fl, rho_fl)` | `qsi.models.soft_sediments` | Uncemented (HM + lower HS) reference trend |
| `voigt_reuss_hill(fractions, bulk_moduli, shear_moduli)` | `qsi.moduli.bounds` | VRH mineral mixing using VWCL |
| `brine_properties(sal, P, T)` | `qsi.fluids.batzle_wang` | Brine K_fl, ρ_fl for Vp–φ crossplot forward model |
| `gassmann_sat(k_dry, g_dry, phi, k_fl, rho_fl, k0, rho_ma)` | `qsi.moduli.gassmann` | Dry → saturated for Vp in Vp–φ crossplot |

**Import pattern** (same as petro-rock's own well_config pattern):
```python
import sys; sys.path.insert(0, '/Users/abd/Developer/qsi')
from qsi.models.cement import contact_cement
from qsi.models.cemented_sand import cemented_sand
from qsi.models.soft_sediments import soft_sediments
from qsi.moduli.bounds import voigt_reuss_hill
from qsi.moduli.gassmann import gassmann_sat
from qsi.fluids.batzle_wang import brine_properties
```

### How `contact_cement` works (critical for calibration)

Cement fraction `alpha = phi_c − phi` is computed **internally** — there is no separate `f` argument.  
The two calibration handles are:
- **`phi_c`** — critical porosity (shifts the whole trend; primary calibration target)
- **`coord`** (Cn) — coordination number (scales stiffness; deferred to later exploration)

`G_frame` is the **dry** shear modulus → `Vs = sqrt(G_frame / rho_sat)` needs no fluid properties (Gassmann: G_sat = G_dry).

---

## Input Data

| Source | File | Columns used |
|--------|------|-------------|
| LAS file | `cfg['las_file']` | PHIT, VWCL (not yet in any parquet) |
| Elastic QC | `{WELL}_elastic.parquet` | VP_OK, VS, VPVS, ELASTIC_EDIT |
| Density editing | `{WELL}_rhob_ok.parquet` | RHOB_OK |
| T/P | `{WELL}_computed.parquet` | DIFF_PRESS, TEMP |
| Faust | `{WELL}_faust.parquet` | VP_SOURCE |
| Tops | `cfg['tops_file']` | Formation boundaries |

---

## Steps

### 9.1 — Setup & Data Load
- `sys.path.insert` for qsi; import all functions listed above
- Load all parquets and join to main dataframe indexed on DEPTH_MD
- Load LAS, apply `curve_map`, extract PHIT and VWCL
- Assign FORMATION from TOPS_MD (same depth-bound loop as earlier notebooks)
- Config block — mineral constants (Pa, kg/m³):
  ```
  Quartz : K=36.6e9, G=45.0e9, ρ=2650
  Clay   : K=25.0e9, G=9.0e9,  ρ=2580
  Cement : K=36.6e9, G=45.0e9  (quartz cement — Garn sandstone)
  ```
- Config block — cement model defaults:
  ```
  phi_c_global = 0.40   # initial; calibrated per formation
  Cn_global    = 8.0    # fixed for now; explore later
  scheme       = 2      # uniform cement on grain surface
  ```

### 9.2 — VRH Mineral Mixing
- Call `voigt_reuss_hill([VWCL, 1-VWCL], [K_clay, K_qtz], [G_clay, G_qtz])` per sample
- Extract K_min (Hill), G_min (Hill); ρ_min = VWCL·ρ_clay + (1−VWCL)·ρ_qtz
- Print range stats; scatter K_min vs VWCL coloured by formation to verify

### 9.3 — Per-Formation Calibration of phi_c
- **Calibration mask** per formation:
  `VS.notna()` (raw DTS — unambiguously measured)
  AND `VP_SOURCE == 0` (measured Vp, not Faust)
  AND `ELASTIC_EDIT == 0`
  AND `PHIT.notna()` AND `RHOB_OK.notna()` AND `DIFF_PRESS.notna()`
- For each sample in calibration set:
  ```python
  k_sat, G_frame = contact_cement(
      phi=[PHIT], phi_c=phi_c_trial, coord=Cn,
      g_grain=G_min, k_grain=K_min,
      g_cement=G_cem, k_cement=K_cem,
      k_fluid=k_brine_scalar, scheme=2)
  VS_pred = sqrt(G_frame / (RHOB_OK * 1000))
  ```
  (Use a representative median brine K for calibration; precise per-sample brine in Step 9.4)
- Per formation: `scipy.optimize.minimize_scalar(rms_fn, bounds=(0.30, 0.50), method='bounded')`  
  → find `phi_c` that minimises RMS(VS_pred − VS_meas)
- Output table: Formation | n_cal | phi_c | Cn | RMS_Vs (m/s) | RMS_Vs% | Mean_VS
- Fall back to `phi_c_global` for formations with < 30 calibration points

### 9.4 — Apply Model: VS_RPM Log
- Apply per-formation calibrated `phi_c` to all samples where PHIT and RHOB_OK are valid
- Use per-sample `DIFF_PRESS` for σ_eff — passed through `hertz_mindlin` internally in `contact_cement`
  (Note: `contact_cement` in qsi does not take pressure directly; effective pressure enters via grain moduli VRH. Keep `Cn` as fixed scalar for now.)
- Output column: `VS_RPM` (m/s)
- Print coverage: n samples with VS_RPM, VS_OK (measured), VS_OK (Castagna)

### 9.5 — Log Display: VS comparison
- 3-track log (same style as prior notebooks), shared y-axis (depth MD), inverted:
  - **Track 1**: GR + formation tops
  - **Track 2**: RHOB_OK
  - **Track 3**: VP_OK (black), VS (measured, dark blue), VS_RPM (red), VS_CASTAGNA from 08 (dashed grey)
- Formation tops overlaid on all tracks

### 9.6 — Vp–Vs Crossplot with Cement Trend Lines
- Scatter: measured (VP_OK, VS) coloured by formation (FORM_COLORS)
- Overlay `cemented_sand(clay=mean_VWCL, f_cement=f, k_fl=k_brine, rho_fl=rho_brine)` trend lines at:
  - f_cement = 0.0, 0.02, 0.05, 0.10 — labelled on the curves
- Overlay `soft_sediments(...)` as the uncemented lower bound (dashed)
- Mark the calibrated phi_c per formation as a labelled point on its best-fit trend

### 9.7 — Vp–φ (PHIT) Crossplot with Cement Trend Lines
- Scatter: measured (VP_OK, PHIT) coloured by formation
- Overlay `cemented_sand(f_cement=f, ...)` Vp–φ curves at same f_cement values
- Overlay `soft_sediments(...)` uncemented lower bound
- Use `brine_properties(sal=cfg['salinity_ppm'], P=median_DIFF_PRESS, T=median_TEMP)` for
  `k_fl, rho_fl` in `cemented_sand`; also run `gassmann_sat` for the dry trend overlay

### 9.8 — Save
- Output: `{WELL_NAME}_rockphysics.parquet`
  - `VS_RPM` — cement-model Vs (m/s)
  - `PHI_C_CEMENT` — calibrated phi_c used per sample
  - `K_MIN` — VRH mineral bulk modulus (Pa)
  - `G_MIN` — VRH mineral shear modulus (Pa)

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Library | qsi (not rockphypy) | Already available, purpose-built, user-maintained |
| Calibration target | `phi_c` per formation | Only free parameter in `contact_cement`; Cn deferred |
| Vs from model | `sqrt(G_frame / rho_sat)` | G_sat = G_dry — no fluid properties needed |
| Fluid for Vp–φ crossplot | Batzle-Wang brine via `qsi.fluids.batzle_wang` | Needed for K_sat in Vp forward model |
| Cement mineral | Quartz (K=36.6, G=45 GPa) | Garn Jurassic sandstone reservoir |
| Cn | Fixed at 8.0 globally | Tune phi_c first; explore Cn later |
| Calibration domain | `VS.notna()` raw DTS + no edits | Measured Vs only — no Castagna-predicted samples |
