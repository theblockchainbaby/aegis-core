import plistlib
from pathlib import Path

PLIST_PATH = (
    Path(__file__).resolve().parent.parent
    / "ops"
    / "launchd"
    / "com.aegiscore.dogfood.plist"
)


def test_launchd_plist_parses_as_valid_plist():
    with PLIST_PATH.open("rb") as f:
        data = plistlib.load(f)
    assert isinstance(data, dict)


def test_launchd_plist_has_keepalive_and_runs_up():
    with PLIST_PATH.open("rb") as f:
        data = plistlib.load(f)
    assert data["Label"] == "com.aegiscore.dogfood"
    assert data["KeepAlive"] is True
    assert data["RunAtLoad"] is True
    # The job must invoke `aegis-core up`.
    assert data["ProgramArguments"][-1] == "up"
    assert data["ProgramArguments"][0].endswith("aegis-core")


def test_launchd_plist_path_includes_homebrew():
    # launchd gives a minimal PATH that excludes Homebrew, where
    # nats-server lives. The plist must restore it or `up` cannot
    # find the nats-server binary.
    with PLIST_PATH.open("rb") as f:
        data = plistlib.load(f)
    assert "/opt/homebrew/bin" in data["EnvironmentVariables"]["PATH"]
