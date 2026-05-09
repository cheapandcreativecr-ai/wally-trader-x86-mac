---
description: Daily habit check-in (morning protocol, checklist, journal compliance)
---

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
