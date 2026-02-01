---
phase: quick
plan: 015
type: execute
wave: 1
depends_on: []
files_modified: ["kflash/screen.py"]
autonomous: true

must_haves:
  truths:
    - "Registered devices show name + firmware version + status icon on line 1"
    - "MCU and serial path appear on line 2 (indented)"
    - "Exclusion warning appears on line 3 if applicable"
    - "Unregistered devices show 'Unregistered Device' on line 1"
    - "Blocked devices show serial id indented to align with device names"
    - "Host firmware line reads 'Host Firmware:' not 'Host:'"
  artifacts:
    - path: "kflash/screen.py"
      provides: "Redesigned render_device_rows and _host_version_line"
  key_links: []
---

<objective>
Restructure the TUI device panel layout so each device uses a clearer multi-line format with firmware info on line 1 beside the name, and MCU/serial on line 2.

Purpose: Improve readability of the main device list.
Output: Updated render_device_rows() and _host_version_line() in screen.py.
</objective>

<context>
@kflash/screen.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Restructure render_device_rows() and fix host version label</name>
  <files>kflash/screen.py</files>
  <action>
  Rewrite `render_device_rows()` (lines 267-324) to produce the new layout:

  **Registered devices (row.group == "registered"):**
  - Line 1: `{icon} #{number}  {name} - {flavor} {version}  {status_icon}`
    - If no version: `{icon} #{number}  {name} - Firmware Unknown  {subtle_status_icon}`
    - The " - " separator joins name and firmware info on one line
  - Line 2: `      ({mcu})  {serial_path}` (6-space indent, same as current)
    - Only show mcu if not "unknown"; only show serial if differs from name
  - Line 3 (conditional): `      Excluded from flash operations` (if not row.flashable)

  **New/unregistered devices (row.group == "new"):**
  - Line 1: `{icon} #{number}  Unregistered Device - {flavor} {version}  {status_icon}`
    - If no version: `{icon} #{number}  Unregistered Device - Firmware Unknown  {subtle_status_icon}`
  - Line 2: `      ({mcu})  {serial_path}`

  **Blocked devices (row.group == "blocked"):**
  - Line 1: `{icon}     {serial_path}` (5 spaces after icon to align with registered device names — past "● #N  ")

  Keep all existing imports (detect_firmware_flavor, is_mcu_outdated) and theme usage. The firmware version + status icon logic moves from the old line 2 into line 1.

  Also in `_host_version_line()` (line 406): change `"Host: {flavor} {host_version}"` to `"Host Firmware: {flavor} {host_version}"`.
  </action>
  <verify>
  1. `python -c "import ast; ast.parse(open('kflash/screen.py').read())"` passes (no syntax errors)
  2. SCP to Pi and run `ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 kflash.py"` — visually confirm:
     - Registered devices show name + firmware on line 1, mcu+serial on line 2
     - Host footer says "Host Firmware:"
  </verify>
  <done>
  Device panel uses new multi-line layout: line 1 has name + firmware + status icon, line 2 has mcu + serial. Host line reads "Host Firmware:". No regressions in blocked or unregistered device rendering.
  </done>
</task>

</tasks>

<verification>
- Syntax check passes
- Visual verification on Pi with connected devices
</verification>

<success_criteria>
- Device rows match target layout described above
- Host firmware label updated
- No visual regressions for blocked/unregistered devices
</success_criteria>

<output>
After completion, create `.planning/quick/015-redesign-tui-menu-layout-box-borders/015-SUMMARY.md`
</output>
