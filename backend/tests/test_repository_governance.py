from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_engineering_governance_files_exist() -> None:
    required = [
        ROOT / "AGENTS.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / ".github" / "pull_request_template.md",
        ROOT / "docs" / "development" / "SCOPE_LEDGER_TEMPLATE.md",
        ROOT / "docs" / "development" / "ENGINEERING_OPERATING_MODEL.md",
    ]

    assert all(path.is_file() for path in required)


def test_pull_request_template_requires_exact_head_and_completion_states() -> None:
    template = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")

    assert "Exact PR head SHA tested" in template
    assert "## Completion states" in template
    assert "## Remaining gates" in template


def test_scope_ledger_separates_required_and_optional_work() -> None:
    ledger = (ROOT / "docs" / "development" / "SCOPE_LEDGER_TEMPLATE.md").read_text(
        encoding="utf-8"
    )

    assert "## Required work" in ledger
    assert "## Optional enhancements" in ledger
    assert "## Explicit exclusions" in ledger
    assert "## Final reconciliation" in ledger
