# Log Conditioning & Rock Physics Preparation Workflow

A general-purpose, step-by-step guide for conditioning wireline log data before rock physics analysis.

---

## Overview

This workflow takes raw wireline log data (LAS / DLIS files) through a structured sequence of QC, editing, and modelling steps to produce a clean set of elastic and petrophysical logs. The output is a well dataset ready for rock physics template construction, RPM calibration, fluid substitution, and seismic-to-well tie.

The 12 phases are ordered so that each step depends only on outputs from earlier steps. Do not skip or reorder phases — a depth shift error in Phase 4, for example, will corrupt every crossplot in Phase 10.

---

## Curve Flow Summary

Input and output curves for each phase. Curves produced in one phase become inputs to later phases — key dependencies are noted below the table.

| Phase | Input curves | Output curves |
|-------|-------------|---------------|
| **1. Data Inventory** | *(all raw LAS/DLIS curves — inventory only)* | Standardised mnemonics loaded |
| **2. T/P Loading** | BHT values, RHOB (overburden integration), RT (Rw derivation), RFT pressure points | TEMP, PORE\_PRESS, DIFF\_PRESS |
| **3. Caliper QC** | CALI, bit size (header) | BAD\_HOLE\_FLAG |
| **4. Depth Shift** | DT, RHOB | DT\_OK (depth-shifted DT) |
| **5. Petrophysics Review** | GR, CALI, RT, MSFL, NPHI, RHOB, PE, DT, VWCL, PHIT, PHIE, SW | Reviewed/updated VWCL, PHIT, PHIE, SW |
| **6. Density Editing** | RHOB, DRHO, CALI, BAD\_HOLE\_FLAG, COAL\_FLAG, CALCFLG, NPHI, DT\_OK | RHOB\_OK |
| **7. Elastic QC** | DT\_OK, DTS, RHOB\_OK, BAD\_HOLE\_FLAG, COAL\_FLAG, CALCFLG | VP (from DT\_OK), VS (from DTS) — QC'd |
| **8. Faust Vp** | RT, DT\_OK (calibration), DIFF\_PRESS, BAD\_HOLE\_FLAG, depth (Z) | VP\_COMP, VP\_SOURCE (splice indicator) |
| **9. Well Correlation** | GR, RT, formation tops | No new curves — stratigraphic framework only |
| **10. Crossplot Analysis** | VP\_COMP, RHOB\_OK, VS, VWCL, PHIT, SW, COAL\_FLAG, CALCFLG, BAD\_HOLE\_FLAG | No new curves — diagnostic and QC only |
| **11. RPM Calibration** | VP\_COMP, RHOB\_OK, VS (calibration well), PHIT, VWCL, DIFF\_PRESS, TEMP | VS\_MOD |
| **12. Fluid Substitution** | RHOB\_OK, VP\_COMP, VS\_MOD (or VS), PHIT, VWCL, SW, TEMP, PORE\_PRESS, DIFF\_PRESS | VPBRINE, VSBRINE, RHOBRINE, VPGAS, VSGAS, RHOGAS |

**Key dependencies:**
- BAD\_HOLE\_FLAG (Phase 3) is consumed by Phases 6, 7, 8, 10, 11
- DT\_OK (Phase 4) flows into every subsequent elastic phase
- RHOB\_OK (Phase 6) flows into every subsequent elastic phase
- VP\_COMP (Phase 8) is the Vp used from Phase 10 onwards — never raw DT
- VS\_MOD (Phase 11) is the only source of Vs for wells without DTS, and is required for Phase 12

---

## PHASE 1: DATA INVENTORY & PROJECT SETUP

### Step 1.1 — Compile Well Information Table

Before loading any data, build a header table for every well in the study. Record:

- Well name, UWI/API number, operator
- Spud date and total depth (MD, TVDkb, TVDss)
- Kelly Bushing (KB) elevation above mean sea level
- Water depth (offshore) or ground elevation (onshore)
- Borehole diameter (nominal bit size — needed for caliper QC)
- Drilling fluid type and weight (affects some log responses)
- Primary target formation(s)
- Any known data quality issues (lost circulation zones, tight hole sections)

**Why this matters**: KB elevation is essential for TVD conversions. Bit size sets the reference for caliper washout assessment. Drilling fluid type affects neutron and density log corrections.

Flag wells drilled before approximately 1990 — older wells often lack shear sonic (DTS) and photoelectric factor (PE) logs. These gaps must be planned for before the project begins.

### Step 1.2 — Log Suite Inventory Matrix

Build a matrix with one row per well and one column per log type. Mark each cell: Present / Absent / Partial (present over part of the interval only).

Minimum log suite for rock physics work:

**Petrophysical logs** (usually delivered from a CPI):
- VWCL or VCL — clay/wet clay volume (fraction)
- VSHALE or VSH — shale volume (fraction)
- PHIT — total porosity (fraction)
- PHIE — effective porosity (fraction)
- SW or SWT — water saturation (fraction)

**Editing and exclusion flags**:
- Coal flag — marks coal seams
- Calcite / cemented layer flag — marks carbonate-cemented intervals
- Any additional lithology flags from petrophysics (e.g., tuff flag, anhydrite flag)

**Elastic logs** (primary deliverables for rock physics):
- DT — compressional slowness (μs/ft or μs/m); present in virtually all wells
- DTS — shear slowness; absent in most wells drilled before ~1990
- RHOB — bulk density (g/cc)
- DRHO — density correction log (g/cc); present when a litho-density tool was run

**Raw input logs** (needed for editing and modelling):
- CALI — borehole caliper (inches or mm)
- GR — gamma ray (API units)
- NPHI — neutron porosity (fraction, limestone units)
- RT / LLD / ILD — deep resistivity (Ω·m)
- MSFL / SFLU / RXO — shallow resistivity (Ω·m)
- PE — photoelectric factor (barns/electron)
- TEMP — downhole temperature (°C or °F); may need to be computed

**Derived logs to be created during this workflow**:
- RHOB_OK — edited density
- VP_COMP — composite compressional velocity (measured + modelled)
- VS_MOD — modelled shear velocity from RPM
- TEMP — formation temperature (if not supplied)
- PORE_PRESS, DIFF_PRESS — pressure logs

### Step 1.3 — Mnemonic Standardisation

Different service companies and vintages use different mnemonics for the same measurement (e.g., DT, DTCO, DTC, AC all refer to compressional slowness). Before loading:

1. Identify the canonical mnemonic for each log type within the project
2. Rename all input curves to the project standard on load
3. Record the original mnemonic and service company in the well header or a lookup table
4. Check units at load — confirm DT is in μs/ft (or convert), RHOB in g/cc, GR in API, depths in metres MD

### Step 1.4 — Define Working Depth Intervals

Load or define formation tops for each well. The working intervals should span the zone of interest plus buffer above and below. Group tops into the stratigraphic intervals that will be used as colour/filter groups in all subsequent crossplots.

---

## PHASE 2: TEMPERATURE & PRESSURE (T/P) LOADING

### Step 2.1 — Temperature Gradient Derivation

Formation temperature is needed for:
- Correcting formation water resistivity (Rw) for use in saturation equations
- Fluid property calculations (Batzle-Wang)
- Pressure computation in combination with density integration

