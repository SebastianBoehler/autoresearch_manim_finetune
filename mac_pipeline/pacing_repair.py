from __future__ import annotations

import re

MAX_PLAY_REPEAT = 3
MAX_WAIT_CALLS = 8
MAX_TRACKER_VALUE_PLAYS = 6

_PLAY_LINE = re.compile(r"^(\s*)self\.play\((.*)\)\s*$")
_WAIT_LINE = re.compile(r"^\s*self\.wait\(([^)]*)\)\s*$")
_BARE_SCENE_METHOD_LINE = re.compile(r"^\s*self\.(?:play|wait)\s*$")
_TRACKER_VALUE_PLAY_LINE = re.compile(
    r"^\s*self\.play\(\s*([A-Za-z_]\w*)\.animate\.set_value\("
)


def compact_repetitive_pacing(code: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    play_counts: dict[str, int] = {}
    tracker_value_counts: dict[str, int] = {}
    wait_count = 0
    previous_play_dropped = False
    output: list[str] = []

    for line in code.splitlines(keepends=True):
        stripped = line.strip()
        if _BARE_SCENE_METHOD_LINE.match(stripped):
            _add_note(notes, "drop dangling bare scene method references")
            previous_play_dropped = False
            continue

        tracker_match = _TRACKER_VALUE_PLAY_LINE.match(stripped)
        if tracker_match:
            tracker_name = tracker_match.group(1)
            tracker_value_counts[tracker_name] = tracker_value_counts.get(tracker_name, 0) + 1
            if tracker_value_counts[tracker_name] > MAX_TRACKER_VALUE_PLAYS:
                _add_note(notes, "drop tracker value animations beyond six-step pacing budget")
                previous_play_dropped = True
                continue

        if _PLAY_LINE.match(stripped):
            key = _compact_key(stripped)
            play_counts[key] = play_counts.get(key, 0) + 1
            if play_counts[key] > MAX_PLAY_REPEAT:
                _add_note(notes, "drop repeated self.play calls after three repeats")
                previous_play_dropped = True
                continue
            previous_play_dropped = False
            output.append(line)
            continue

        if _WAIT_LINE.match(stripped):
            if previous_play_dropped:
                _add_note(notes, "drop waits paired with removed repeated plays")
                previous_play_dropped = False
                continue
            wait_count += 1
            if wait_count > MAX_WAIT_CALLS:
                _add_note(notes, "drop waits beyond eight-call pacing budget")
                continue
            output.append(line)
            continue

        previous_play_dropped = False
        output.append(line)

    return "".join(output), notes


def _compact_key(line: str) -> str:
    return " ".join(line.split())


def _add_note(notes: list[str], note: str) -> None:
    if note not in notes:
        notes.append(note)
