import json
from pathlib import Path

from backend.leadmap.geography.cli import run_import

FIXTURE = Path(__file__).parent / "fixtures" / "ireland_boundaries_sample.geojson"


def _arguments(tmp_path: Path) -> list[str]:
    return [
        str(FIXTURE),
        "--artifact-directory",
        str(tmp_path),
        "--dataset-title",
        "Local Authorities 2026",
        "--publisher",
        "Tailte Éireann",
        "--licence",
        "CC BY 4.0",
        "--edition-year",
        "2026",
        "--source-url",
        "https://example.invalid/ireland.geojson",
        "--retrieved-at",
        "2026-07-21T07:00:00+00:00",
        "--id-field",
        "boundary_id",
        "--name-field",
        "name",
        "--expected-feature-count",
        "2",
    ]


def test_imports_and_reuses_valid_artifact(
    tmp_path: Path,
    capsys: object,
) -> None:
    assert run_import(_arguments(tmp_path)) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["created"] is True
    assert first["feature_count"] == 2
    assert Path(first["artifact_path"]).is_file()

    assert run_import(_arguments(tmp_path)) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["created"] is False
    assert second["checksum_sha256"] == first["checksum_sha256"]


def test_returns_failure_for_missing_source(
    tmp_path: Path,
    capsys: object,
) -> None:
    arguments = _arguments(tmp_path)
    arguments[0] = str(tmp_path / "missing.geojson")

    assert run_import(arguments) == 1
    assert "Geography import failed" in capsys.readouterr().err