**Why BHT measurements are unreliable raw**

Wireline tools are run shortly after the borehole has been circulated with drilling mud. The circulating mud is cooler than formation temperature, so the borehole has not fully re-equilibrated. Raw BHT values can be 10–30°C too low, especially in deep wells and when circulation time was long.

**Horner correction procedure**

For each BHT measurement, the Horner method uses the following equation:

```
T_corrected = T_static + (T_static - BHT) × log[(t_circ + Δt) / Δt]
                                             ─────────────────────────
                                             (Horner time ratio term)
```

Where:
- `T_static` = estimated true formation temperature (unknown — iterated to find)
- `BHT` = measured bottom-hole temperature at time Δt after circulation stopped
- `t_circ` = total circulation time before the survey (hours)
- `Δt` = time since last circulation stopped (hours)

In practice:
1. Collect all BHT values from all wireline runs in the well (multiple runs give multiple points)
2. For each run, compute the Horner time ratio: `log[(t_circ + Δt) / Δt]`
3. Plot BHT (y-axis) vs the Horner time ratio (x-axis), with time ratio decreasing to the right (towards infinite shut-in at x=0)
4. Fit a straight line through the points
5. Extrapolate to x = 0 (infinite shut-in); the y-intercept is the corrected static formation temperature

If only one BHT run is available per well, use an industry correction chart (e.g., AAPG BHT correction chart based on well depth and time after circulation) as a fallback.

**Building the geothermal gradient**

1. Plot corrected T vs depth TVDss for all wells together
2. Fit a linear regression: `T[°C] = T_surface + G × depth[m]`
   - `T_surface` is the mean annual surface (or seabed) temperature
   - `G` is the geothermal gradient in °C/m (typical range: 0.025–0.045°C/m for NW Europe)
3. Load this linear function as a temperature log in each well

If there is evidence of lateral variation in heat flow (e.g., igneous intrusions, major faults), a well-specific gradient may be preferable to a field-wide average.

### Step 2.2 — Formation Water Resistivity (Rw)

Rw is required for Archie-based saturation calculations and for Pickett plot construction.

**Determining salinity**

Preferred sources in order of reliability:
1. Produced water chemical analyses (NaCl equivalent concentration in ppm or mg/L)
2. Formation water database for the basin / formation
3. Pickett plot back-calculation (see Phase 10)

**Converting salinity to Rw**

At a reference temperature T_ref (typically 25°C or 75°F):

```
Rw[T_ref] = (3.647 × 10^4 / salinity[ppm])^1.14   [Ω·m, approximate Arps formula]
```

At formation temperature T [°C]:

```
Rw[T] = Rw[25°C] × (25 + 21.5) / (T + 21.5)      [Ω·m, Wright-Welex approximation]
```

Load Rw as a depth-varying log by applying the temperature log from Step 2.1.

**Sanity check**: plot Rw vs depth. It should decrease monotonically with depth (increasing temperature). Any step or reversal suggests an error in the temperature gradient.

### Step 2.3 — Pressure Loading

Pressure logs are required for:
- Stress-sensitive rock physics models (Phase 11)
- Fluid substitution calculations (Phase 12)
- Identifying overpressured intervals

**Overburden (lithostatic) pressure**

Integrate bulk density from surface:

```
P_OB[MPa] = ∫ ρ_b(z) × g × dz
```

Where ρ_b is bulk density in kg/m³, g = 9.81 m/s², and the integral runs from surface to depth z. In the absence of a density log to surface, use a water-filled column from mudline to seabed and a basin-typical density function (e.g., Gardner-based) from seabed to first log reading.

As a rule of thumb, lithostatic gradient is approximately 1.0 psi/ft (22.6 kPa/m) in most sedimentary basins.

**Hydrostatic (pore) pressure**

In normally pressured reservoirs:
```
P_hydro[MPa] = ρ_water × g × z
```
Typical gradient: 0.433–0.450 psi/ft (9.8–10.2 kPa/m) depending on water salinity.

**Direct pressure measurements (RFT / MDT)**

Where drill-stem tests (DST) or formation tester measurements (RFT/MDT) are available:
1. Digitise the pressure vs depth table from the well completion report
2. Load as a discrete depth-indexed log or as top/base interval constants
3. These override the hydrostatic assumption in tested intervals and are the most reliable source for reservoir pore pressure

**Differential (effective) pressure**

```
P_diff = P_overburden − P_pore
```

This is the key input to stress-sensitive rock physics models. Load as a computed log.

---

## PHASE 3: HOLE CONDITION QC — CALIPER ANALYSIS

### Step 3.1 — Understanding the Caliper Log

The caliper tool measures borehole diameter. It is the primary indicator of log data reliability:
- **In-gauge borehole**: diameter close to the nominal bit size. All log measurements are reliable.
- **Washout (enlarged)**: diameter significantly larger than bit. The tool is not pressed against the formation; density and neutron responses are severely affected. Sonic may also be affected.
- **Tight hole / squeeze**: diameter smaller than bit. Indicates swelling clays or incomplete drilling. Rare.

Types of caliper tool:
- **1-arm caliper** (pad-type): measures in one direction only; misses elliptical boreholes
- **2-arm caliper**: measures two orthogonal diameters; provides borehole shape
- **4-arm caliper** (often part of a dipmeter): measures two independent diameters and tool orientation; most informative

When two caliper readings are available (C1 and C2), use the larger of the two for washout assessment.

### Step 3.2 — Washout Detection Criteria

Define washout using the following thresholds, applied per well based on the nominal bit size (BS):

| Condition | Criterion | Action |
|-----------|-----------|--------|
| Good hole | CALI ≤ BS + 10% | Use all logs |
| Marginal hole | BS + 10% < CALI ≤ BS + 25% | Use with caution; inspect DRHO |
| Washout | CALI > BS + 25% | Density and neutron unreliable |
| Severe washout | CALI > 1.5 × BS | All pad-contact tools unreliable |

For example, with a 12.25-inch bit:
- Good hole: CALI ≤ 13.5 inches
- Marginal: 13.5 < CALI ≤ 15.3 inches
- Washout: CALI > 15.3 inches

Adjust thresholds based on local experience. Some operators use an absolute threshold (e.g., flag any CALI > 14 inches) rather than a percentage.

### Step 3.3 — Creating the Borehole Quality Flag

Compute a BAD_HOLE_FLAG log (1 = bad, 0 = good):

```
BAD_HOLE_FLAG = 1  if CALI > BS × 1.25  (or locally-calibrated threshold)
BAD_HOLE_FLAG = 0  otherwise
```

Additional conditions to force BAD_HOLE_FLAG = 1:
- Where |DRHO| > 0.15 g/cc (see Phase 6) regardless of caliper
- Any manually identified bad intervals noted in the log heading remarks

This flag will be used to:
- Exclude intervals from density editing decisions
- Mask data in all elastic crossplots
- Exclude intervals from Faust Vp calibration
- Exclude intervals from RPM calibration

**Practical note**: caliper tools frequently have spikes at casing shoes, tool junctions, and zones of stuck pipe. Inspect the log visually and remove obvious artefacts before computing the flag.

