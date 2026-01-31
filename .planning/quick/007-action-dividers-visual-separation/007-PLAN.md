---
phase: quick-007
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - kflash/tui.py
  - kflash/panels.py
autonomous: true

must_haves:
  truths:
    - "Action output is visually separated from menu screen by a divider line"
    - "Returning to menu after action shows clear separation before redraw"
    - "Divider uses existing theme colors and render_step_divider primitive"
  artifacts:
    - path: "kflash/tui.py"
      provides: "Divider calls before/after action execution"
    - path: "kflash/panels.py"
      provides: "render_action_divider function"
  key_links:
    - from: "kflash/tui.py"
      to: "kflash/panels.py"
      via: "import render_action_divider"
      pattern: "render_action_divider"
---

<objective>
Add visual dividers between action menu redraws in the TUI to reduce visual clutter when actions produce output before returning to the main screen.

Purpose: When a user triggers an action (Flash, Add, Remove), the action output appears inline after the menu. Currently there is no visual boundary between the menu panels and the action output, or between action output and the next menu redraw. Adding dividers improves scanability.

Output: A lightweight divider element printed before action output begins, using existing theme styling and the render_step_divider primitive already in panels.py.
</objective>

<context>
@kflash/tui.py — Main menu loop, action dispatch (lines 476-576)
@kflash/panels.py — render_step_divider already exists (lines 176-202)
@kflash/theme.py — Theme with subtle/dim styles
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add action divider helper and integrate into menu loop</name>
  <files>kflash/tui.py, kflash/panels.py</files>
  <action>
1. In `kflash/panels.py`, add a `render_action_divider(label: str = "") -> str` function that produces a thin horizontal rule using the existing `render_step_divider` when a label is provided, or a simple subtle dashed line (using the ┄ character, width ~60) when no label. This reuses the existing BOX/theme infrastructure.

2. In `kflash/tui.py`, import `render_action_divider` from `.panels`.

3. In the `run_menu` while loop, after each action key echo (e.g., `print(key)` on lines 506, 518, 530, 542, 548, 554), print a blank line then `print(render_action_divider())` to visually separate the menu from the action output that follows. This applies to the `f`, `a`, `r`, `d`, `c`, `b` key handlers.

4. Before the `_countdown_return` calls (lines 512, 524, 536, 562), print a blank line to add breathing room after action output and before the countdown text.

Keep it minimal — just blank line + divider after key echo, blank line before countdown. Do NOT change the clear_screen() behavior or panel rendering.
  </action>
  <verify>
    Run `python -c "from kflash.panels import render_action_divider; print(render_action_divider()); print(render_action_divider('Flash'))"` to confirm the divider renders without errors. Then run `python -c "from kflash.tui import run_menu"` to confirm import succeeds without errors.
  </verify>
  <done>
    Action dividers appear between menu and action output. render_action_divider exists in panels.py and is called from tui.py for all action handlers.
  </done>
</task>

</tasks>

<verification>
- `python -c "from kflash.panels import render_action_divider; print(repr(render_action_divider()))"` prints a string containing ┄ characters
- `python -c "import kflash.tui"` imports without error
- Visual: on Pi, run `python3 flash.py` and press D (refresh) — divider line should appear briefly before screen clears and redraws
</verification>

<success_criteria>
- render_action_divider function exists in panels.py
- All 6 action handlers in tui.py print a divider after key echo
- Flash/Add/Remove handlers print a blank line before countdown
- No new dependencies added
</success_criteria>

<output>
After completion, create `.planning/quick/007-action-dividers-visual-separation/007-SUMMARY.md`
</output>
