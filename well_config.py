"""
well_config.py — centralised per-well parameters for the petro-rock notebook pipeline.

To switch wells, change WELL_NAME in the first cell of any notebook to one of the keys below.
Add missing values (marked None) once well reports / headers are available.

Public API
----------
ACTIVE_WELL               str    currently selected well — edit here to switch all notebooks at once
get_cfg(well_name)        -> dict  merged defaults + well overrides
form_colours(names)       -> dict  auto-assigned colours keyed by formation name
set_plot_style()                   apply shared matplotlib rcParams
"""

import matplotlib.pyplot as plt

# ── Active well selection ───────────────────────────────────────────────────
# Change this to switch every notebook to a different well in one edit.
# Available: "15_9-F-1A", "65074-2S", "65077-1", "65077-14S", "65077-15S"
ACTIVE_WELL = "65077-15S"

_DVALIN_CURVE_MAP = {
    "AC"           : "DT",    # P-wave sonic (μs/ft)
    "ACS"          : "DTS",   # S-wave sonic (μs/ft)  — absent in 65077-1
    "DEN"          : "RHOB",  # bulk density (g/cc)
    "DENC"         : "DRHO",  # density correction (g/cc)
    "NEU"          : "NPHI",  # neutron porosity (fraction)
    "RDEP"         : "RT",    # deep resistivity (Ω·m)
    "BS_MERGED_ED" : "BS",    # bit size, merged & edited (inches)
}

WELLS = {
    # ── Volve demo well ────────────────────────────────────────────────────────
    "15_9-F-1A": {
        "las_file"     : "wells/15_9-F-1A.LAS",
        "tops_file"    : "wells/Volve_formation_tops.csv",
        "tops_well_id" : "NO 15/9-F-1 A",
        "reservoir_fm" : "Hugin Fm",
        "log_top"      : 2605,    # m MD  (top of 8.5" section with RHOB)
        "log_base"     : 3680,    # m MD
        "kb_above_msl" : 54.9,   # m  (Kelly Bushing above MSL)
        "water_depth"  : 91.1,   # m  (seabed below MSL)
        "t_seabed"     : 5.0,    # °C
        "geotherm"     : 0.031,  # °C/m from seabed
        "salinity_ppm" : 57_500, # ppm NaCl eq. (Hugin Fm formation water)
        "curve_map"    : {},      # no renaming needed — native mnemonics
    },

    # ── Dvalin 6507/4-2 S ─────────────────────────────────────────────────────
    "65074-2S": {
        "las_file"     : "wells/65074-2 S_petrorock.las",
        "tops_file"    : "wells/Dvalin_VM_tops_ABD.asc",
        "tops_well_id" : "NO 6507/4-2 S",
        "reservoir_fm" : "GARN FM",
        "log_top"      : None,    # use full LAS range; update once log interval known
        "log_base"     : None,
        "kb_above_msl" : 32.0,   # m  SODIR Factpages
        "water_depth"  : 450.0,  # m  SODIR Factpages
        "t_seabed"     : 4.0,    # °C Norwegian Sea bottom water
        "geotherm"     : 0.040,  # °C/m from BHT 162°C at 3948 m below seabed (uncorrected)
        "salinity_ppm" : 50_000, # ppm NaCl eq. placeholder          (update from Rw data)
        "curve_map"    : _DVALIN_CURVE_MAP,
    },

    # ── Dvalin 6507/7-1 ───────────────────────────────────────────────────────
    "65077-1": {
        "las_file"     : "wells/65077-1_petrorock.las",
        "tops_file"    : "wells/Dvalin_VM_tops_ABD.asc",
        "tops_well_id" : "NO 6507/7-1",
        "reservoir_fm" : "GARN FM",
        "log_top"      : None,
        "log_base"     : None,
        "kb_above_msl" : 25.0,   # m  SODIR Factpages
        "water_depth"  : 367.0,  # m  SODIR Factpages
        "t_seabed"     : 4.0,    # °C Norwegian Sea bottom water
        "geotherm"     : 0.038,  # °C/m from BHT 170°C at 4426 m below seabed (uncorrected)
        "salinity_ppm" : 50_000,
        "curve_map"    : _DVALIN_CURVE_MAP,  # note: no ACS (Vs) in this well
    },

    # ── Dvalin 6507/7-14 S ────────────────────────────────────────────────────
    "65077-14S": {
        "las_file"     : "wells/65077-14 S_petrorock.las",
        "tops_file"    : "wells/Dvalin_VM_tops_ABD.asc",
        "tops_well_id" : "NO 6507/7-14 S",
        "reservoir_fm" : "GARN FM",
        "log_top"      : None,
        "log_base"     : None,
        "kb_above_msl" : 25.0,   # m  SODIR Factpages
        "water_depth"  : 344.0,  # m  SODIR Factpages
        "t_seabed"     : 4.0,    # °C Norwegian Sea bottom water
        "geotherm"     : 0.038,  # °C/m from BHT 162°C at 4108 m below seabed (uncorrected)
        "salinity_ppm" : 50_000,
        "curve_map"    : _DVALIN_CURVE_MAP,
    },

    # ── Dvalin 6507/7-15 S ────────────────────────────────────────────────────
    "65077-15S": {
        "las_file"     : "wells/65077-15 S_petrorock.las",
        "tops_file"    : "wells/Dvalin_VM_tops_ABD.asc",
        "tops_well_id" : "NO 6507/7-15 S",
        "reservoir_fm" : "GARN FM",
        "log_top"      : None,
        "log_base"     : None,
        "kb_above_msl" : 18.0,   # m  SODIR Factpages
        "water_depth"  : 399.0,  # m  SODIR Factpages
        "t_seabed"     : 4.0,    # °C Norwegian Sea bottom water
        "geotherm"     : 0.039,  # °C/m from BHT 165°C at 4135 m below seabed (uncorrected)
        "salinity_ppm" : 50_000,
        "curve_map"    : _DVALIN_CURVE_MAP,
    },
}

