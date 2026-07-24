from pathlib import Path

from backend.leadmap.browser.subprocess_provider import SubprocessPlaywrightProvider


def test_uses_default_browser_profile_directory(monkeypatch) -> None:
    monkeypatch.delenv("LEADMAP_BROWSER_PROFILE_DIRECTORY", raising=False)

    provider = SubprocessPlaywrightProvider()

    assert provider._profile_directory == Path("browser-profile")


def test_uses_configured_browser_profile_directory(monkeypatch, tmp_path: Path) -> None:
    profile_directory = tmp_path / "acceptance-browser-profile"
    monkeypatch.setenv("LEADMAP_BROWSER_PROFILE_DIRECTORY", str(profile_directory))

    provider = SubprocessPlaywrightProvider()

    assert provider._profile_directory == profile_directory


def test_explicit_profile_directory_overrides_environment(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(
        "LEADMAP_BROWSER_PROFILE_DIRECTORY",
        str(tmp_path / "environment-profile"),
    )
    explicit_profile = tmp_path / "explicit-profile"

    provider = SubprocessPlaywrightProvider(profile_directory=explicit_profile)

    assert provider._profile_directory == explicit_profile
