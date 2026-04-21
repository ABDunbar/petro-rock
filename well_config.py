"""
well_config.py — centralised per-well parameters for the petro-rock notebook pipeline.

To switch wells, change WELL_NAME in the first cell of any notebook to one of the keys below.
Add missing values (marked None) once well reports / headers are available.
"""

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
        "tops_file"    : "wells/Dvalin_formation_tops.csv",
        "tops_well_id" : "NO 6507/4-2 S",
        "log_top"      : None,    # use full LAS range; update once log interval known
        "log_base"     : None,
        "kb_above_msl" : 27.5,   # m  typical Norwegian Sea semi-sub (update when known)
        "water_depth"  : 380.0,  # m  approximate Dvalin area       (update when known)
        "t_seabed"     : 4.0,    # °C Norwegian Sea bottom water
        "geotherm"     : 0.038,  # °C/m Norwegian Sea typical        (update when known)
        "salinity_ppm" : 50_000, # ppm NaCl eq. placeholder          (update from Rw data)
        "curve_map"    : _DVALIN_CURVE_MAP,
    },

    # ── Dvalin 6507/7-1 ───────────────────────────────────────────────────────
    "65077-1": {
        "las_file"     : "wells/65077-1_petrorock.las",
        "tops_file"    : "wells/Dvalin_formation_tops.csv",
        "tops_well_id" : "NO 6507/7-1",
        "log_top"      : None,
        "log_base"     : None,
        "kb_above_msl" : 27.5,
        "water_depth"  : 380.0,
        "t_seabed"     : 4.0,
        "geotherm"     : 0.038,
        "salinity_ppm" : 50_000,
        "curve_map"    : _DVALIN_CURVE_MAP,  # note: no ACS (Vs) in this well
    },

    # ── Dvalin 6507/7-14 S ────────────────────────────────────────────────────
    "65077-14S": {
        "las_file"     : "wells/65077-14 S_petrorock.las",
        "tops_file"    : "wells/Dvalin_formation_tops.csv",
        "tops_well_id" : "NO 6507/7-14 S",
        "log_top"      : None,
        "log_base"     : None,
        "kb_above_msl" : 27.5,
        "water_depth"  : 380.0,
        "t_seabed"     : 4.0,
        "geotherm"     : 0.038,
        "salinity_ppm" : 50_000,
        "curve_map"    : _DVALIN_CURVE_MAP,
    },

    # ── Dvalin 6507/7-15 S ────────────────────────────────────────────────────
    "65077-15S": {
        "las_file"     : "wells/65077-15 S_petrorock.las",
        "tops_file"    : "wells/Dvalin_formation_tops.csv",
        "tops_well_id" : "NO 6507/7-15 S",
        "log_top"      : None,
        "log_base"     : None,
        "kb_above_msl" : 27.5,
        "water_depth"  : 380.0,
        "t_seabed"     : 4.0,
        "geotherm"     : 0.038,
        "salinity_ppm" : 50_000,
        "curve_map"    : _DVALIN_CURVE_MAP,
    },
}