---

## PHASE 4: DEPTH SHIFTING — SONIC TO DENSITY ALIGNMENT

### Step 4.1 — Why Depth Shifts Occur

Modern LWD (logging-while-drilling) tools acquire measurements close to the drill bit and at nearly the same depth. Wireline tools, by contrast, are run as a string: the density pad sits at one position on the string, the sonic transmitter/receivers at another, typically separated by several metres. When the tool string is pulled up the hole, each sensor samples a given formation depth at a slightly different cable depth reading.

In addition:
- Cable stretch varies with tension and hole deviation
- Depth counters may reset or slip between runs
- Certain tools are recorded on separate passes (e.g., density on one run, sonic on another)

The result is a systematic depth offset between DT and RHOB that, if uncorrected, causes artificial scatter on Vp–density crossplots — the most important diagnostic plot in rock physics.

### Step 4.2 — Identifying the Required Shift

The diagnostic tool is the **RHOB vs DT crossplot**:

1. Select a QC window: use a long, geologically homogeneous interval with good hole condition (caliper in gauge). Avoid intervals with gas, hydrocarbons, or highly variable lithology.
2. Generate the RHOB vs DT crossplot and observe the scatter pattern.
3. If the logs are well-aligned, the points will cluster tightly around the expected formation trend.
4. If the logs are misaligned by even 0.5 m, you will see the cloud of points smeared along the trend — the scatter is characteristically elongated in the direction of the trend, because the tool is reading the density of the layer above (or below) while the sonic reads the current layer.

**Shift direction diagnostic**:
- If DT needs to be shifted upward (DT reads too deep), the sonic is seeing the same layer later than the density. The crossplot scatter will show a "leading edge" on the right-hand side (slow, low-density points that should not exist for that lithology).
- If DT needs to be shifted downward, the opposite pattern occurs.

In practice, it is easier to use software that computes a cross-correlation or a statistical measure of scatter as a function of trial shift, and then selects the optimal shift automatically.

### Step 4.3 — Applying and Validating the Shift

1. Apply the depth shift to the DT log only (DT is conventionally shifted to match RHOB, which is considered the depth reference for the tool string).
2. Regenerate the RHOB vs DT crossplot and confirm scatter has reduced.
3. Also compare the log tracks visually: after the shift, thinly-bedded sand/shale sequences should show DT and RHOB peaks/troughs at the same depths.
4. Record the applied shift (sign and magnitude) in the well header for documentation.

**Typical magnitudes**: ±0.5–3.0 m. Larger shifts (>3 m) are possible if sonic and density were on separate wireline runs.

**Important**: apply the shift before any editing or modelling steps that use both DT and RHOB simultaneously.

---

## PHASE 5: PETROPHYSICAL LOG REVIEW & CPI EVALUATION

### Step 5.1 — Standard Composite Log Display

Build a composite log display per well. The track layout below is a common convention:

| Track | Curves | Scale |
|-------|--------|-------|
| 1 | GR | 0–150 API |
| 1 | CALI, Bit Size | 6–16 inches |
| 2 | RT (deep resistivity) | 0.2–2000 Ω·m (log scale) |
| 2 | MSFL / RXO (shallow) | 0.2–2000 Ω·m (log scale) |
| 3 | NPHI | 0.45–−0.15 (reversed, limestone units) |
| 3 | RHOB | 1.95–2.95 g/cc |
| 3 | PE | 0–10 barns/electron (if available) |
| 4 | DT (sonic) | 140–40 μs/ft (reversed) |
| 5 | VWCL or VSHALE | 0–1 fraction |
| 6 | PHIT, PHIE | 0.4–0 fraction (reversed) |
| 7 | SW / SWT | 1–0 (reversed, so hydrocarbon is right-filling) |
| 7 | Flags | Coloured fills |

Note the reversal conventions: DT reversed so faster rock (smaller number) plots to the right, matching the behaviour of higher-velocity formations. Porosity reversed so reservoir stands out.

Visual checks on this display:
- GR should increase in shales and decrease in clean sands/carbonates
- RHOB and NPHI should show crossover in gas zones (density reads lower, neutron reads higher relative to brine)
- RT should increase dramatically in hydrocarbon-bearing intervals at reservoir porosity
- VWCL should track GR; sharp departures suggest the clay model needs reviewing
- PHIT and PHIE should converge in clean sand (little clay-bound water) and diverge in shales

### Step 5.2 — NPHI–RHOB Lithology Crossplot

Plot NPHI (x-axis, limestone units) vs RHOB (y-axis) for each well. The standard mineral lines plot as follows:

```
          RHOB (g/cc)
   2.0 ─────────────────────────────────
       │        Coal (~1.3)
   2.2 ─         ·
       │
   2.4 ─                   Sandstone
       │            Limestone  ·  · ·
   2.6 ─                  ·       Dolomite
       │         Shale band
   2.8 ─     · · ·
       │
   3.0 ─                              Anhydrite
       └─────────────────────────────────────────
       0.45  0.35  0.25  0.15  0.05  -0.05  -0.15
                    NPHI (fraction)
```

Key identifications:
- **Clean sandstone**: plots along the sandstone line (NPHI ~0.02–0.08, RHOB ~2.62–2.65 at zero porosity)
- **Shale**: plots above and to the right of sandstone — high NPHI (bound water), elevated RHOB
- **Coal**: very low density (1.2–1.5 g/cc), high neutron response — isolated cluster at bottom-left
- **Carbonate cement / calcite**: low NPHI, high RHOB — plots toward the limestone/dolomite lines
- **Gas effect**: density moves left (lower) and neutron moves right (lower), so the crossplot point moves up and left relative to the brine-filled position — the "gas crossover" on log display translates to a leftward shift on this crossplot

### Step 5.3 — Pickett Plot (PHIT vs RT)

The Pickett plot is the standard saturation QC tool. It is a log–log plot of deep resistivity (RT, x-axis) vs total porosity (PHIT, y-axis).

Archie's equation in log form:

```
log(RT) = log(a × Rw) + n × log(Sw) − m × log(PHIT)
```

For 100% brine-saturated rock (Sw = 1):
```
log(RT) = log(a × Rw) − m × log(PHIT)
```

This is a straight line on the Pickett plot with:
- Slope = −m (cementation exponent, typically 1.8–2.1 for clean consolidated sands; 1.5–1.8 for unconsolidated)
- Intercept at PHIT = 1.0 gives RT = a × Rw

**How to use the Pickett plot**:

1. Plot all data points from a given interval coloured by depth or formation
2. Identify the cluster of "wet" (brine-saturated) points — these define the Archie trend line
3. Fit the Archie line through the wet points
4. The y-intercept at PHIT = 1.0 should equal a × Rw; with a ≈ 1 for intergranular porosity, this gives an independent estimate of Rw
5. Points plotting to the right of the brine line (higher RT for the same porosity) are hydrocarbon-bearing; their horizontal displacement from the line is proportional to log(Sw)
6. Construct Sw = 0.5 and Sw = 0.25 lines parallel to the brine line, shifted right by log(0.5^−n) and log(0.25^−n) respectively, to estimate saturation contours

