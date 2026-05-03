from pathlib import Path
import subprocess
import sys
import tomllib

import pandas as pd

from scripts import check_inputs


ROOT = Path(__file__).resolve().parents[1]


def test_artifact_schemas_capture_notebook_lineage():
    assert check_inputs.ARTIFACT_SCHEMAS["computed"] == (
        "TVD",
        "TVDSS_ABS",
        "DEPTH_BELOW_SEABED",
        "TEMP",
        "RW",
        "P_OB",
        "PORE_PRESS",
        "DIFF_PRESS",
    )
    assert "VP_OK" in check_inputs.ARTIFACT_SCHEMAS["elastic"]
    assert "VS_RPM" in check_inputs.ARTIFACT_SCHEMAS["rockphysics"]


def test_check_configured_inputs_pass_for_active_well():
    results = check_inputs.check_configured_inputs("65077-15S")

    failed = [r for r in results if r.status == "FAIL"]

    assert failed == []
    assert any(r.name == "LAS 65077-15S" and r.status == "OK" for r in results)
    assert any(r.name == "tops 65077-15S" and r.status == "OK" for r in results)


def test_existing_artifact_schema_passes_for_computed_stage():
    result = check_inputs.check_artifact_schema(
        Path("wells/65077-15S_computed.parquet"),
        check_inputs.ARTIFACT_SCHEMAS["computed"],
    )

    assert result.status == "OK"
    assert "rows=" in result.detail
    assert "index=DEPTH_MD" in result.detail


def test_missing_artifact_warns_unless_strict(tmp_path):
    missing = tmp_path / "missing.parquet"

    relaxed = check_inputs.check_artifact_schema(
        missing,
        ("DEPTH_MD",),
        strict_missing=False,
    )
    strict = check_inputs.check_artifact_schema(
        missing,
        ("DEPTH_MD",),
        strict_missing=True,
    )

    assert relaxed.status == "WARN"
    assert strict.status == "FAIL"


def test_artifact_schema_reports_missing_columns(tmp_path):
    artifact = tmp_path / "bad.parquet"
    df = pd.DataFrame({"TVD": [100.0, 101.0]}, index=pd.Index([1.0, 2.0], name="DEPTH_MD"))
    df.to_parquet(artifact)

    result = check_inputs.check_artifact_schema(
        artifact,
        ("TVD", "TEMP"),
    )

    assert result.status == "FAIL"
    assert "missing columns: TEMP" in result.detail


def test_cli_runs_from_repo_root():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_inputs.py",
            "--well",
            "65077-15S",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0
    assert "[OK] LAS 65077-15S" in completed.stdout


def test_runtime_dependencies_include_notebook_imports():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependencies = set(pyproject["project"]["dependencies"])

    assert "lasio>=0.32" in dependencies
