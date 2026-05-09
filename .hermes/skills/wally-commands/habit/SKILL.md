---
name: habit
description: Daily habit check-in (morning protocol, checklist, journal compliance)
version: 1.0.0
metadata:
  hermes:
    tags:
    - wally-trader
    - command
    - slash
    category: trading-command
    requires_toolsets:
    - terminal
    - subagents
---
<!-- generated from system/commands/habit.md by adapters/hermes/transform.py -->
<!-- Hermes invokes via /habit -->


Run habit check-in or show streak.

## Usage
- `/habit` — show current streak summary
- `/habit check-in` — interactive 6-question check-in (run at end of day)
- `/habit streak` — show streak detail

## Implementation
```bash
PROFILE=$(python3 .claude/scripts/profile.py get | awk '{print $1}')
ARG="$ARGUMENTS"
if [ "$ARG" = "check-in" ]; then
    python3 .claude/scripts/habit_tracker.py --profile "$PROFILE" --check-in
elif [ "$ARG" = "streak" ]; then
    python3 .claude/scripts/habit_tracker.py --profile "$PROFILE" --streak
else
    python3 .claude/scripts/habit_tracker.py --profile "$PROFILE"
fi
```
