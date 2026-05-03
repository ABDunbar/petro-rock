# petro-rock

Notebook-driven wireline log conditioning and rock-physics preparation for
Volve and Dvalin wells. The current workflow is exploratory, but the notebooks
already form a staged pipeline with shared well configuration in
`well_config.py` and generated parquet artifacts in `wells/`.

## Project Structure

- `notebooks/` - numbered analysis notebooks. These are the primary workflow.
- `well_config.py` - well definitions, curve mnemonic maps, QC constants, tops
  loading, and plot style.
- `wells/` - raw LAS files, formation tops, well reports, generated parquet
  outputs, and processed LAS exports.
- `scripts/` - utility scripts. `check_inputs.py` validates configured inputs
  and generated artifact lineage without editing files.
- `reference/` - reference PDF reports.
- `docs/superpowers/` - design notes and implementation plans from prior work.
- `Log_Conditioning_Workflow.md` - conceptual log-conditioning workflow.
- `pyproject.toml` and `uv.lock` - Python environment metadata.

## Current Notebook Order

Run notebooks in numeric order for one active well. The active well is selected
by `ACTIVE_WELL` in `well_config.py`, with optional per-notebook overrides.

| Notebook | Purpose | Main output |
| --- | --- | --- |
| `01_data_loading.ipynb` | LAS inventory, curve coverage, tops display | no persistent output |
| `02_temperature_pressure.ipynb` | MD to TVD/TVDSS, temperature, Rw, pressure | `{WELL}_computed.parquet` |
| `03_caliper_qc.ipynb` | caliper/DRHO hole-condition flags | `{WELL}_flags.parquet` |
| `04_depth_shift.ipynb` | sonic-density alignment and shifted sonic curves | `{WELL}_depthshift.parquet` |
| `05_petrophysics_review.ipynb` | petrophysical QC crossplots and summaries | no persistent output |
| `06_faust_vp.ipynb` | Faust Vp calibration and Vp infill | `{WELL}_faust.parquet` |
| `07_density_editing.ipynb` | density editing and Gardner infill | `{WELL}_rhob_ok.parquet` |
| `08_elastic_qc.ipynb` | Vp/Vs QC, final elastic curves, LAS export | `{WELL}_elastic.parquet`, `{WELL}_processed.las` |
| `09_rock_physics.ipynb` | contact-cement Vs model calibration | `{WELL}_rockphysics.parquet` |

The conceptual workflow document contains a broader 12-phase target workflow.
The notebook numbering is currently the operational source of truth.

## Data Lineage

Generated artifacts are depth-indexed by `DEPTH_MD` in metres.

```text
raw LAS + tops
  -> 02 computed: TVD, TVDSS_ABS, DEPTH_BELOW_SEABED, TEMP, RW, P_OB, PORE_PRESS, DIFF_PRESS
  -> 03 flags: ENLARGED_HOLE, BAD_HOLE_FLAG, DRHO_SUSPECT, DENSITY_SUSPECT
  -> 04 depthshift: DT/DTS shifted curves, VP/VS, DEPTH_SHIFT_M
  -> 06 faust: VP_FAUST, VP_COMPOSITE, VP_SOURCE, C_FAUST
  -> 07 rhob_ok: RHOB_OK, Gardner density helpers, edit/lithology flags
  -> 08 elastic: VP_OK, VS_OK, VPVS, Castagna helpers, elastic QC flags
  -> 09 rockphysics: VS_RPM, PHI_C_CEMENT, K_MIN, G_MIN
```

## Canonical Conventions

- **MD**: LAS depth index, standardized as `DEPTH_MD`, metres measured depth.
- **Curve names**: canonical mnemonics are applied through `cfg["curve_map"]`
  from `well_config.py`. Dvalin LAS curves such as `AC`, `ACS`, `DEN`,
  `DENC`, and `RDEP` are mapped to `DT`, `DTS`, `RHOB`, `DRHO`, and `RT`.
- **Sonic units**: current LAS files store `DT`/`DTS` or `AC`/`ACS` in
  microseconds per foot. Velocity conversion is `1e6 / slowness * 0.3048`.
- **Density**: `RHOB`/`DEN` is g/cc (`g/cm3` in LAS headers).
- **Resistivity**: `RT`/`RDEP` is ohm-m.
- **Caliper and bit size**: inches.
- **KB/RKB and water depth**: configured per well in `well_config.py`.
- **Formation tops**: loaded through `load_tops()` in `well_config.py`. Tops
  MD is used for log annotation and formation assignment. Petrel `Z` is read
  as signed TVDSS and converted in notebook 02 to positive-down `TVDSS_ABS`.
- **MD to TVD/TVDSS**: notebook 02 currently creates the canonical persisted
  conversion columns in `{WELL}_computed.parquet`.
- **Temperature and pressure**: notebook 02 outputs are canonical for the
  current notebooks. Pore pressure is hydrostatic unless a future RFT/MDT input
  overrides it.
- **Faust depth `Z`**: notebook 06 currently uses `TVDSS_ABS` converted to feet.
  Treat this as an implementation convention to QC before changing calculations.
- **Checkshots, replacement velocity, and seismic time-depth**: no canonical
  source exists yet. Tops files may contain TWT fields, but the notebooks do not
  currently implement a checkshot or seismic tie workflow.

## Input And Unit QC

Run the read-only checker from the repository root:

```bash
uv run python scripts/check_inputs.py
```

Useful options:

```bash
uv run python scripts/check_inputs.py --well 65077-15S
uv run python scripts/check_inputs.py --strict
```

The checker validates configured LAS/tops paths, LAS curve units after mnemonic
mapping, tops depth consistency, generated parquet schemas, index alignment, and
artifact freshness. It prints `OK`, `WARN`, and `FAIL` messages and does not
write or modify any project files.

## Safe First Refactor Targets

Good early Codex tasks are:

- keep this README and project map current;
- maintain `scripts/check_inputs.py`;
- add lightweight regression checks for parquet schemas and summary statistics;
- extract shared helpers for LAS loading, path construction, formation
  assignment, nearest-depth lookup, and DT/DTS velocity conversion;
- defer calculation refactors until old/new parquet outputs can be compared.
