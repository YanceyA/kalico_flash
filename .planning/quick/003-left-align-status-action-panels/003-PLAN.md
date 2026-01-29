---
phase: quick
plan: 003
type: execute
wave: 1
depends_on: []
files_modified: [kflash/screen.py]
autonomous: true

must_haves:
  truths:
    - "All three panels (header, status, actions) are left-aligned with borders flush left"
    - "Panel widths remain unchanged"
  artifacts:
    - path: "kflash/screen.py"
      provides: "Left-aligned panel rendering"
  key_links: []
---

<objective>
Left-align all TUI panels instead of centering them.

Purpose: Panels currently appear center/center-left aligned. User wants all three panels (status, devices, actions) left-aligned with borders aligned on the left side, keeping panel sizes unchanged.

Output: Modified screen.py with left-aligned panels.
</objective>

<context>
@kflash/screen.py
@kflash/panels.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove center_panel calls from screen rendering</name>
  <files>kflash/screen.py</files>
  <action>
In `render_main_screen()` (line 357), replace:
```python
centered = [center_panel(p) for p in panels]
return "\n\n".join(centered)
```
with:
```python
return "\n\n".join(panels)
```

In `render_config_screen()` (line 401-402), apply the same change:
```python
centered = [center_panel(p) for p in panels]
return "\n\n".join(centered)
```
becomes:
```python
return "\n\n".join(panels)
```

Remove the `center_panel` import from line 17 since it will be unused. Change:
```python
from .panels import center_panel, render_panel, render_two_column
```
to:
```python
from .panels import render_panel, render_two_column
```

Do NOT modify panels.py or delete center_panel — it may be used elsewhere.
  </action>
  <verify>Run `python -c "from kflash.screen import render_main_screen"` on Pi to confirm no import errors. Visually confirm panels are left-aligned by running the TUI.</verify>
  <done>All panels render left-aligned with borders flush to the left edge. Panel widths unchanged.</done>
</task>

</tasks>

<verification>
- Panels render without centering indent
- Panel border characters (top-left corner) appear at column 0
- Panel widths remain the same as before
</verification>

<success_criteria>
Status, Devices, and Actions panels all left-aligned with borders flush left. No change to panel dimensions.
</success_criteria>

<output>
After completion, create `.planning/quick/003-left-align-status-action-panels/003-SUMMARY.md`
</output>
