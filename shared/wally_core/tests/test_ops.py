import pytest
from unittest.mock import patch, MagicMock
from wally_core.ops import (
    HealthCheck, latency_probe, check_disk_space, run_all_checks, overall_status,
    detect_clock_drift, check_mcp_processes,
)


def test_health_check_dataclass():
    hc = HealthCheck(name="test", status="ok", detail="all good")
    assert hc.name == "test"
    assert hc.status == "ok"
    assert hc.timestamp == ""


def test_overall_status_all_ok():
    checks = [HealthCheck("a", "ok"), HealthCheck("b", "ok")]
    assert overall_status(checks) == "ok"


def test_overall_status_warn_when_any_warn():
    checks = [HealthCheck("a", "ok"), HealthCheck("b", "warn")]
    assert overall_status(checks) == "warn"


def test_overall_status_critical_supersedes_warn():
    checks = [HealthCheck("a", "warn"), HealthCheck("b", "critical")]
    assert overall_status(checks) == "critical"


def test_run_all_checks_returns_list():
    checks = run_all_checks()
    assert len(checks) >= 4
    for c in checks:
        assert isinstance(c, HealthCheck)
        assert c.status in ("ok", "warn", "critical")
        assert c.timestamp  # populated by run_all_checks


def test_check_disk_space_returns_health_check():
    hc = check_disk_space()
    assert isinstance(hc, HealthCheck)
    assert hc.name == "disk_space"
    # Could be ok/warn/critical depending on actual disk
    assert hc.status in ("ok", "warn", "critical")


@patch("urllib.request.urlopen")
def test_latency_probe_success(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    result = latency_probe("http://test.example.com")
    assert result["ok"] is True
    assert result["status"] == 200
    assert "latency_ms" in result


@patch("urllib.request.urlopen", side_effect=Exception("fail"))
def test_latency_probe_failure(mock_urlopen):
    result = latency_probe("http://nonexistent.example.com", timeout=1.0)
    assert result["ok"] is False
    assert "error" in result


def test_check_mcp_processes_returns_health_check():
    hc = check_mcp_processes()
    assert isinstance(hc, HealthCheck)
    assert hc.name == "mcp_processes"
