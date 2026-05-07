"""
transform.py — Translate Claude Code agents/commands to OpenClaw Agent skills.

OpenClaw (NousResearch) loads skills following the agentskills.io standard:
each skill is a directory with SKILL.md (frontmatter + markdown body).
OpenClaw has NO native subagent or slash-command concept on filesystem,
so we project both into the skills system:
  - system/agents/<name>.md  → .openclaw/skills/wally-agents/<name>/SKILL.md
  - system/commands/<name>.md → .openclaw/skills/wally-commands/<name>/SKILL.md
  - system/skills/* are passthrough (already compatible standard).

Usage (invoked by install.sh or pre-commit hook):
    python3 transform.py
"""
import re
import shutil
import sys
from pathlib import Path


try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


def _parse_frontmatter(text):
    """Return (frontmatter_dict, body_str). (None, text) if no frontmatter."""
    m = re.match(r'^---\n(.*?)\n---\n(.*)', text, re.DOTALL)
    if not m:
        return None, text
    fm = yaml.safe_load(m.group(1)) or {}
    return fm, m.group(2)


def _serialize(fm, body):
    if not fm:
        return body
    return "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body


def _parse_tools(tools_raw):
    """Normalize CC `tools:` (string or list) to a clean list of tool names."""
    if isinstance(tools_raw, str):
        return [t.strip() for t in re.split(r'[,\n]', tools_raw) if t.strip()]
    if isinstance(tools_raw, list):
        return [str(t).strip() for t in tools_raw if t]
    return []


def _toolsets_from_tools(tools):
    """Map CC tool names → OpenClaw toolset names (heuristic)."""
    toolsets = {'terminal'}  # all wally trader skills shell out
    for t in tools:
        if t.startswith('mcp__'):
            toolsets.add('mcp')
        if t in ('WebFetch', 'WebSearch'):
            toolsets.add('web')
        if t == 'Agent':
            toolsets.add('subagents')  # OpenClaw has delegation/subagents
    return sorted(toolsets)


def agent_to_skill(src_path, dst_root, group='wally-agents'):
    """Claude Code agent .md → OpenClaw skill directory.

    Writes `dst_root/<group>/<name>/SKILL.md` with OpenClaw-flavored frontmatter.
    Returns the skill name written.
    """
    text = src_path.read_text()
    fm, body = _parse_frontmatter(text)
    if fm is None:
        fm = {}

    name = fm.get('name') or src_path.stem
    description = fm.get('description', f'Wally Trader agent: {name}')
    tools = _parse_tools(fm.get('tools', ''))
    toolsets = _toolsets_from_tools(tools)

    new_fm = {
        'name': name,
        'description': description,
        'version': '1.0.0',
        'metadata': {
            'openclaw': {
                'tags': ['wally-trader', 'agent', 'trading'],
                'category': 'trading-agent',
                'requires_toolsets': toolsets,
            }
        }
    }

    # Header note explaining provenance + how OpenClaw activates this skill
    header = (
        f"<!-- generated from system/agents/{src_path.name} by adapters/openclaw/transform.py -->\n"
        f"<!-- Original CC tools: {', '.join(tools) if tools else '(none)'} -->\n\n"
    )

    skill_dir = dst_root / group / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / 'SKILL.md').write_text(_serialize(new_fm, header + body))
    return name


def command_to_skill(src_path, dst_root, group='wally-commands'):
    """Claude Code slash-command .md → OpenClaw skill directory.

    Slash command `/morning` becomes skill `wally-commands/morning`,
    which OpenClaw still invokes as `/morning` (skill name = slash trigger).
    """
    text = src_path.read_text()
    fm, body = _parse_frontmatter(text)
    if fm is None:
        fm = {}

    name = src_path.stem  # /morning -> "morning"
    description = fm.get('description', f'Wally Trader command: /{name}')

    # `argument-hint` → embedded as comment (OpenClaw has no equivalent field)
    if fm.get('argument-hint'):
        body = f"<!-- args: {fm['argument-hint']} -->\n{body}"

    new_fm = {
        'name': name,
        'description': description,
        'version': '1.0.0',
        'metadata': {
            'openclaw': {
                'tags': ['wally-trader', 'command', 'slash'],
                'category': 'trading-command',
                # Commands typically delegate to agents → need terminal + subagents access
                'requires_toolsets': ['terminal', 'subagents'],
            }
        }
    }

    header = (
        f"<!-- generated from system/commands/{src_path.name} by adapters/openclaw/transform.py -->\n"
        f"<!-- OpenClaw invokes via /{name} -->\n\n"
    )

    skill_dir = dst_root / group / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / 'SKILL.md').write_text(_serialize(new_fm, header + body))
    return name


def _clean_group(dst_root, group):
    """Remove stale skills in a group dir before regen (avoid orphans)."""
    group_dir = dst_root / group
    if group_dir.exists():
        shutil.rmtree(group_dir)


def main():
    repo = Path(__file__).parent.parent.parent
    system_dir = repo / 'system'
    openclaw_build_dir = repo / '.openclaw' / 'skills'

    if not system_dir.exists():
        print(f"ERROR: {system_dir} not found.", file=sys.stderr)
        sys.exit(1)

    # Clean stale build artifacts (only the groups we generate; leave passthrough alone)
    _clean_group(openclaw_build_dir, 'wally-agents')
    _clean_group(openclaw_build_dir, 'wally-commands')

    # Agents → skills
    agent_count = 0
    src_agent_dir = system_dir / 'agents'
    for src in sorted(src_agent_dir.glob('*.md')):
        agent_to_skill(src, openclaw_build_dir)
        agent_count += 1

    # Commands → skills
    cmd_count = 0
    src_cmd_dir = system_dir / 'commands'
    for src in sorted(src_cmd_dir.glob('*.md')):
        command_to_skill(src, openclaw_build_dir)
        cmd_count += 1

    # Skills passthrough — symlink to system/skills/ for unified install location
    skills_passthrough = openclaw_build_dir / 'wally-skills'
    target = Path('../../system/skills')
    if skills_passthrough.is_symlink():
        if Path(str(skills_passthrough.readlink())) != target:
            skills_passthrough.unlink()
            skills_passthrough.symlink_to(target)
    elif skills_passthrough.exists():
        shutil.move(str(skills_passthrough), str(skills_passthrough) + '.backup')
        skills_passthrough.symlink_to(target)
    else:
        openclaw_build_dir.mkdir(parents=True, exist_ok=True)
        skills_passthrough.symlink_to(target)

    skill_passthrough_count = sum(1 for _ in (system_dir / 'skills').iterdir() if _.is_dir())

    print(f"✓ Translated {agent_count} agents → .openclaw/skills/wally-agents/")
    print(f"✓ Translated {cmd_count} commands → .openclaw/skills/wally-commands/")
    print(f"✓ Symlinked {skill_passthrough_count} skills → .openclaw/skills/wally-skills (passthrough)")


if __name__ == '__main__':
    main()