# ── Default physics / QC parameters ───────────────────────────────────────────
# Any well can override individual keys by including them in its WELLS entry.

_DEFAULTS = {
    # Caliper QC (notebook 03)
    "cal_enlarged_in"        : 0.5,    # inches over BS — mild washout flag
    "cal_bad_hole_in"        : 1.0,    # inches over BS — severe washout flag
    "drho_qc_thresh"         : 0.10,   # g/cc  density correction flag

    # Depth shift / Gardner (notebooks 04 & 06)
    "gardner_a"              : 0.31,   # Gardner a coefficient (SI units)
    "gardner_b"              : 0.25,   # Gardner b exponent
    "depth_shift_max_samples": 100,    # ± samples searched for best shift

    # Archie (notebook 05)
    "archie_a"               : 1.0,    # tortuosity factor
    "archie_m"               : 2.0,    # cementation exponent
    "archie_n"               : 2.0,    # saturation exponent

    # Density editing (notebook 06)
    "drho_edit_thresh"       : 0.15,   # g/cc  DRHO cut for bad-density edit
    "rhob_coal_max"          : 1.80,   # g/cc  upper bound for coal identification
    "rhob_carbonate"         : 2.72,   # g/cc  matrix density for carbonate flag
    "infill_gap_max_m"       : 5.0,    # m     max NaN gap filled by interpolation (longer → Gardner)

    # Elastic QC bounds (notebook 07)
    "vp_min"                 : 1500.0, # m/s
    "vp_max"                 : 6500.0, # m/s
    "vs_min"                 :  700.0, # m/s
    "vs_max"                 : 4000.0, # m/s
    "vpvs_min"               : 1.35,
    "vpvs_max"               : 4.0,
    "spike_thresh_vp"        :  600,   # m/s per sample — cycle-skip detection
    "spike_thresh_vs"        :  400,   # m/s per sample

    # Castagna mudrock line  Vs = castagna_a * Vp + castagna_b  (m/s)
    "castagna_a"             : 0.8042,
    "castagna_b"             : -855.9,

    # Faust Vp calibration (notebook 08)
    "faust_rt_min"           : 0.2,    # Ω·m  exclude noise
    "faust_rt_max"           : 10.0,   # Ω·m  exclude hydrocarbons
}


