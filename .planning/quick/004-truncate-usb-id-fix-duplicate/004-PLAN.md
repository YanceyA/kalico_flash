---
phase: quick
plan: 004
type: execute
wave: 1
depends_on: []
files_modified:
  - kflash/screen.py
autonomous: true

must_haves:
  truths:
    - "Long USB serial IDs are truncated with ellipsis to fit the panel"
    - "New/unregistered devices show the USB ID only once per line"
  artifacts:
    - path: "kflash/screen.py"
      provides: "truncate_serial and render_device_row fixes"
  key_links: []
---

<objective>
Fix two display bugs in the TUI devices panel: (1) truncate long USB serial IDs with ellipsis in the middle, and (2) remove duplicate USB ID display for new/unregistered devices.

Purpose: USB IDs like `usb-Klipper_stm32h723xx_29001A001151313531383332-if00` overflow the panel and new devices show the ID twice.
Output: Clean device rows that fit within the panel width.
</objective>

<context>
@kflash/screen.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix truncate_serial and remove duplicate USB ID for new devices</name>
  <files>kflash/screen.py</files>
  <action>
Two changes in `kflash/screen.py`:

1. **`truncate_serial` function (line ~82):** Change the ellipsis from `"..."` (3 dots) to `"\u2026"` (single ellipsis character). This saves 2 columns. Keep max_width at 40 — this gives enough context to identify the device while fitting the 80-col panel.

   Updated logic:
   ```python
   def truncate_serial(path: str, max_width: int = 40) -> str:
       if len(path) <= max_width:
           return path
       available = max_width - 1  # 1 char for ellipsis
       left = available // 2
       right = available - left
       return path[:left] + "\u2026" + path[-right:]
   ```

2. **`render_device_row` function (line ~222):** For new/unregistered devices, `row.name` and `row.serial_path` are identical (both set to `device.filename` in `build_device_list`). Skip appending the serial when `row.name == row.serial_path` to avoid duplication.

   Change the serial append block (around line 246) from:
   ```python
   parts.append(f"  {theme.subtle}{serial}{theme.reset}")
   ```
   to:
   ```python
   if serial != row.name:
       parts.append(f"  {theme.subtle}{serial}{theme.reset}")
   ```

   Also apply truncation to the device name for new devices so the label itself is truncated. Change line 243 area — when `row.group == "new"`, use `truncate_serial(row.name)` for the name display:
   ```python
   display_name = truncate_serial(row.name) if row.group == "new" else row.name
   parts.append(f"  {theme.text}{display_name}{theme.reset}")
   ```
  </action>
  <verify>
  Visually inspect by running on the Pi:
  ```bash
  scp kflash/screen.py yanceya@192.168.50.50:~/kalico-flash/kflash/screen.py
  ssh yanceya@192.168.50.50 "cd ~/kalico-flash && python3 -c \"from kflash.screen import truncate_serial; print(truncate_serial('usb-Klipper_stm32h723xx_29001A001151313531383332-if00'))\""
  ```
  Expected: truncated string ~40 chars with ellipsis in middle.

  Also verify render_device_row does not duplicate for new devices by checking the code logic.
  </verify>
  <done>
  - truncate_serial uses single ellipsis character and produces max 40-char output
  - New devices show USB ID once (as the name), not twice
  - Registered devices still show name + truncated serial (no change)
  </done>
</task>

</tasks>

<verification>
- Long USB IDs truncated to ~40 chars with ellipsis in middle
- New device rows show: `icon #N  usb-Klipper_stm32h7...3332-if00 (unknown)` — no trailing duplicate
- Registered device rows unchanged in behavior (name + serial are different values)
</verification>

<success_criteria>
- No USB ID exceeds 40 visible characters in the devices panel
- New/unregistered devices display the USB ID exactly once per row
</success_criteria>

<output>
After completion, create `.planning/quick/004-truncate-usb-id-fix-duplicate/004-SUMMARY.md`
</output>