**Using the Pickett plot to back-calculate Rw**:
If salinity data is unavailable, fit the Archie line to the wet points and read off the intercept. Compare to expected values from the basin water salinity database.

### Step 5.4 — CPI Review: Clay Volume (VWCL / VSHALE)

Clay volume is the most consequential petrophysical output for rock physics because:
- It controls PHIE (PHIE = PHIT − clay-bound water fraction)
- It appears directly in rock physics mixing models as a mineral end-member
- Overestimated clay leads to underestimated PHIE, which shifts sand points on Rho–Vp crossplots to incorrect positions

Check the clay volume model used in the CPI:
- **Linear GR (Larionov)**: simple but often overestimates clay in radioactive sands
- **Clavier**: uses a non-linear GR transform; typically gives lower clay than linear GR
- **NPHI–RHOB combination**: more lithology-independent, better in complex mineralogy
- **Dual clay model (VWCL vs VSHALE)**: distinguishes dispersed clay (in pore space) from laminated clay (thin shale beds); better for laminated reservoirs

To QC the clay volume:
1. Compare VWCL to GR — they should track each other; large departures suggest radioactive non-shale (tuff, K-feldspar) or non-radioactive shale
2. Check VWCL in known clean reservoir intervals (confirmed by core or test) — should approach zero
3. Check VWCL in adjacent shale packages — should approach 1.0
4. Verify that PHIE goes to near-zero in shale (not negative, which would indicate overcorrection)

### Step 5.5 — Hydrocarbon Interval Documentation

For each well, record:
- GOC, GWC, or OWC depth (TVDkb and TVDss)
- Fluid type (gas, condensate, oil, mixed)
- Key fluid properties from well test reports or PVT analysis:
  - Gas: gravity (specific gravity relative to air), H₂S and CO₂ content
  - Oil: API gravity, GOR (SCF/STB or sm³/sm³), formation volume factor (Bo)
  - Condensate: API gravity (typically >45°), GOR, gas gravity

These values feed into Batzle-Wang fluid property calculations in Phase 12.

---

## PHASE 6: DENSITY LOG EDITING

### Step 6.1 — The DRHO Log and What It Measures

The litho-density tool uses two gamma-ray detectors at different distances from the source (a short-spacing "compensation" detector and a long-spacing "measurement" detector). The DRHO (Δρ) curve represents the correction applied by the tool's spine-and-ribs algorithm to compensate for borehole rugosity effects.

**Physical interpretation**:
- When the density pad is pressed firmly against smooth formation, both detectors measure consistently → DRHO is small (< 0.05 g/cc in absolute value)
- When the pad bridges across a rough or washed-out section, the two detectors see different amounts of borehole fluid → DRHO becomes large

**The spine-and-ribs correction works up to a point**. Beyond a certain level of hole rugosity, the compensation algorithm saturates and the reported RHOB is unreliable even after the DRHO correction. The threshold is approximately:

| |DRHO| range | Interpretation | Action |
|------------|-------------|--------|
| < 0.05 g/cc | Excellent hole condition | Accept RHOB |
| 0.05–0.10 g/cc | Good; minor correction applied | Accept RHOB |
| 0.10–0.15 g/cc | Marginal; larger correction | Accept with caution; inspect caliper |
| 0.15–0.20 g/cc | Poor hole | Flag for replacement |
| > 0.20 g/cc | Severe — algorithm is saturated | Replace RHOB |

**Important caveat — gas zones**: In gas-bearing intervals, the density correction may legitimately be larger than in brine-saturated rock even with a smooth borehole, because low-density gas near the borehole wall creates an apparent "negative" borehole effect. Be careful not to flag gas-bearing sands as bad-hole solely on the basis of DRHO — cross-check with caliper.

**Decision rule for density editing**:

```
IF |DRHO| > 0.15 g/cc  AND  CALI > BS × 1.15:
    → Flag for replacement (washout + large correction)

IF |DRHO| > 0.15 g/cc  AND  CALI ≤ BS × 1.15:
    → Inspect; likely gas or rugose microstructure; do not automatically replace

IF |DRHO| ≤ 0.15 g/cc  AND  CALI > BS × 1.25:
    → Inspect; possible pad bridging; RHOB may still be unreliable
```

### Step 6.2 — Applying Lithology Flags Before Editing

Load all lithology flags before making any editing decisions. These define intervals where the density log reading is physically correct but the lithology is atypical for the elastic analysis:

**Coal (COAL_FLAG)**:
- True formation density: ~1.2–1.5 g/cc (much lighter than siliciclastic rock)
- The density reading is correct — coal really is that light
- Do NOT replace coal density
- Do mask coal in all rock physics crossplots (coal is not part of the sand–shale elastic trend)
- Vp in coal is also anomalously slow (~1.5–2.5 km/s) and Vs is low, giving Vp/Vs ≈ 2.0

**Carbonate cement / calcite layers (CALCFLG / CEMENTED_LAYER_FLAG)**:
- Calcite density: ~2.71 g/cc; dolomite: ~2.85 g/cc
- High-density spikes in an otherwise siliciclastic section represent real cemented layers, not artefacts
- These are geologically important but plot off the clastic elastic trend
- Mask in rock physics crossplots; keep a separate carbonate cluster for identification

**Anhydrite / evaporite** (if present):
- Anhydrite density: ~2.98 g/cc; halite: ~2.16 g/cc
- Similarly real, similarly need to be masked from clastic analysis

### Step 6.3 — Density Infill Methods

Where RHOB is flagged for replacement (bad hole, not coal or carbonate), choose one of the following methods:

**Method A — Gardner Relation (from sonic)**

Gardner's empirical relation connects compressional velocity to bulk density for a wide range of sedimentary rocks:

```
ρ = a × Vp^b
```

Where ρ is in g/cc and Vp is in m/s. Standard Gardner parameters: a = 0.31, b = 0.25.

Calibrated to local data:
1. In good-hole intervals, plot RHOB (y-axis) vs Vp derived from DT (x-axis) in log–log space
2. Fit a straight line; slope = b, intercept = log(a)
3. Apply the fitted a and b to predict RHOB in washout intervals from the DT log

**Limitations**: Gardner is calibrated for wet rocks. It gives poor predictions in gas sands (density is lower than Gardner predicts for a given velocity because gas lowers velocity more than density), in carbonates, and in coals. Only use in shale-dominated washout intervals where no better method is available.

**Method B — NPHI–RHOB Cross-plot Trend**

In many formations a tight linear relationship exists between neutron porosity and bulk density at a given lithology:

```
RHOB_predicted = c₀ + c₁ × NPHI
```

Where c₀ and c₁ are calibrated from good-hole data in the same lithology.

Steps:
1. Isolate the washout interval's bounding formations and determine their expected lithology (from GR and PE)
2. In good-hole sections of the same lithology, plot NPHI vs RHOB; fit the linear trend
3. Apply the fitted equation to predict RHOB in the washout interval using the NPHI log (which is less sensitive to hole rugosity because the neutron tool is a full-bore measurement, not a pad tool)
4. If NPHI is also affected by the washout (rare but possible), use Method A instead