# ── Public helpers ─────────────────────────────────────────────────────────────

def get_cfg(well_name: str) -> dict:
    """Return a merged config dict: defaults overridden by well-specific values."""
    if well_name not in WELLS:
        raise KeyError(
            f"Unknown well '{well_name}'. Available: {list(WELLS)}"
        )
    return {**_DEFAULTS, **WELLS[well_name]}


def form_colours(formation_names) -> dict:
    """Auto-assign colours from the tab20 colourmap to an iterable of formation names."""
    cmap = plt.get_cmap("tab20")
    return {name: cmap(i % 20) for i, name in enumerate(formation_names)}


def _load_tops_petrel_asc(tops_file, well_id: str):
    """Parse a Petrel VERSION 2 well-tops .asc export.

    Extracts Surface (PICKS), MD (DEPTH), and Well columns.
    Well names in the file have no country prefix, so 'NO ' is prepended
    to match the tops_well_id convention used elsewhere.
    Null sentinel -999 is replaced with NaN.
    """
    import shlex
    import pandas as pd
    import numpy as np

    # --- parse header to get ordered column names ---
    columns = []
    in_header = False
    data_lines = []
    with open(tops_file, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("BEGIN HEADER"):
                in_header = True
                continue
            if line.startswith("END HEADER"):
                in_header = False
                continue
            if in_header:
                columns.append(line.strip())
                continue
            if line.startswith("#") or line.startswith("VERSION"):
                continue
            if line.strip():
                data_lines.append(line)

    # column indices we care about
    col_md      = columns.index("MD")
    col_surface = columns.index("Surface")
    col_well    = columns.index("Well")
    col_z       = columns.index("Z")

    rows = []
    for line in data_lines:
        tokens = shlex.split(line)
        if len(tokens) <= max(col_md, col_surface, col_well):
            continue
        md      = float(tokens[col_md])
        surface = tokens[col_surface]
        well    = "NO " + tokens[col_well]
        if md == -999:
            md = float("nan")
        tvdss = float(tokens[col_z]) if tokens[col_z] != "-999" else float("nan")
        rows.append({"WELL": well, "DEPTH": md, "PICKS": surface, "TVDSS": tvdss})

    df = pd.DataFrame(rows)
    f = (
        df[df["WELL"] == well_id]
        .sort_values("DEPTH")
        .drop_duplicates(subset="DEPTH")
        .copy()
        .reset_index(drop=True)
    )
    return f


def load_tops(tops_file, well_id: str):
    """Load, clean, and return formation tops for one well.

    Dispatches on file extension:
      .asc  — Petrel VERSION 2 well-tops export
      .csv  — legacy CSV (WELL, DEPTH, PICKS columns)

    Cleans trailing qualifiers from PICKS names ('. Top', ' VOLVE Top',
    ' Sand VOLVE Top', etc.) so that formation names are concise and
    consistent across wells.

    Returns a DataFrame sorted by DEPTH with duplicate depths removed.
    """
    import pandas as pd

    if str(tops_file).lower().endswith(".asc"):
        return _load_tops_petrel_asc(tops_file, well_id)

    df = pd.read_csv(tops_file)
    f = (
        df[df['WELL'] == well_id]
        .sort_values('DEPTH')
        .drop_duplicates(subset='DEPTH')
        .copy()
        .reset_index(drop=True)
    )
    f['PICKS'] = (
        f['PICKS']
        .str.replace(r'[. ]*(?:Sand\s+)?(?:VOLVE\s+)?Top$', '', regex=True)
        .str.strip()
    )
    return f


def set_plot_style() -> None:
    """Apply the shared petro-rock matplotlib style to the current session."""
    plt.rcParams.update({
        "font.family"    : "DejaVu Sans",
        "font.size"      : 9,
        "axes.linewidth" : 0.8,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "figure.dpi"     : 120,
    })
