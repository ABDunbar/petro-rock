"""
patch_multiwell.py — patches all 8 notebooks to use centralised well_config.py.

Run from the project root:  uv run python scripts/patch_multiwell.py
"""

import json
from pathlib import Path

NB_DIR = Path("notebooks")

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def load(nb_path):
    with open(nb_path) as f:
        return json.load(f)

def save(nb, nb_path):
    with open(nb_path, "w") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print(f"  saved {nb_path}")

def set_source(nb, idx, source_str):
    """Replace the source of cell at index idx."""
    lines = source_str.split("\n")
    # Rebuild source list with \n between lines (last line has no trailing \n)
    source_list = [l + "\n" for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
    nb["cells"][idx]["source"] = source_list
    # Clear outputs for code cells so notebook is clean
    if nb["cells"][idx]["cell_type"] == "code":
        nb["cells"][idx]["outputs"] = []
        nb["cells"][idx]["execution_count"] = None


# ─────────────────────────────────────────────────────────────────────────────
# Shared new-source strings
# ─────────────────────────────────────────────────────────────────────────────

CONFIG_HEADER = """\
import sys; sys.path.insert(0, '..')
from well_config import WELLS

# ── Well selection ────────────────────────────────────────────────────────────
WELL_NAME = "15_9-F-1A"   # ← change this to switch wells
cfg       = WELLS[WELL_NAME]\
"""

PLOT_STYLE = """\
# ── Plot style ─────────────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family'      : 'DejaVu Sans',
    'font.size'        : 9,
    'axes.linewidth'   : 0.8,
    'xtick.direction'  : 'in',
    'ytick.direction'  : 'in',
    'figure.dpi'       : 120,
})\
"""

RENAME_SNIPPET = "df.rename(columns=cfg.get('curve_map', {}), inplace=True)"


# ─────────────────────────────────────────────────────────────────────────────
# 01_data_loading.ipynb
# ─────────────────────────────────────────────────────────────────────────────
def patch_nb01():
    path = NB_DIR / "01_data_loading.ipynb"
    nb = load(path)

    # Cell 1 — imports + config
    set_source(nb, 1, f"""\
import lasio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.transforms import blended_transform_factory
from pathlib import Path
{CONFIG_HEADER}

# ── Paths ─────────────────────────────────────────────────────────────────────
WELL_FILE = Path('..') / cfg['las_file']
TOPS_FILE = Path('..') / cfg['tops_file']

{PLOT_STYLE}""")

    # Cell 3 — LAS load + well header (robust field access)
    set_source(nb, 3, """\
las = lasio.read(WELL_FILE)

# ── Well header ───────────────────────────────────────────────────────────────
def _hval(las, key):
    try: return las.well[key].value
    except: return '—'

header_items = [
    ('Well',     _hval(las, 'WELL')),
    ('Field',    _hval(las, 'FLD')),
    ('Company',  _hval(las, 'COMP')),
    ('Start (m)',_hval(las, 'STRT')),
    ('Stop (m)', _hval(las, 'STOP')),
    ('Step (m)', _hval(las, 'STEP')),
    ('Null',     _hval(las, 'NULL')),
    ('Location', _hval(las, 'LOC')),
    ('Lat',      _hval(las, 'LATI')),
    ('Long',     _hval(las, 'LONG')),
]
print('─' * 45)
print('  WELL HEADER')
print('─' * 45)
for k, v in header_items:
    print(f'  {k:<12s}: {v}')
print('─' * 45)""")

    # Cell 7 — coverage table (add curve renaming)
    set_source(nb, 7, """\
df = las.df()
df.replace(-999.25, np.nan, inplace=True)
df.rename(columns=cfg.get('curve_map', {}), inplace=True)
df.index.name = 'DEPTH'

total = len(df)
cov_rows = []
for col in df.columns:
    valid   = df[col].dropna()
    n_valid = len(valid)
    z_top   = valid.index[0]  if n_valid else float('nan')
    z_bot   = valid.index[-1] if n_valid else float('nan')
    cov_rows.append({
        'Curve'    : col,
        'Top (m)'  : z_top,
        'Base (m)' : z_bot,
        'N valid'  : n_valid,
        'Coverage' : f"{100 * n_valid / total:.1f}%" if n_valid else '—',
        'Mean'     : f"{valid.mean():.3f}" if n_valid else '—',
        'Min'      : f"{valid.min():.3f}"  if n_valid else '—',
        'Max'      : f"{valid.max():.3f}"  if n_valid else '—',
    })

print(pd.DataFrame(cov_rows).to_string(index=False))""")

    # Cell 11 — formation tops (dynamic)
    set_source(nb, 11, """\
# ── Load picks and filter to this well ───────────────────────────────────────
all_tops = pd.read_csv(TOPS_FILE)
f1a_tops = (
    all_tops[all_tops['WELL'] == cfg['tops_well_id']]
    [['PICKS', 'DEPTH', 'TVD', 'TVDSS']]
    .sort_values('DEPTH')
    .reset_index(drop=True)
)
if not f1a_tops.empty:
    print(f"Formation tops for {cfg['tops_well_id']} ({len(f1a_tops)} picks):\\n")
    print(f"  {'Formation':<35}  {'MD (m)':>8}  {'TVD (m)':>8}  {'TVDSS (m)':>10}")
    print('  ' + '─' * 65)
    for _, row in f1a_tops.iterrows():
        print(f"  {row['PICKS']:<35}  {row['DEPTH']:>8.1f}  {row['TVD']:>8.1f}  {row['TVDSS']:>10.1f}")
else:
    print(f"No formation tops loaded for {cfg['tops_well_id']}.")
    print("Add picks to the tops CSV to enable formation annotations.")

# ── TOPS_MD: {formation_name: MD_depth} for log annotations ──────────────────
if not f1a_tops.empty:
    TOPS_MD = dict(zip(f1a_tops['PICKS'], f1a_tops['DEPTH']))
    RESERVOIR_TOP = f1a_tops.iloc[-1]['PICKS']   # deepest pick = target
else:
    TOPS_MD = {}
    RESERVOIR_TOP = None""")

    # Cell 14 — full log display (dynamic depths + well name)
    set_source(nb, 14, """\
# ── Full logging interval ─────────────────────────────────────────────────────
LOG_TOP  = cfg['log_top']  if cfg['log_top']  is not None else df.index[0]
LOG_BASE = cfg['log_base'] if cfg['log_base'] is not None else df.index[-1]

fig, axes = plot_composite_log(
    df,
    top           = LOG_TOP,
    base          = LOG_BASE,
    well_name     = cfg['tops_well_id'],
    bs_default    = 8.5,
    tops          = TOPS_MD,
    reservoir_top = RESERVOIR_TOP,
)
plt.show()""")

    # Cell 15 — zoom display (dynamic)
    set_source(nb, 15, """\
# ── Lower interval zoom (lower third of logged section) ──────────────────────
zoom_size = (LOG_BASE - LOG_TOP) / 3
fig, axes = plot_composite_log(
    df,
    top           = LOG_BASE - zoom_size,
    base          = LOG_BASE,
    well_name     = f"{cfg['tops_well_id']}  — Lower Section",
    bs_default    = 8.5,
    tops          = TOPS_MD,
    reservoir_top = RESERVOIR_TOP,
    figsize       = (16, 12),
)
plt.show()""")

    save(nb, path)


# ─────────────────────────────────────────────────────────────────────────────
# 02_temperature_pressure.ipynb
# ─────────────────────────────────────────────────────────────────────────────
def patch_nb02():
    path = NB_DIR / "02_temperature_pressure.ipynb"
    nb = load(path)

    # Cell 1 — imports + full config block
    set_source(nb, 1, f"""\
import lasio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from scipy.stats import linregress
from pathlib import Path
{CONFIG_HEADER}

# ── Paths ─────────────────────────────────────────────────────────────────────
WELL_FILE = Path('..') / cfg['las_file']
TOPS_FILE = Path('..') / cfg['tops_file']
OUT_FILE  = Path(f'../wells/{{WELL_NAME}}_computed.parquet')

# ── Well geometry (from config — update well_config.py for each well) ─────────
KB_ABOVE_MSL  = cfg['kb_above_msl']   # m  Kelly Bushing above MSL
WATER_DEPTH   = cfg['water_depth']    # m  seabed below MSL

# ── Temperature ───────────────────────────────────────────────────────────────
T_SEABED      = cfg['t_seabed']       # °C
GEOTHERM      = cfg['geotherm']       # °C/m from seabed

# ── Formation water ───────────────────────────────────────────────────────────
SALINITY_PPM  = cfg['salinity_ppm']   # ppm NaCl equivalent

# ── Pressure ──────────────────────────────────────────────────────────────────
RHO_SEAWATER  = 1.025    # g/cc
G_MPA         = 9.81e-3  # MPa per (g/cc · m)

{PLOT_STYLE}""")

    # Cell 3 — LAS load + tops filter (dynamic; TVD fallback if no tops)
    set_source(nb, 3, """\
# ── Load LAS ──────────────────────────────────────────────────────────────────
las = lasio.read(WELL_FILE)
df  = las.df()
df.replace(-999.25, np.nan, inplace=True)
df.rename(columns=cfg.get('curve_map', {}), inplace=True)
df.index.name = 'DEPTH_MD'

# ── Formation tops — depth tie-points ─────────────────────────────────────────
all_tops = pd.read_csv(TOPS_FILE)
f1a = (
    all_tops[all_tops['WELL'] == cfg['tops_well_id']]
    .sort_values('DEPTH')
    .drop_duplicates(subset='DEPTH')
    .reset_index(drop=True)
)

# TVDSS convention in file: negative = below MSL; convert to positive-downward
if not f1a.empty:
    f1a['TVDSS_ABS'] = f1a['TVDSS'].abs()

md = df.index.values

if not f1a.empty:
    df['TVD']      = np.interp(md, f1a['DEPTH'].values, f1a['TVD'].values)
    df['TVDSS_ABS'] = np.interp(md, f1a['DEPTH'].values, f1a['TVDSS_ABS'].values)
else:
    # No tops available — approximate as vertical well offset by KB
    print(f"WARNING: No formation tops for {cfg['tops_well_id']}. "
          "Using TVD ≈ MD - KB as approximation. Add tops for accuracy.")
    df['TVD']       = md - KB_ABOVE_MSL
    df['TVDSS_ABS'] = md - KB_ABOVE_MSL - WATER_DEPTH

df['DEPTH_BELOW_SEABED'] = np.maximum(df['TVDSS_ABS'] - WATER_DEPTH, 0.0)

# ── Helper ─────────────────────────────────────────────────────────────────────
def nearest_idx(df, md):
    return df.index[np.argmin(np.abs(df.index.values - md))]

# ── Quick sanity check ────────────────────────────────────────────────────────
print(f"KB above MSL          : {KB_ABOVE_MSL:.1f} m")
print(f"Seabed depth (MSL)    : {WATER_DEPTH:.1f} m")
print(f"MD range              : {md.min():.0f}–{md.max():.0f} m")
print(f"TVD range             : {df['TVD'].min():.0f}–{df['TVD'].max():.0f} m")
print(f"TVDss range (abs)     : {df['TVDSS_ABS'].min():.0f}–{df['TVDSS_ABS'].max():.0f} m")
if not f1a.empty:
    print()
    print("Formation tops used for MD→TVD conversion:")
    print(f"  {'Formation':<35} {'MD':>8} {'TVD':>8} {'TVDss':>8}")
    print("  " + "─"*62)
    for _, r in f1a.iterrows():
        print(f"  {r['PICKS']:<35} {r['DEPTH']:>8.1f} {r['TVD']:>8.1f} {-r['TVDSS_ABS']:>8.1f}")""")

    # Cell 8 — TEMP log + TOPS_MD (dynamic)
    old_src8 = "".join(nb["cells"][8]["source"])
    new_src8 = old_src8.replace(
        "TOPS_MD = {\n    'Ty Fm'       : 2621.5, 'Shetland GP' : 2770.6, 'Hod Fm'      : 2987.0,\n"
        "    'Draupne Fm'  : 3358.0, 'Heather Fm'  : 3429.4, 'Hugin Fm'    : 3435.0,\n"
        "    'Sleipner Fm' : 3500.2, 'Skagerrak Fm': 3543.7, 'Smith Bank Fm': 3608.0,\n}",
        "# ── TOPS_MD from CSV ──────────────────────────────────────────────────────────\n"
        "if not f1a.empty:\n"
        "    TOPS_MD = dict(zip(f1a['PICKS'], f1a['DEPTH']))\n"
        "else:\n"
        "    TOPS_MD = {}"
    )
    nb["cells"][8]["source"] = new_src8.split("\n")
    nb["cells"][8]["source"] = [l + "\n" for l in new_src8.splitlines()[:-1]] + [new_src8.splitlines()[-1]]
    nb["cells"][8]["outputs"] = []
    nb["cells"][8]["execution_count"] = None

    # Cell 15 — display: dynamic LOG_TOP/BASE + robust TOPS_TVDSS
    old_src15 = "".join(nb["cells"][15]["source"])
    new_src15 = old_src15.replace(
        "# Restrict to the logging interval for display\nLOG_TOP  = 2585   # MD\nLOG_BASE = 3680   # MD\n",
        "# Restrict to the logging interval for display\n"
        "LOG_TOP  = cfg['log_top']  if cfg['log_top']  is not None else int(df.index[0])\n"
        "LOG_BASE = cfg['log_base'] if cfg['log_base'] is not None else int(df.index[-1])\n"
    ).replace(
        "RESERVOIR_TOP = 'Hugin Fm'",
        "RESERVOIR_TOP = list(TOPS_MD.keys())[-1] if TOPS_MD else None"
    ).replace(
        "fig.suptitle('15/9-F-1 A (Volve) — Temperature, Rw & Pressure Profiles',",
        "fig.suptitle(f\"{cfg['tops_well_id']} — Temperature, Rw & Pressure Profiles\","
    )
    nb["cells"][15]["source"] = [l + "\n" for l in new_src15.splitlines()[:-1]] + [new_src15.splitlines()[-1]]
    nb["cells"][15]["outputs"] = []
    nb["cells"][15]["execution_count"] = None

    save(nb, path)


# ─────────────────────────────────────────────────────────────────────────────
# 03_caliper_qc.ipynb  (has cell IDs: cell-1, cell-3, cell-11)
# ─────────────────────────────────────────────────────────────────────────────
def patch_nb03():
    path = NB_DIR / "03_caliper_qc.ipynb"
    nb = load(path)

    cells_by_id = {c["id"]: (i, c) for i, c in enumerate(nb["cells"]) if "id" in c}

    # cell-1: imports + config
    idx, _ = cells_by_id["cell-1"]
    set_source(nb, idx, f"""\
import lasio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as mpatches
from matplotlib.transforms import blended_transform_factory
from pathlib import Path
{CONFIG_HEADER}

# ── Paths ─────────────────────────────────────────────────────────────────────
WELL_FILE    = Path('..') / cfg['las_file']
TOPS_FILE    = Path('..') / cfg['tops_file']
COMPUTED_IN  = Path(f'../wells/{{WELL_NAME}}_computed.parquet')
COMPUTED_OUT = Path(f'../wells/{{WELL_NAME}}_flags.parquet')

# ── Hole condition thresholds ──────────────────────────────────────────────────
ENLARGED_THRESH_IN = 0.5   # inches over BS — mild
BAD_HOLE_THRESH_IN = 1.0   # inches over BS — severe, affects density
DRHO_THRESH        = 0.10  # g/cc

{PLOT_STYLE}""")

    # cell-3: LAS load (add curve renaming + dynamic tops filter)
    idx, cell3 = cells_by_id["cell-3"]
    src = "".join(cell3["source"])
    src = src.replace(
        "df.replace(-999.25, np.nan, inplace=True)\ndf.index.name = 'DEPTH_MD'\n",
        "df.replace(-999.25, np.nan, inplace=True)\ndf.rename(columns=cfg.get('curve_map', {}), inplace=True)\ndf.index.name = 'DEPTH_MD'\n"
    ).replace(
        "all_tops[all_tops['WELL'] == 'NO 15/9-F-1 A']",
        "all_tops[all_tops['WELL'] == cfg['tops_well_id']]"
    )
    nb["cells"][idx]["source"] = [l + "\n" for l in src.splitlines()[:-1]] + [src.splitlines()[-1]]
    nb["cells"][idx]["outputs"] = []
    nb["cells"][idx]["execution_count"] = None

    # cell-11: dynamic TOPS_MD
    idx, _ = cells_by_id["cell-11"]
    old = "".join(nb["cells"][idx]["source"])
    # Replace the hardcoded TOPS_MD block
    tops_block_start = old.find("TOPS_MD = {")
    tops_block_end   = old.find("}", tops_block_start) + 1
    old_tops_block   = old[tops_block_start:tops_block_end]
    new_tops_block   = (
        "if not f1a.empty:\n"
        "    TOPS_MD = dict(zip(f1a['PICKS'], f1a['DEPTH']))\n"
        "    RESERVOIR_TOP = f1a.iloc[-1]['PICKS']\n"
        "else:\n"
        "    TOPS_MD = {}\n"
        "    RESERVOIR_TOP = None"
    )
    new = old.replace(old_tops_block, new_tops_block)
    # Also remove the hardcoded RESERVOIR_TOP line that follows
    new = new.replace("\nRESERVOIR_TOP = 'Hugin Fm'\n", "\n")
    nb["cells"][idx]["source"] = [l + "\n" for l in new.splitlines()[:-1]] + [new.splitlines()[-1]]
    nb["cells"][idx]["outputs"] = []
    nb["cells"][idx]["execution_count"] = None

    save(nb, path)


# ─────────────────────────────────────────────────────────────────────────────
# 04_depth_shift.ipynb  (cell-1, cell-3)
# ─────────────────────────────────────────────────────────────────────────────
def patch_nb04():
    path = NB_DIR / "04_depth_shift.ipynb"
    nb = load(path)
    cells_by_id = {c["id"]: (i, c) for i, c in enumerate(nb["cells"]) if "id" in c}

    idx, _ = cells_by_id["cell-1"]
    set_source(nb, idx, f"""\
import lasio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.transforms import blended_transform_factory
from scipy import signal
from scipy.ndimage import uniform_filter1d
from pathlib import Path
{CONFIG_HEADER}

# ── Paths ─────────────────────────────────────────────────────────────────────
WELL_FILE   = Path('..') / cfg['las_file']
TOPS_FILE   = Path('..') / cfg['tops_file']
COMPUTED_IN = Path(f'../wells/{{WELL_NAME}}_computed.parquet')
FLAGS_IN    = Path(f'../wells/{{WELL_NAME}}_flags.parquet')
OUT_FILE    = Path(f'../wells/{{WELL_NAME}}_depthshift.parquet')

# ── Gardner relation constants (clastic sediments) ────────────────────────────
GARDNER_A = 0.31   # RHOB [g/cc] = A × Vp [m/s] ^ B
GARDNER_B = 0.25

{PLOT_STYLE}""")

    idx, cell3 = cells_by_id["cell-3"]
    src = "".join(cell3["source"])
    src = src.replace(
        "df.replace(-999.25, np.nan, inplace=True)\ndf.index.name = 'DEPTH_MD'\n",
        "df.replace(-999.25, np.nan, inplace=True)\ndf.rename(columns=cfg.get('curve_map', {}), inplace=True)\ndf.index.name = 'DEPTH_MD'\n"
    ).replace(
        "`WELL` == 'NO 15/9-F-1 A'",
        "`WELL` == cfg['tops_well_id']"
    )
    nb["cells"][idx]["source"] = [l + "\n" for l in src.splitlines()[:-1]] + [src.splitlines()[-1]]
    nb["cells"][idx]["outputs"] = []
    nb["cells"][idx]["execution_count"] = None

    save(nb, path)


# ─────────────────────────────────────────────────────────────────────────────
# 05_petrophysics_review.ipynb  (cell-1, cell-3)
# ─────────────────────────────────────────────────────────────────────────────
def patch_nb05():
    path = NB_DIR / "05_petrophysics_review.ipynb"
    nb = load(path)
    cells_by_id = {c["id"]: (i, c) for i, c in enumerate(nb["cells"]) if "id" in c}

    idx, _ = cells_by_id["cell-1"]
    set_source(nb, idx, f"""\
import lasio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as mpatches
from matplotlib.transforms import blended_transform_factory
from pathlib import Path
{CONFIG_HEADER}

# ── Paths ─────────────────────────────────────────────────────────────────────
WELL_FILE    = Path('..') / cfg['las_file']
TOPS_FILE    = Path('..') / cfg['tops_file']
COMPUTED_IN  = Path(f'../wells/{{WELL_NAME}}_computed.parquet')
FLAGS_IN     = Path(f'../wells/{{WELL_NAME}}_flags.parquet')
DS_IN        = Path(f'../wells/{{WELL_NAME}}_depthshift.parquet')

# ── Archie parameters (standard starting point) ────────────────────────────────
ARCHIE_A  = 1.0   # tortuosity factor
ARCHIE_M  = 2.0   # cementation exponent
ARCHIE_N  = 2.0   # saturation exponent

{PLOT_STYLE}""")

    idx, cell3 = cells_by_id["cell-3"]
    src = "".join(cell3["source"])
    src = src.replace(
        "df.replace(-999.25, np.nan, inplace=True)\ndf.index.name = 'DEPTH_MD'\n",
        "df.replace(-999.25, np.nan, inplace=True)\ndf.rename(columns=cfg.get('curve_map', {}), inplace=True)\ndf.index.name = 'DEPTH_MD'\n"
    ).replace(
        "`WELL` == 'NO 15/9-F-1 A'",
        "`WELL` == cfg['tops_well_id']"
    )
    nb["cells"][idx]["source"] = [l + "\n" for l in src.splitlines()[:-1]] + [src.splitlines()[-1]]
    nb["cells"][idx]["outputs"] = []
    nb["cells"][idx]["execution_count"] = None

    save(nb, path)


# ─────────────────────────────────────────────────────────────────────────────
# 06_density_editing.ipynb  (cell-1, cell-3)
# ─────────────────────────────────────────────────────────────────────────────
def patch_nb06():
    path = NB_DIR / "06_density_editing.ipynb"
    nb = load(path)
    cells_by_id = {c["id"]: (i, c) for i, c in enumerate(nb["cells"]) if "id" in c}

    idx, _ = cells_by_id["cell-1"]
    set_source(nb, idx, f"""\
import lasio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.transforms import blended_transform_factory
from pathlib import Path
{CONFIG_HEADER}

# ── Paths ─────────────────────────────────────────────────────────────────────
WELL_FILE    = Path('..') / cfg['las_file']
TOPS_FILE    = Path('..') / cfg['tops_file']
COMPUTED_IN  = Path(f'../wells/{{WELL_NAME}}_computed.parquet')
FLAGS_IN     = Path(f'../wells/{{WELL_NAME}}_flags.parquet')
DS_IN        = Path(f'../wells/{{WELL_NAME}}_depthshift.parquet')
OUT_FILE     = Path(f'../wells/{{WELL_NAME}}_rhob_ok.parquet')

# ── Editing thresholds ─────────────────────────────────────────────────────────
DRHO_EDIT_THRESH = 0.15   # g/cc — above this, prefer Gardner infill over raw RHOB
RHOB_COAL_MAX    = 1.80   # g/cc — below this, flag as coal
RHOB_CARBONATE   = 2.72   # g/cc — above this, flag as tight carbonate

# ── Gardner constants ──────────────────────────────────────────────────────────
GARDNER_A = 0.31
GARDNER_B = 0.25

{PLOT_STYLE}""")

    # cell-3: add renaming + dynamic LOG_TOP/BASE + dynamic TOPS_MD
    idx, cell3 = cells_by_id["cell-3"]
    src = "".join(cell3["source"])
    src = src.replace(
        "df.replace(-999.25, np.nan, inplace=True)\ndf.index.name = 'DEPTH_MD'\n",
        "df.replace(-999.25, np.nan, inplace=True)\ndf.rename(columns=cfg.get('curve_map', {}), inplace=True)\ndf.index.name = 'DEPTH_MD'\n"
    ).replace(
        "LOG_TOP, LOG_BASE = 2605, 3680\nsub = df.loc[LOG_TOP:LOG_BASE].copy()\n",
        "LOG_TOP  = cfg['log_top']  if cfg['log_top']  is not None else df.index[0]\n"
        "LOG_BASE = cfg['log_base'] if cfg['log_base'] is not None else df.index[-1]\n"
        "sub = df.loc[LOG_TOP:LOG_BASE].copy()\n"
    ).replace(
        "TOPS_MD = {\n"
        "    'Ty Fm': 2621.5, 'Shetland GP': 2770.6, 'Hod Fm': 2987.0,\n"
        "    'Draupne Fm': 3358.0, 'Heather Fm': 3429.4, 'Hugin Fm': 3435.0,\n"
        "    'Sleipner Fm': 3500.2, 'Skagerrak Fm': 3543.7, 'Smith Bank Fm': 3608.0,\n}",
        "all_tops = pd.read_csv(TOPS_FILE)\n"
        "f1a = all_tops[all_tops['WELL'] == cfg['tops_well_id']].sort_values('DEPTH').reset_index(drop=True)\n"
        "TOPS_MD = dict(zip(f1a['PICKS'], f1a['DEPTH'])) if not f1a.empty else {}"
    )
    nb["cells"][idx]["source"] = [l + "\n" for l in src.splitlines()[:-1]] + [src.splitlines()[-1]]
    nb["cells"][idx]["outputs"] = []
    nb["cells"][idx]["execution_count"] = None

    save(nb, path)


# ─────────────────────────────────────────────────────────────────────────────
# 07_elastic_qc.ipynb  (cell-1, cell-3)
# ─────────────────────────────────────────────────────────────────────────────
def patch_nb07():
    path = NB_DIR / "07_elastic_qc.ipynb"
    nb = load(path)
    cells_by_id = {c["id"]: (i, c) for i, c in enumerate(nb["cells"]) if "id" in c}

    idx, _ = cells_by_id["cell-1"]
    set_source(nb, idx, f"""\
import lasio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.transforms import blended_transform_factory
from pathlib import Path
{CONFIG_HEADER}

# ── Paths ─────────────────────────────────────────────────────────────────────
WELL_FILE    = Path('..') / cfg['las_file']
TOPS_FILE    = Path('..') / cfg['tops_file']
COMPUTED_IN  = Path(f'../wells/{{WELL_NAME}}_computed.parquet')
FLAGS_IN     = Path(f'../wells/{{WELL_NAME}}_flags.parquet')
DS_IN        = Path(f'../wells/{{WELL_NAME}}_depthshift.parquet')
RHOB_OK_IN   = Path(f'../wells/{{WELL_NAME}}_rhob_ok.parquet')
OUT_FILE     = Path(f'../wells/{{WELL_NAME}}_elastic.parquet')

# ── Physical bounds for Vp/Vs QC ──────────────────────────────────────────────
VP_MIN   = 1500.0   # m/s
VP_MAX   = 6500.0
VS_MIN   =  700.0
VS_MAX   = 4000.0
VPVS_MIN =    1.35
VPVS_MAX =    4.0

# ── Castagna mudrock line: Vs = A*Vp + B (m/s) ───────────────────────────────
CASTAGNA_A =  0.8042
CASTAGNA_B = -855.9

{PLOT_STYLE}""")

    idx, cell3 = cells_by_id["cell-3"]
    src = "".join(cell3["source"])
    src = src.replace(
        "df.replace(-999.25, np.nan, inplace=True)\ndf.index.name = 'DEPTH_MD'\n",
        "df.replace(-999.25, np.nan, inplace=True)\ndf.rename(columns=cfg.get('curve_map', {}), inplace=True)\ndf.index.name = 'DEPTH_MD'\n"
    ).replace(
        "`WELL` == 'NO 15/9-F-1 A'",
        "`WELL` == cfg['tops_well_id']"
    ).replace(
        "LOG_TOP, LOG_BASE = 2605, 3680\n",
        "LOG_TOP  = cfg['log_top']  if cfg['log_top']  is not None else df.index[0]\n"
        "LOG_BASE = cfg['log_base'] if cfg['log_base'] is not None else df.index[-1]\n"
    )
    nb["cells"][idx]["source"] = [l + "\n" for l in src.splitlines()[:-1]] + [src.splitlines()[-1]]
    nb["cells"][idx]["outputs"] = []
    nb["cells"][idx]["execution_count"] = None

    save(nb, path)


# ─────────────────────────────────────────────────────────────────────────────
# 08_faust_vp.ipynb  (cell-1, cell-3)
# ─────────────────────────────────────────────────────────────────────────────
def patch_nb08():
    path = NB_DIR / "08_faust_vp.ipynb"
    nb = load(path)
    cells_by_id = {c["id"]: (i, c) for i, c in enumerate(nb["cells"]) if "id" in c}

    idx, _ = cells_by_id["cell-1"]
    set_source(nb, idx, f"""\
import lasio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as mpatches
from matplotlib.transforms import blended_transform_factory
from scipy import stats
from pathlib import Path
{CONFIG_HEADER}

# ── Paths ─────────────────────────────────────────────────────────────────────
WELL_FILE    = Path('..') / cfg['las_file']
TOPS_FILE    = Path('..') / cfg['tops_file']
COMPUTED_IN  = Path(f'../wells/{{WELL_NAME}}_computed.parquet')
FLAGS_IN     = Path(f'../wells/{{WELL_NAME}}_flags.parquet')
ELASTIC_IN   = Path(f'../wells/{{WELL_NAME}}_elastic.parquet')
RHOB_OK_IN   = Path(f'../wells/{{WELL_NAME}}_rhob_ok.parquet')
OUT_FILE     = Path(f'../wells/{{WELL_NAME}}_faust.parquet')

# ── Faust calibration domain ───────────────────────────────────────────────────
RT_CALIB_MAX = 10.0    # Ω·m — exclude HC-elevated resistivity from calibration
RT_CALIB_MIN =  0.2    # Ω·m — exclude conductive artefacts

{PLOT_STYLE}""")

    idx, cell3 = cells_by_id["cell-3"]
    src = "".join(cell3["source"])
    src = src.replace(
        "df.replace(-999.25, np.nan, inplace=True)\ndf.index.name = 'DEPTH_MD'\n",
        "df.replace(-999.25, np.nan, inplace=True)\ndf.rename(columns=cfg.get('curve_map', {}), inplace=True)\ndf.index.name = 'DEPTH_MD'\n"
    ).replace(
        "`WELL` == 'NO 15/9-F-1 A'",
        "`WELL` == cfg['tops_well_id']"
    ).replace(
        "LOG_TOP, LOG_BASE = 2605, 3680\n",
        "LOG_TOP  = cfg['log_top']  if cfg['log_top']  is not None else df.index[0]\n"
        "LOG_BASE = cfg['log_base'] if cfg['log_base'] is not None else df.index[-1]\n"
    ).replace(
        "TOPS_MD = {\n"
        "    'Ty Fm': 2621.5, 'Shetland GP': 2770.6, 'Hod Fm': 2987.0,\n"
        "    'Draupne Fm': 3358.0, 'Heather Fm': 3429.4, 'Hugin Fm': 3435.0,\n"
        "    'Sleipner Fm': 3500.2, 'Skagerrak Fm': 3543.7,\n"
        "    'Smith Bank Fm': 3608.0,\n}",
        "all_tops = pd.read_csv(TOPS_FILE)\n"
        "f1a_tops = all_tops[all_tops['WELL'] == cfg['tops_well_id']].sort_values('DEPTH').reset_index(drop=True)\n"
        "TOPS_MD = dict(zip(f1a_tops['PICKS'], f1a_tops['DEPTH'])) if not f1a_tops.empty else {}"
    )
    nb["cells"][idx]["source"] = [l + "\n" for l in src.splitlines()[:-1]] + [src.splitlines()[-1]]
    nb["cells"][idx]["outputs"] = []
    nb["cells"][idx]["execution_count"] = None

    save(nb, path)


# ─────────────────────────────────────────────────────────────────────────────
# Run all patches
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Patching notebooks for multi-well support...\n")
    patch_nb01()
    patch_nb02()
    patch_nb03()
    patch_nb04()
    patch_nb05()
    patch_nb06()
    patch_nb07()
    patch_nb08()
    print("\nDone. Set WELL_NAME in each notebook's first code cell to switch wells.")
    print("Available well keys: 15_9-F-1A | 65074-2S | 65077-1 | 65077-14S | 65077-15S")