**Storing the edited log**:
Always create a new curve (e.g., RHOB_OK) for the edited density. Never overwrite the original RHOB. Document every edited interval: depth range, method used, and reason for editing.

---

## PHASE 7: ELASTIC LOG QC & Vp–Vs–DENSITY INTEGRATION

### Step 7.1 — DT to Vp Conversion and Unit Checking

Compressional slowness DT is stored in μs/ft (US field convention) or μs/m (SI/metric). Check the unit carefully — a factor-of-3 error in DT will produce completely wrong Vp values.

Conversion:
```
If DT in μs/ft:    Vp [m/s]  = 304,800 / DT[μs/ft]
If DT in μs/m:     Vp [m/s]  = 1,000,000 / DT[μs/m]
```

Sanity check on computed Vp values:
| Lithology | Expected Vp range (m/s) |
|-----------|-------------------------|
| Gas sand | 1,800–2,400 |
| Brine sand | 2,400–3,500 |
| Shale | 2,200–3,500 |
| Coal | 1,500–2,500 |
| Chalk / limestone | 3,500–5,500 |
| Anhydrite | 5,500–6,500 |
| Basement / granite | 5,000–6,500 |

Values outside these ranges for the expected lithology are suspect.

### Step 7.2 — Cycle Skip Detection and Repair

A cycle skip (also called skip correlation) occurs when the sonic tool fails to detect the first arrival of the compressional wave and instead latches onto a later cycle. The result is anomalously high DT (low Vp) values, often occurring as:
- Isolated spikes of high DT surrounded by reasonable values
- Sustained intervals of anomalously high DT where the tool struggled to find the first arrival (in gas sands, soft formations, or washed-out sections)

**Detection criteria**:
1. **Threshold approach**: flag all intervals where DT exceeds a formation-appropriate upper bound (e.g., DT > 120 μs/ft in consolidated formations below ~2000 m; DT > 140 μs/ft in shallow unconsolidated sections). Adjust the threshold per formation using expected Vp ranges above.
2. **Derivative approach**: compute the depth derivative d(DT)/dz. Cycle skips produce large positive-then-negative spikes in the derivative. Flag where |d(DT)/dz| exceeds a threshold (e.g., 5 μs/ft per metre).
3. **Visual inspection**: cycle skips are usually visually obvious — sudden large excursions in DT that do not correlate with any corresponding change in GR, RHOB, or resistivity.

**Repair options**:
- **Interpolation**: for isolated spikes (< 2–3 m), replace with linear interpolation between good values above and below
- **Faust model**: for longer cycle-skip intervals, replace with Vp modelled from resistivity (Phase 8)
- **Nearby well correlation**: if a laterally close well has good sonic over the same formation, consider using it as a guide for the expected DT trend

### Step 7.3 — Shear Sonic QC (DTS)

Where a measured shear log exists, apply the same unit conversion:
```
If DTS in μs/ft:   Vs [m/s]  = 304,800 / DTS[μs/ft]
If DTS in μs/m:    Vs [m/s]  = 1,000,000 / DTS[μs/m]
```

Check Vp/Vs ratios depth-by-depth. Expected ranges:
| Lithology / fluid | Vp/Vs |
|-------------------|-------|
| Dry rock (theoretical) | 1.41–1.8 |
| Brine sand | 1.6–2.0 |
| Gas sand | 1.5–1.75 |
| Shale | 2.2–3.0 |
| Coal | 1.9–2.2 |
| Calcite | 1.85–1.95 |
| Anhydrite | 1.75–1.85 |

Vp/Vs < 1.5 or > 3.5 for clastic rocks indicates an error in DT or DTS.

**Crossplot QC**: plot Vp vs Vs coloured by VWCL. Sand points should cluster around the Castagna et al. (1985) brine-sand line:
```
Vs [km/s] = 0.804 × Vp[km/s] − 0.856
```
Shale points should cluster around the mudrock line:
```
Vs [km/s] = 0.862 × Vp[km/s] − 1.172
```

Points that fall well off both lines are suspect and should be checked against the raw DT/DTS logs.

### Step 7.4 — Flag-Based Data Masking

Before generating any elastic crossplot used for rock physics interpretation, apply all flags:
- BAD_HOLE_FLAG → exclude (caliper washout)
- COAL_FLAG → separate cluster or exclude from clastic analysis
- CALCFLG / CEMENTED_LAYER_FLAG → separate cluster or exclude
- Any hydrocarbon flag → colour-code separately to distinguish HC from brine response

This is not optional — plotting unmasked data will corrupt trend lines and calibration.

---

## PHASE 8: Vp GAP-FILLING FROM RESISTIVITY (FAUST METHOD)

### Step 8.1 — When to Use Faust

The Faust (1953) method is appropriate when:
- No sonic log was run (common in older wells)
- The sonic is heavily cycle-skipped over a significant interval
- A pseudo-Vp log is needed for a well with only resistivity and GR (legacy data)

The method exploits the empirical observation that, in normally compacted brine-saturated siliciclastic rocks, formation resistivity and seismic velocity increase together with burial depth and porosity reduction.

**Important limitations**:
- Faust only applies to brine-saturated rock. Hydrocarbon zones have elevated resistivity that is not caused by velocity increase → Faust will over-predict Vp in HC zones.
- Faust does not account for lithology variation. Pure shales and pure sands have different Vp for the same resistivity at the same depth → separate calibrations may be needed.
- In overpressured formations, the normal compaction trend is violated → Faust will over-predict Vp.
- In carbonate-cemented intervals, resistivity is low (calcite) while Vp is high → Faust will under-predict.

Always mask Faust-predicted Vp from calibration crossplots in HC zones, and inspect the fit carefully across lithology boundaries.

### Step 8.2 — The Faust Equation

The original Faust (1953) equation in field units:

```
Vp [ft/s] = C × (Z[ft] × RT[Ω·m])^(1/6)
```

Where:
- Z = depth below surface, TVD, in feet
- RT = true formation resistivity in Ω·m (use deep reading: LLD, ILD, or equivalent)
- C = empirical constant, calibrated per well
- 1/6 ≈ 0.1667 is the universal exponent

In SI units:

```
Vp [m/s] = C_metric × (Z[m] × RT[Ω·m])^(1/6)
```

The metric constant C_metric differs from the field-unit constant because of the unit conversion on Z. The two are related by:

```
C_metric = C_field × (0.3048)^(1/6) ≈ C_field × 0.8255
```

A common starting point for the metric constant is approximately C_metric ≈ 820–900 for normally consolidated siliciclastic sections, but this must always be calibrated to the local well data.

### Step 8.3 — Calibrating the Faust Constant

**Setup**: you need a well (or interval) where both DT and RT are available and of good quality (no cycle skips, good caliper, brine-saturated). This is the calibration dataset.

**Procedure**:

1. Compute measured Vp from DT in the calibration interval:
   ```
   Vp_meas [m/s] = 304,800 / DT[μs/ft]
   ```

2. Compute the Faust predictor using the starting constant:
   ```
   F(z,R) = (Z × RT)^(1/6)
   ```

