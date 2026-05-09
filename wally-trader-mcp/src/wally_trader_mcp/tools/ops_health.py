"""Ops health MCP tool wrapper."""
from wally_core.ops import run_all_checks, overall_status


def ops_health_tool(dashboard_port: int = 8080) -> dict:
    """Run all health checks. Returns overall status + per-check details."""
    checks = run_all_checks(dashboard_port=dashboard_port)
    return {
        "overall": overall_status(checks),
        "checks": [
            {"name": c.name, "status": c.status, "detail": c.detail, "latency_ms": c.latency_ms}
            for c in checks
        ],
    }
