# Video Director GUI Demo

## Purpose

Provide reusable directing rules for realistic desktop GUI demo videos.

## Directing rules

1. Simulate human typing in the goal/input field.
2. Default pace intent: 3 words per second, converted to a fixed character cadence (default 15 chars/sec using 5 chars/word).
3. Type character-by-character at a constant interval; do not jump word-by-word.
4. Hide the mouse pointer while typing is in progress.
5. Do not show the mouse pointer again until a real mouse interaction starts (mouse move, a click, or scroll).
6. Show a visible mouse cursor for mouse interactions, but use a non-occluding style (hollow/translucent) so text and UI details remain readable.
7. Before any click, highlight the click target/cursor and delay the actual click by 1 second.
8. Wait 3 seconds after typing completes before triggering submit/send.
9. Wait 5 seconds after a goal completes before typing the next goal.
10. Keep progress/logger area visible during execution so viewers can see internal activity.
11. Ensure final outputs that include ASCII tables use aligned `|` separators.

## Recommended flow template

1. Launch app and pause briefly so the UI is readable.
2. Goal A: state query (show current data/state).
3. Goal B: update action + verification view.
4. Goal C: create new entries + final full-state render.
5. End on a stable final frame.

## Validation checklist

- Input typing appears incremental.
- Delay timing follows the configured pacing.
- Progress/log panel changes over time while work is running.
- Final frame and output are legible and deterministic.