3. Plot Vp_meas (y-axis) vs F(z,R) (x-axis). The slope of the best-fit line through the origin is the calibrated constant C.

   Alternatively, compute C at each depth sample:
   ```
   C_i = Vp_meas_i / (Z_i × RT_i)^(1/6)
   ```
   Then take the median of C_i over the calibration interval. (Use median rather than mean to reduce sensitivity to outliers from HC zones or cemented layers.)

4. Apply any necessary data masking before computing C:
   - Exclude HC zones (RT anomalously high for the depth, not due to velocity)
   - Exclude cemented layers (high RT for non-compaction reasons)
   - Exclude washout intervals (unreliable RT from mud invasion)
   - Exclude coal (very different compaction behaviour)

5. Check the calibration by plotting measured Vp vs Faust-predicted Vp on a 1:1 scatter plot. A well-calibrated Faust model will show points clustering along the 1:1 line with acceptable scatter (±100–150 m/s is typical).

6. Consider calibrating separate constants for:
   - Sand-dominated intervals vs shale-dominated intervals (GR can separate these)
   - Different depth windows if there is evidence of a compaction break

### Step 8.4 — Applying the Faust Model and Building the Composite Vp Log

1. Apply the calibrated Faust equation at all depths to generate Vp_Faust.

2. Build a composite Vp log (VP_COMP) using the following splice logic:

   ```
   VP_COMP = Vp_measured    where:  BAD_HOLE_FLAG = 0
                                    AND  DT is not cycle-skipped
                                    AND  interval is not HC zone (for Faust accuracy)

   VP_COMP = Vp_Faust       elsewhere
   ```

3. Create a splice indicator log (e.g., VP_SOURCE: 0 = measured, 1 = Faust) to document which samples came from which source.

4. At the splice boundaries, check that the two Vp versions agree to within ±50 m/s. A step at the splice indicates either a calibration error or a genuine lithology/fluid change that the Faust model is not capturing.

5. Convert VP_COMP back to DT units if the downstream software requires slowness input:
   ```
   DT_MOD [μs/ft] = 304,800 / VP_COMP[m/s]
   ```

---

## PHASE 9: WELL CORRELATION & STRATIGRAPHIC FRAMEWORK

### Step 9.1 — Formation Tops Loading and QC

Load formation tops from well completion reports, regional biostratigraphic studies, or company databases. Enter all tops in a consistent depth reference (TVDkb or TVDss — match the reference used for log depths).

QC each top pick by checking it against the log response:
- Shale / seal tops: expect GR increase, resistivity decrease, density increase
- Sand / reservoir tops: expect GR decrease, resistivity spike (if HC), NPHI–RHOB separation
- Carbonate tops: expect PE increase, density increase, NPHI decrease
- Unconformity surfaces: may show no clear log response; check for missing section vs correlative conformity

If a top does not match the expected log signature, check:
1. Whether the well was drilled deviated — MD tops need to be converted to TVD using the deviation survey
2. Whether the top was picked on a different datum in the original report and needs datum conversion
3. Whether the formation is genuinely absent (erosional or depositional hiatus) vs the pick being incorrect

### Step 9.2 — Well Correlation Panel Construction

Build a multi-well correlation panel:

1. Choose a correlation datum: use a mappable, areally extensive marker — typically a regionally conformable shale surface (maximum flooding surface) or a major formation boundary
2. Convert all well depths to TVD relative to that datum (TVDml = TVD minus datum depth)
3. Lay out wells in map-view order (not alphabetical) to make lateral correlation visually intuitive
4. Display at minimum: GR and deep resistivity; add RHOB and DT if available
5. Annotate each well with formation tops

Correlation checks:
- Are formation thicknesses geologically plausible given structural position?
- Do major shale markers correlate laterally?
- Are thinning/thickening trends consistent with the known depositional model?
- Are any formations duplicated (fault repetition) or missing (fault cutting out section)?

A consistent stratigraphic framework is essential before formation-level crossplot analysis — without it, a crossplot coloured "by formation" is meaningless.

---

## PHASE 10: FORMATION-LEVEL ELASTIC CROSSPLOT ANALYSIS

### Step 10.1 — RHOB vs Vp Crossplot (Acoustic Impedance Space)

This is the primary rock physics diagnostic plot. It shows the relationship between elastic velocity and density — the two properties that control acoustic impedance and therefore seismic reflection amplitude.

**Setup**:
- X-axis: Vp [m/s or km/s], typically 1,500–5,000 m/s
- Y-axis: RHOB [g/cc], typically 1.8–2.9 g/cc
- Colour by VWCL (clay volume): use a colour scale from blue (clean sand) to red (shale)
- Plot all wells for the same formation together
- Mask all flagged data (coal, carbonate, washouts) before plotting

**Expected features and their interpretation**:

*Sand–shale separation*: clean sands (low VWCL, blue) should form a distinct cluster from shales (high VWCL, red). The sand cluster should sit at higher Vp and higher RHOB than shale for the same depth. If sand and shale overlap completely, the VWCL model may be wrong.

*Compaction trend*: within each lithology cluster, deeper samples should plot toward higher Vp and higher RHOB. A positive Vp–RHOB correlation is the signature of burial compaction.

*Hydrocarbon effect*: gas or condensate shifts sand points downward and to the left (lower density, lower Vp) relative to the brine-saturated trend. Oil shifts sand points slightly left (lower Vp) with less density effect than gas. The magnitude of the shift depends on gas saturation, porosity, and depth. Identifying this shift is critical for AVO and DHI analysis.

*Carbonate outliers* (even if flagged): plot as a tight cluster at high Vp (>4000 m/s) and high RHOB (>2.65 g/cc). Useful to confirm that the calcite flag correctly identifies these points.

*Coal outliers*: plot far to the lower-left — low density (~1.3–1.5 g/cc) and low Vp (~1,500–2,000 m/s). Coal is easily identified even without a coal flag.

**Using multiple colour schemes**:
Run the same crossplot with three different colouring variables:
1. VWCL — identifies lithology
2. PHIT — identifies porosity trends (higher porosity = lower Vp, lower RHOB in the same lithology)
3. Formation or well — identifies systematic inter-well differences

If colouring by well shows that one well plots systematically offset from all others at the same VWCL and PHIT, this may indicate:
- A depth-shift error (Phase 4 not applied correctly)
- A density editing issue (Phase 6)
- A real geological difference (different diagenetic history, cementation, abnormal pressure)

### Step 10.2 — Vp–Vs Crossplot

This plot is only possible where measured Vs exists. It is the calibration foundation for the rock physics model.

**Setup**:
- X-axis: Vp [km/s]
- Y-axis: Vs [km/s]
- Plot reference lines: Castagna mudrock line and brine-sand line
- Colour by VWCL and by formation

**What to look for**:
- Shale points should track the mudrock line: Vs = 0.862 × Vp − 1.172
- Brine sand points should track the sand line: Vs = 0.804 × Vp − 0.856
- The gap between the two lines narrows at high Vp (deeply buried, well-cemented) and widens at low Vp (shallow, soft)
- Gas sands: lower Vp than brine sands at the same Vs → shift points to the left relative to the brine-sand line
- Coal: distinctive cluster, typically near Vp/Vs ≈ 2.0, plotting close to the mudrock line despite being coal

