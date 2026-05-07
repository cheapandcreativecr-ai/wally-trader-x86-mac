"""Unit tests for transform.py — CC agents/commands → OpenClaw skills."""
import importlib.util
import re
from pathlib import Path

import yaml

# Load transform.py under a unique module name to avoid sys.modules collision
# with adapters/opencode/transform.py when running `pytest adapters/`.
_spec = importlib.util.spec_from_file_location(
    "openclaw_transform", Path(__file__).parent / "transform.py"
)
transform = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(transform)


def _read_skill(skill_dir):
    """Helper: parse SKILL.md frontmatter + body."""
    content = (skill_dir / 'SKILL.md').read_text()
    m = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    fm = yaml.safe_load(m.group(1))
    return fm, m.group(2)


def test_agent_to_skill_basic_frontmatter(tmp_path):
    src = tmp_path / "regime-detector.md"
    src.write_text("""---
name: regime-detector
description: Detects market regime
tools: mcp__tradingview__quote_get, Read
---

## Body
Procedure here.
""")
    transform.agent_to_skill(src, tmp_path)
    fm, body = _read_skill(tmp_path / "wally-agents" / "regime-detector")

    assert fm['name'] == 'regime-detector'
    assert fm['description'] == 'Detects market regime'
    assert fm['version'] == '1.0.0'
    assert 'wally-trader' in fm['metadata']['openclaw']['tags']
    assert 'agent' in fm['metadata']['openclaw']['tags']
    assert fm['metadata']['openclaw']['category'] == 'trading-agent'
    assert 'Procedure here.' in body


def test_agent_to_skill_detects_mcp_toolset(tmp_path):
    src = tmp_path / "tv-agent.md"
    src.write_text("""---
name: tv-agent
description: Uses TradingView MCP
tools: mcp__tradingview__quote_get, mcp__tradingview__draw_shape
---

body
""")
    transform.agent_to_skill(src, tmp_path)
    fm, _ = _read_skill(tmp_path / "wally-agents" / "tv-agent")
    toolsets = fm['metadata']['openclaw']['requires_toolsets']
    assert 'mcp' in toolsets
    assert 'terminal' in toolsets


def test_agent_to_skill_detects_web_toolset(tmp_path):
    src = tmp_path / "web-agent.md"
    src.write_text("""---
name: web-agent
description: Web fetcher
tools: WebFetch, WebSearch, Read
---

body
""")
    transform.agent_to_skill(src, tmp_path)
    fm, _ = _read_skill(tmp_path / "wally-agents" / "web-agent")
    assert 'web' in fm['metadata']['openclaw']['requires_toolsets']


def test_agent_to_skill_detects_subagents_toolset(tmp_path):
    src = tmp_path / "router.md"
    src.write_text("""---
name: router
description: Routes to other agents
tools: Agent, Read
---

body
""")
    transform.agent_to_skill(src, tmp_path)
    fm, _ = _read_skill(tmp_path / "wally-agents" / "router")
    assert 'subagents' in fm['metadata']['openclaw']['requires_toolsets']


def test_agent_to_skill_no_tools_only_terminal(tmp_path):
    src = tmp_path / "simple.md"
    src.write_text("""---
name: simple
description: Plain agent
---

body
""")
    transform.agent_to_skill(src, tmp_path)
    fm, _ = _read_skill(tmp_path / "wally-agents" / "simple")
    assert fm['metadata']['openclaw']['requires_toolsets'] == ['terminal']


def test_agent_to_skill_preserves_body_with_provenance_header(tmp_path):
    src = tmp_path / "agent.md"
    src.write_text("""---
name: agent
description: x
tools: Read
---

Line A
Line B
""")
    transform.agent_to_skill(src, tmp_path)
    _, body = _read_skill(tmp_path / "wally-agents" / "agent")
    assert "Line A" in body
    assert "Line B" in body
    assert "generated from system/agents/" in body  # provenance comment


def test_command_to_skill_basic(tmp_path):
    src = tmp_path / "morning.md"
    src.write_text("""---
description: Morning analysis
---

Run /morning protocol with $ARGUMENTS.
""")
    transform.command_to_skill(src, tmp_path)
    fm, body = _read_skill(tmp_path / "wally-commands" / "morning")

    assert fm['name'] == 'morning'
    assert fm['description'] == 'Morning analysis'
    assert 'command' in fm['metadata']['openclaw']['tags']
    assert 'slash' in fm['metadata']['openclaw']['tags']
    assert fm['metadata']['openclaw']['category'] == 'trading-command'
    assert 'subagents' in fm['metadata']['openclaw']['requires_toolsets']
    assert "$ARGUMENTS" in body


def test_command_to_skill_argument_hint_embedded(tmp_path):
    src = tmp_path / "order.md"
    src.write_text("""---
description: Place order
argument-hint: <symbol> <side> <size>
---

Encolar orden $1 $2 $3.
""")
    transform.command_to_skill(src, tmp_path)
    _, body = _read_skill(tmp_path / "wally-commands" / "order")
    assert "<!-- args: <symbol> <side> <size> -->" in body
    assert "$1 $2 $3" in body


def test_command_to_skill_uses_filename_as_slash_name(tmp_path):
    """Slash command /risk → skill name 'risk' (filename without ext)."""
    src = tmp_path / "risk.md"
    src.write_text("""---
description: position sizing
---

Calc 2% risk.
""")
    transform.command_to_skill(src, tmp_path)
    fm, _ = _read_skill(tmp_path / "wally-commands" / "risk")
    assert fm['name'] == 'risk'


def test_command_to_skill_no_frontmatter(tmp_path):
    src = tmp_path / "bare.md"
    src.write_text("Just a plain body, no frontmatter\n")
    transform.command_to_skill(src, tmp_path)
    fm, body = _read_skill(tmp_path / "wally-commands" / "bare")
    assert fm['name'] == 'bare'
    assert "Wally Trader command: /bare" in fm['description']
    assert "Just a plain body" in body


def test_clean_group_removes_orphans(tmp_path):
    """If an agent is deleted upstream, its skill must be cleaned on next run."""
    target = tmp_path / "wally-agents" / "old-agent"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("stale")

    transform._clean_group(tmp_path, 'wally-agents')
    assert not target.exists()
    assert not (tmp_path / "wally-agents").exists()


def test_clean_group_no_op_on_missing_dir(tmp_path):
    """Should not error when group dir doesn't exist."""
    transform._clean_group(tmp_path, 'nonexistent')
    # No assertion needed, just shouldn't raise.
