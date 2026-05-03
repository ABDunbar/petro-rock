"""Read-only input and artifact checks for the petro-rock notebook workflow."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from well_config import WELLS, get_cfg, load_tops

ARTIFACT_SCHEMAS = {
    "computed": (
        "TVD",
        "TVDSS_ABS",
        "DEPTH_BELOW_SEABED",
        "TEMP",
        "RW",
        "P_OB",
        "PORE_PRESS",
        "DIFF_PRESS",
    ),
    "flags": (
        "ENLARGED_HOLE",
        "BAD_HOLE_FLAG",
        "DRHO_SUSPECT",
        "DENSITY_SUSPECT",
    ),
    "depthshift": (
        "DT_SHIFT",
        "DTS_SHIFT",
        "VP",
        "VS",
        "VP_SHIFT",
        "VS_SHIFT",
        "DEPTH_SHIFT_M",
    ),
    "faust": (
        "VP_FAUST",
        "VP_COMPOSITE",
        "VP_SOURCE",
        "C_FAUST",
    ),
    "rhob_ok": (
        "RHOB_OK",
        "RHOB_GARD",
        "RHOB_GARD_CORR",
        "RHOB_RESID",
        "EDIT_FLAG",
        "COAL_FLAG",
        "CALC_FLAG",
    ),
    "elastic": (
        "VP",
        "VS",
        "VP_OK",
        "VS_OK",
        "VPVS",
        "VS_CASTAGNA",
        "VS_RESID",
        "CYCLE_SKIP_VP",
        "CYCLE_SKIP_VS",
        "VPVS_FLAG",
        "ELASTIC_EDIT",
    ),
    "rockphysics": (
        "VS_RPM",
        "PHI_C_CEMENT",
        "K_MIN",
        "G_MIN",
    ),
}


@dataclass(frozen=True)
class CheckResult:
    status: str
    name: str
    detail: str


def _repo_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def _format_result(result: CheckResult) -> str:
    return f"[{result.status}] {result.name:<28} {result.detail}"


def check_configured_inputs(well_name: str) -> list[CheckResult]:
    """Validate configured LAS and tops inputs for one well."""
    cfg = get_cfg(well_name)
    results: list[CheckResult] = []

    las_path = _repo_path(cfg["las_file"])
    if las_path.exists():
        results.append(CheckResult("OK", f"LAS {well_name}", str(las_path.relative_to(ROOT))))
    else:
        results.append(CheckResult("FAIL", f"LAS {well_name}", f"missing: {las_path}"))

    tops_path = _repo_path(cfg["tops_file"])
    if not tops_path.exists():
        results.append(CheckResult("FAIL", f"tops {well_name}", f"missing: {tops_path}"))
        return results

    try:
        tops = load_tops(tops_path, cfg["tops_well_id"])
    except Exception as exc:  # pragma: no cover - exact parser errors are data-dependent.
        results.append(CheckResult("FAIL", f"tops {well_name}", f"{type(exc).__name__}: {exc}"))
        return results

    if tops.empty:
        results.append(CheckResult("FAIL", f"tops {well_name}", "no rows for configured tops_well_id"))
    elif "DEPTH" not in tops.columns:
        results.append(CheckResult("FAIL", f"tops {well_name}", "missing DEPTH column"))
    elif tops["DEPTH"].isna().all():
        results.append(CheckResult("FAIL", f"tops {well_name}", "all DEPTH values are null"))
    else:
        depth = tops["DEPTH"].dropna()
        results.append(
            CheckResult(
                "OK",
                f"tops {well_name}",
                f"rows={len(tops)}, depth={depth.min():.2f}-{depth.max():.2f} m",
            )
        )

    return results


def check_artifact_schema(
    path: str | Path,
    required_columns: Iterable[str],
    *,
    strict_missing: bool = False,
) -> CheckResult:
    """Validate one parquet artifact's depth index and required columns."""
    artifact = _repo_path(path)
    display = str(artifact.relative_to(ROOT)) if artifact.is_relative_to(ROOT) else str(artifact)

    if not artifact.exists():
        status = "FAIL" if strict_missing else "WARN"
        return CheckResult(status, display, "missing artifact")

    try:
        df = pd.read_parquet(artifact)
    except Exception as exc:
        return CheckResult("FAIL", display, f"read error: {type(exc).__name__}: {exc}")

    problems: list[str] = []
    if df.index.name != "DEPTH_MD":
        problems.append(f"index={df.index.name!r}, expected 'DEPTH_MD'")
    if len(df.index) > 1 and not df.index.is_monotonic_increasing:
        problems.append("DEPTH_MD index is not monotonic increasing")

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        problems.append(f"missing columns: {', '.join(missing)}")

    if problems:
        return CheckResult("FAIL", display, "; ".join(problems))

    return CheckResult("OK", display, f"rows={len(df)}, index=DEPTH_MD")


def check_artifacts(well_name: str, *, strict_missing: bool = False) -> list[CheckResult]:
    results = []
    for stage, columns in ARTIFACT_SCHEMAS.items():
        path = Path("wells") / f"{well_name}_{stage}.parquet"
        results.append(check_artifact_schema(path, columns, strict_missing=strict_missing))
    return results


def run_checks(well_names: Iterable[str], *, strict: bool = False) -> list[CheckResult]:
    results: list[CheckResult] = []
    for well_name in well_names:
        results.extend(check_configured_inputs(well_name))
        results.extend(check_artifacts(well_name, strict_missing=strict))
    return results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--well",
        action="append",
        choices=sorted(WELLS),
        help="Well name to check. Repeat for multiple wells. Defaults to all configured wells.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat missing generated artifacts as FAIL instead of WARN.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    well_names = args.well or sorted(WELLS)
    results = run_checks(well_names, strict=args.strict)

    for result in results:
        print(_format_result(result))

    failures = [r for r in results if r.status == "FAIL"]
    warnings = [r for r in results if r.status == "WARN"]
    print()
    print(f"{len(results)} checks: {len(failures)} FAIL, {len(warnings)} WARN")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