The spacing between the sand and shale lines on this plot defines the "fluid discrimination" potential of the formation. A large gap = good DHI / AVO response expected. A small gap = difficult fluid discrimination from seismic.

### Step 10.3 — Per-Formation Summary

Repeat the Rho–Vp and Vp–Vs crossplots for each working interval defined in Phase 9. Document for each formation:
- Which lithologies are present and how well separated they are
- Whether hydrocarbons are visible as an elastic effect
- Which wells have anomalous data (and why)
- The sand-line trend parameters (slope, intercept) for input to the RPM calibration

---

## PHASE 11: ROCK PHYSICS MODEL CALIBRATION

### Step 11.1 — Model Selection

The choice of rock physics model depends on the degree of cementation and the stress sensitivity of the formation:

| Formation character | Recommended model | Notes |
|--------------------|------------------|-------|
| Unconsolidated sand (shallow, high porosity) | Soft Sand (Hertz-Mindlin + lower Hashin-Shtrikman) | Strong pressure dependence; Vp increases rapidly with depth |
| Friable sand (moderate burial, uncemented but compacted) | Friable Sand (modified Hashin-Shtrikman) | Less pressure-sensitive than soft sand |
| Cemented / partially cemented sand | Patchy Cement model | Both contact cement and pressure sensitivity; appropriate for most Jurassic/Triassic sandstones |
| Diagenetically complex (mixed cement, dissolution) | QSAND or Dvorkin–Nur extended | More parameters; requires core data for calibration |

For most intermediate-to-deep (>1500 m) siliciclastic reservoirs, the **Patchy Cement model** is the appropriate starting point.

### Step 11.2 — Patchy Cement Model Parameters

The Patchy Cement model (Dvorkin, Nur et al.) combines two end-member scenarios:
1. **Contact cement only** (scheme 2 cement): cement deposited at grain contacts, stiffening the frame dramatically even at small cement volumes
2. **Hertz-Mindlin contact physics** for the uncemented fraction

The mixing is controlled by the parameter **f** (fraction of grain contacts that are cemented).

| Parameter | Symbol | Typical range | Effect |
|-----------|--------|--------------|--------|
| Critical porosity | φ_c | 0.36–0.42 | Sets the end-member loose-pack porosity; use 0.40 for quartz sand |
| Coordination number | n | 8–12 | Average grain contacts per grain; 9 for well-sorted sand, 11 for moderate sorting |
| Cement fraction | f | 0.0–1.0 | Key calibration parameter; controls how stiff the frame is at a given porosity |
| Shear friction coefficient | μ | 0.0–0.5 | Controls Vs sensitivity to pressure; 0.5 for rough contacts, 0 for frictionless |
| Mineral bulk modulus | K_min | Fixed by mineralogy | Quartz: 36.6 GPa; use VRH average for clay mixture |
| Mineral shear modulus | G_min | Fixed by mineralogy | Quartz: 45 GPa; clay: ~7 GPa |
| Mineral density | ρ_min | Fixed by mineralogy | Quartz: 2.65 g/cc; use VRH average |

### Step 11.3 — RPM Forward Modelling and Calibration

The goal is to find the parameter set (especially f per formation) that reproduces both the Vp–Vs trend and the RHOB–Vp trend simultaneously.

**Step-by-step calibration on a well with measured Vs**:

1. Extract depth samples at which: BAD_HOLE_FLAG = 0, no coal flag, no calcite flag, interval is brine-saturated (below OWC/GWC).

2. Run fluid substitution to 100% brine (Gassmann, Phase 12) if the extracted samples include any HC saturation. RPM calibration must be done on brine-saturated data — fluid substitution contaminates the framework if not removed first.

3. Compute effective pressure P_eff at each sample from Phase 2 pressure logs.

4. Run the RPM forward model with starting parameters (e.g., n = 11, φ_c = 0.40, f = 0.8) to generate predicted Vp, Vs, and RHOB as a function of PHIT.

5. Plot modelled Vp vs Vs (as a curve) on top of the measured Vp–Vs data scatter. Assess the fit:
   - If model Vs is too high for a given Vp: reduce f (less cementation) or reduce n (fewer contacts)
   - If model Vs is too low: increase f or n
   - If the model slope (d(Vs)/d(Vp)) is wrong: adjust the Hertz-Mindlin pressure component (friction coefficient μ, or P_eff)

6. Overlay the same RPM curve on the RHOB vs Vp crossplot to confirm the model honours both dimensions simultaneously.

7. Repeat per formation interval — f typically increases with depth (greater burial → more cementation). Create a lookup table of calibrated f values per formation interval.

**Practical iteration guide for f**:
- Start at f = 0.8 for deeply buried sands (> 3000 m)
- Start at f = 0.4–0.6 for shallower sands (1500–3000 m)
- If observed Vp/Vs is lower than model: the sand is less cemented than assumed → reduce f
- If observed Vp/Vs is higher than model: more cemented → increase f
- Changes in f of 0.1 units shift Vs by approximately 50–150 m/s at typical reservoir conditions

### Step 11.4 — Generating Synthetic Vs Logs

With calibrated parameters, run the RPM in prediction mode to generate synthetic Vs at wells without measured shear:

Inputs per depth sample:
- VP_COMP (from Phase 8)
- RHOB_OK (from Phase 6)
- PHIT (from CPI)
- VWCL (from CPI, for mineral moduli mixing)
- P_diff (from Phase 2)
- TEMP (from Phase 2, for fluid properties if HC-bearing)

Output: VS_MOD log.

Verify the synthetic Vs by checking:
- Vp/Vs ratios are in the expected range per formation (see Phase 7 table)
- VS_MOD honours the Vp–Vs trend established on the calibration well
- Shear impedance (Vs × RHOB) varies sensibly with lithology

---

## PHASE 12: FLUID SUBSTITUTION SETUP (GASSMANN)

### Step 12.1 — Gassmann's Equation

Gassmann's equation predicts how the elastic moduli of a rock change when the pore fluid is changed. It is the fundamental rock physics tool for "fluid substitution" — predicting seismic response under different fluid scenarios.

**Gassmann forward substitution** (from fluid 1 to fluid 2):

Step 1 — Compute dry-frame bulk modulus from the saturated state:
```
K_dry = K_sat1 × (φ × K_min / K_fl1 + 1 − φ) − K_min
        ─────────────────────────────────────────────────
        φ × K_min / K_fl1 + K_sat1/K_min − 1 − φ
```

Step 2 — Substitute the new fluid:
```
K_sat2 = K_dry + (1 − K_dry/K_min)²
                  ──────────────────────────────────────
                  φ/K_fl2 + (1−φ)/K_min − K_dry/K_min²
```

Step 3 — Shear modulus is unchanged by fluid substitution:
```
G_sat2 = G_sat1 = G_dry
```

Step 4 — Update density:
```
ρ_sat2 = ρ_mineral × (1−φ) + ρ_fl2 × φ
```

Step 5 — Compute new velocities:
```
Vp2 = √[(K_sat2 + 4/3 × G_sat2) / ρ_sat2]
Vs2 = √[G_sat2 / ρ_sat2]
```

Where φ is the total connected porosity (use PHIT for Gassmann; PHIE in some shaly-sand extensions).

### Step 12.2 — Mineral End-Members

Use VRH (Voigt-Reuss-Hill) mixing to compute the mineral frame moduli from volume fractions:

| Mineral | K (GPa) | G (GPa) | ρ (g/cc) |
|---------|---------|---------|---------|
| Quartz | 36.6 | 45.0 | 2.65 |
| K-feldspar | 37.5 | 15.0 | 2.57 |
| Plagioclase | 55.0 | 28.0 | 2.63 |
| Calcite | 76.8 | 32.0 | 2.71 |
| Dolomite | 94.9 | 45.0 | 2.87 |
| Clay (illite) | 25.0 | 9.0 | 2.58 |
| Clay (smectite) | 12.0 | 4.0 | 2.58 |
| Anhydrite | 56.0 | 29.0 | 2.98 |

For a quartz–clay mixture:
```
K_min = VWCL × K_clay + (1−VWCL) × K_quartz   [Voigt upper bound]
K_min = 1 / (VWCL/K_clay + (1−VWCL)/K_quartz)  [Reuss lower bound]
K_min_VRH = 0.5 × (K_Voigt + K_Reuss)           [Hill average]
```

Apply same mixing for G_min and ρ_min.

### Step 12.3 — Fluid Properties via Batzle-Wang (1992)

Batzle and Wang (1992) provide empirical equations for bulk modulus and density of brine, oil, and gas as functions of temperature, pressure, and fluid composition. These are the industry standard.

**Brine**:
Inputs: salinity [ppm NaCl equivalent], T [°C], P [MPa]
Outputs: K_brine [GPa], ρ_brine [g/cc]

The brine bulk modulus increases with pressure, decreases with temperature, and increases with salinity. At typical reservoir conditions (T = 70–120°C, P = 20–50 MPa, salinity = 30,000–80,000 ppm), K_brine is typically 2.2–3.0 GPa.

**Oil**:
Inputs: API gravity, GOR [sm³/sm³ or SCF/STB], gas gravity, T [°C], P [MPa]
Outputs: K_oil [GPa], ρ_oil [g/cc]

Light oils (high API) have lower K and ρ than heavy oils. Live oil (with dissolved gas) has lower K and ρ than dead oil. Use live oil properties at reservoir conditions.

**Gas / condensate**:
Inputs: gas gravity (specific gravity relative to air = 1), T [°C], P [MPa]
Outputs: K_gas [GPa], ρ_gas [g/cc]

Gas has very low K (0.02–0.15 GPa at reservoir conditions) and very low ρ (0.05–0.3 g/cc). Even small gas saturations (10–20%) dramatically reduce K_sat because the pore fluid stiffness K_fl is governed by the harmonic mean of the phase moduli (the Wood equation) — a small fraction of gas in a brine-dominated pore makes the mixture almost as compressible as pure gas.

**Patchy saturation vs homogeneous mixing**:
Gassmann assumes uniform (homogeneous) fluid mixing at the pore scale. In practice, partial saturation often occurs in patches at scales larger than the pore but smaller than the seismic wavelength. For patchy saturation, use the Voigt average of K_fl from the two phases instead of Wood's equation. The choice between homogeneous and patchy mixing affects the predicted Vp at partial saturations and matters for CO₂ injection scenarios.

### Step 12.4 — Running Fluid Substitution as Logs

Apply Gassmann substitution depth-by-depth as a log computation:

**Inputs per sample**:
- RHOB_OK → ρ_sat1 (measured density)
- VP_COMP → Vp1 (compressional velocity)
- VS_MOD (or VS measured) → Vs1 (shear velocity)
- PHIT (total porosity)
- VWCL (for mineral moduli via VRH)
- SW / SWT (in-situ water saturation — needed to characterise the in-situ fluid mixture for K_fl1)
- T, P (from Phase 2 — for Batzle-Wang fluid properties)
- Fluid properties for in-situ fluid and target fluid (Phase 12.3)

**Common substitution scenarios**:
1. In-situ → 100% brine: creates the "wet rock" baseline. Use for rock physics template construction.
2. In-situ → 100% gas or CO₂: models the fully HC-charged scenario. Use for DHI prediction.
3. Brine → CO₂ (injection simulation): predicts time-lapse seismic response to CO₂ storage.

**Store results as new log curves**:
- VPBRINE, VSBRINE, RHOBRINE (brine-substituted)
- VPGAS, VSGAS, RHOGAS (gas/CO₂-substituted)
- AI_BRINE = VPBRINE × RHOBRINE (brine acoustic impedance)
- AI_GAS = VPGAS × RHOGAS

---

## DELIVERABLES CHECKLIST

At workflow completion, the following conditioned logs should exist per well:

| Curve | Description | Created in Phase |
|-------|-------------|-----------------|
| RHOB_OK | Density after DRHO QC, flag exclusion, and washout infill | 6 |
| DT_OK | Sonic after depth shift and cycle-skip repair | 4, 7 |
| VP_COMP | Composite Vp: measured where good, Faust-modelled otherwise | 8 |
| VS | Measured shear velocity (calibration well only) | 7 |
| VS_MOD | Modelled shear velocity from RPM (all wells) | 11 |
| PHIT | Total porosity from reviewed and updated CPI | 5 |
| PHIE | Effective porosity from reviewed and updated CPI | 5 |
| VWCL | Clay volume from reviewed and updated CPI | 5 |
| SW / SWT | Water saturation from reviewed and updated CPI | 5 |
| COAL_FLAG | Coal seam exclusion flag | 1/6 |
| CALCFLG | Carbonate cement exclusion flag | 1/6 |
| BAD_HOLE_FLAG | Caliper washout exclusion flag | 3 |
| VP_SOURCE | Splice indicator for VP_COMP (0=measured, 1=Faust) | 8 |
| TEMP | Formation temperature log | 2 |
| PORE_PRESS | Pore pressure log | 2 |
| DIFF_PRESS | Differential (effective) pressure log | 2 |
| VPBRINE | Fluid-substituted Vp at 100% brine | 12 |
| VSBRINE | Fluid-substituted Vs at 100% brine | 12 |
| RHOBRINE | Density at 100% brine saturation | 12 |
| VPGAS | Fluid-substituted Vp at 100% gas/CO₂ | 12 |

---

## Common Pitfalls and QC Sanity Checks

| Check | Expected result | Possible failure |
|-------|----------------|-----------------|
| PHIE ≤ PHIT everywhere | Always true | Clay correction error in CPI |
| PHIT ≤ 0.42 in sand | Should not exceed critical porosity | Porosity overestimation |
| Vs < Vp everywhere | Fundamental physics | Unit error in DTS conversion |
| Vp/Vs between 1.5 and 3.5 in clastics | Expected range | Cycle skip in DT or DTS |
| Gardner-predicted RHOB within 0.1 g/cc of measured | Good calibration | Gassy interval included in calibration |
| Faust-predicted Vp within ±150 m/s of measured | Good calibration | HC zones included in calibration |
| K_dry > 0 after Gassmann back-strip | Physical requirement | Vp/Vs/RHOB inconsistency; depth-shift error |
| ρ_brine > ρ_gas everywhere | Always true | Fluid property calculation error |
