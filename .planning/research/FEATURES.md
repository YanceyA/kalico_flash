# Feature Landscape: kalico-flash

**Domain:** Embedded firmware build/flash CLI for Klipper 3D printer MCUs
**Researched:** 2026-01-29
**Overall confidence:** MEDIUM (verified with official Moonraker/Klipper docs, CLI best practices)

---

## v3.3 Features Research: Config Device Editor

**Focus:** Per-device property editing via TUI config screen, following existing global config screen pattern
**Researched:** 2026-01-31
**Confidence:** HIGH (based on existing codebase patterns and standard CLI editing conventions)

---

### Table Stakes

Features users expect when editing device properties. Missing these = editor feels broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Show current values | User must see what they're changing before changing it | LOW | Reuse `render_panel` with numbered settings rows, same as global config screen |
| Show device identity (read-only) | MCU type and serial pattern are derived from hardware; editing them makes no sense. Displaying them orients the user. | LOW | Show MCU and serial_pattern at top of screen, not numbered, visually distinct |
| Edit display name | Most common edit: user wants friendlier name than what was auto-assigned | LOW | Text input with current value as default. Same pattern as path editing in `_config_screen` |
| Edit flash method | Per-device override of global default (katapult vs make_flash). Already stored in `DeviceEntry.flash_method` | LOW | Cycle/toggle between: "default", "katapult", "make_flash". Single keypress toggles like skip_menuconfig |
| Edit include/exclude status | Toggle `flashable` boolean. Already exists in model and registry (`set_flashable`) | LOW | Toggle type, flip on keypress. Same as skip_menuconfig toggle |
| Immediate persistence | Changes save to registry on each edit, not on "save and exit". Matches existing global config behavior | LOW | Use `registry.save()` after each field change, identical to `_config_screen` pattern |
| Back/escape to return | Consistent navigation with global config screen (Esc or B) | LOW | Already established pattern in `_config_screen` |
| Device selection prompt | User picks which device to configure via device number prompt | LOW | Reuse `_prompt_device_number` from tui.py |

### Differentiators

Features that improve the editing experience beyond the minimum.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Edit device key (with migration) | Renaming the key affects CLI `--device` flag and cached config directory. Doing it correctly with migration is valuable. | MEDIUM | Must: validate new key (no spaces, no duplicates), rename config cache dir, update registry atomically. Show warning about CLI flag change. |
| Show effective flash method | When flash_method is None (use default), show "default (katapult)" so user sees what will actually happen | LOW | Read global_config.default_flash_method and display alongside "default" option |
| Validation on text input | Reject empty names, reject duplicate keys, reject keys with spaces/special chars | LOW | Reuse validation pattern from add-device wizard. Key validation: lowercase, alphanumeric + hyphens |
| Status message after edit | Brief confirmation like "Name updated" shown on redraw, same as global config screen implicitly does by redrawing | LOW | Already happens naturally with screen redraw pattern |

### Anti-Features

Things to deliberately NOT build for device config editing.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Edit MCU type | MCU is extracted from serial path during discovery. Changing it would break config cache matching and build targeting. | Show as read-only. If wrong, user should remove and re-add device. |
| Edit serial pattern | Serial pattern is hardware-derived. Changing it breaks device matching on USB scan. | Show as read-only. If wrong, remove and re-add. |
| Multi-device batch edit | "Change flash method for all devices" adds complexity for a rare action. Users have 2-5 devices typically. | Edit one device at a time. Fast enough with single-keypress toggles. |
| Undo/revert changes | Adds state tracking complexity. Edits are simple field changes, not dangerous operations. | Each field saves immediately. User can re-edit to previous value. |
| Free-form JSON editing | Exposing raw JSON is error-prone and breaks the abstraction. | Structured fields with validation only. |
| Delete device from config screen | Config screen is for editing properties. Delete is a separate destructive action already handled by Remove Device (R key). Mixing edit and delete UX is confusing. | Keep Remove as separate main menu action with its own confirmation flow. |
| Edit blocked_devices list | Blocked devices are a separate concept from registered device config. Mixing them muddies the UI. | Blocked devices managed via separate mechanism if needed. |

### Feature Dependencies

```
[Existing: _config_screen pattern in tui.py]
    |-- provides --> [Screen layout pattern: status panel + settings panel]
    |-- provides --> [Input handling: _getch for selection, input() for text]
    |-- provides --> [Toggle pattern: flip boolean on keypress]
    |-- provides --> [Text edit pattern: prompt with [current] default]

[Existing: _prompt_device_number in tui.py]
    |-- provides --> [Device selection before entering config screen]

[Existing: Registry.save() + atomic writes]
    |-- provides --> [Immediate persistence after each edit]

[Existing: DeviceEntry model in models.py]
    |-- defines --> [Editable fields: key, name, flash_method, flashable]
    |-- defines --> [Read-only fields: mcu, serial_pattern]

[NEW: Device key rename]
    |-- requires --> [Registry: remove old key + add new key atomically]
    |-- requires --> [Config cache: rename directory from old key to new key]
    |-- requires --> [Validation: no duplicate keys, valid key format]
```

**Dependency Notes:**
- **Zero new modules needed.** All patterns exist in `_config_screen`. Device config is essentially the same screen with different fields and a different data source (DeviceEntry instead of GlobalConfig).
- **Key rename is the only non-trivial operation.** It touches registry (remove+add) and filesystem (config cache dir rename). Everything else is simple field assignment.
- **Registry already has `set_flashable()`** but lacks a general `update_device()` method. Will need either a new method or direct load/modify/save pattern.

### MVP Definition (v3.3)

Launch with the minimum that makes device config editing functional.

- [ ] Device config screen accessible via new main menu action key
  - **Why essential:** Must be reachable. Add "E" (Edit Device) or similar to actions panel.
- [ ] Device selection via numbered prompt (reuse `_prompt_device_number`)
  - **Why essential:** Must pick which device to edit
- [ ] Read-only identity section showing MCU and serial pattern
  - **Why essential:** Orients user; prevents "where do I change MCU?" confusion
- [ ] Editable display name (text input with current value default)
  - **Why essential:** Most common edit operation
- [ ] Editable flash method (toggle: default / katapult / make_flash)
  - **Why essential:** Per-device flash method override is core functionality
- [ ] Editable include/exclude status (toggle)
  - **Why essential:** Already exists as concept; needs UI exposure
- [ ] Immediate save on each edit (match global config pattern)
  - **Why essential:** Consistency with existing settings screen

### Add After Validation (v3.4+)

Features to add once core device config is working.

- [ ] Device key rename with config cache migration -- Trigger: user requests it or finds key naming painful
- [ ] Show effective flash method ("default (katapult)") -- Trigger: user confusion about what "default" means
- [ ] Input validation feedback (duplicate key, empty name) -- Trigger: user manages to corrupt registry via bad input

### Design Decisions

**Screen Layout: Match Global Config Pattern**

```
  ┌─[ S T A T U S ]──────────────────────────────────────────┐
  │  Press setting number to edit, Esc to return              │
  └───────────────────────────────────────────────────────────┘

  ┌─[ D E V I C E :  O C T O P U S - P R O ]────────────────┐
  │                                                           │
  │  MCU:     stm32h723                                       │
  │  Serial:  usb-Klipper_stm32h723xx_29001A*                 │
  │                                                           │
  │  1. Name:          Octopus Pro v1.1                       │
  │  2. Flash method:  default                                │
  │  3. Included:      YES                                    │
  │                                                           │
  └───────────────────────────────────────────────────────────┘
```

**Rationale:**
- Panel title includes device key for identification
- Read-only fields (MCU, Serial) shown first without numbers
- Editable fields numbered starting at 1, same as global config
- Three fields keeps it simple; more can be added later

**Field Types (matching existing `_config_screen` patterns):**

| Field | Type | Behavior |
|-------|------|----------|
| Name | text | Prompt with `[current]` default, Enter to keep |
| Flash method | cycle | Keypress cycles: default -> katapult -> make_flash -> default |
| Included | toggle | Keypress flips YES/NO immediately |

**Rationale for "cycle" instead of "toggle" for flash method:**
- Flash method has 3 values, not 2. Toggle is for booleans.
- Cycle on keypress (no Enter needed) matches the toggle UX but for 3-state.
- Display: "default", "katapult", "make_flash"

**Action Key: "E" for Edit Device**

Adding to ACTIONS list after Remove:
```
("E", "Edit Device")
```

**Rationale:**
- "C" is already taken by Config (global settings)
- "E" for Edit is intuitive and not taken
- Follows alphabetical-ish pattern: F(lash), A(dd), R(emove), E(dit), D(evices), C(onfig), B(atch), Q(uit)

**Registry Update Pattern:**

Use load/modify/save (same as `_config_screen`):
```python
data = registry.load()
device = data.devices[device_key]
device.name = new_name  # or flash_method, flashable
registry.save(data)
```

This is simpler than adding a new `update_device()` method and matches the existing `_config_screen` pattern exactly (which uses `dataclasses.replace` on GlobalConfig then `registry.save_global()`).

### Implementation Notes

**Minimal code needed:**
1. **screen.py:** Add `DEVICE_SETTINGS` list and `render_device_config_screen()` function (follows `render_config_screen` pattern)
2. **tui.py:** Add `_device_config_screen(registry, out, device_key)` function (follows `_config_screen` pattern)
3. **tui.py:** Add "E" key handler in `run_menu` dispatch (follows "R" remove pattern: prompt device number, then enter screen)
4. **screen.py:** Add "E" to ACTIONS list
5. **validation.py:** Add `validate_device_name()` if input validation is included in MVP

**Estimated touch points:** 2 files (screen.py, tui.py), ~80-120 lines of new code.

### Real-World CLI Patterns (from Codebase Analysis)

**Existing Global Config Screen (the pattern to follow):**
- Clear screen, draw panels, prompt for setting number
- Single keypress selects field
- Toggle fields flip immediately (no Enter)
- Text/numeric fields prompt with `[current]` default
- Empty input = keep current value
- Loops back to redraw after each edit
- Esc/B returns to main menu

**Existing Device Selection (reusable):**
- `_prompt_device_number()` handles single/multi device selection
- Auto-selects if only one device exists
- 3-attempt retry on invalid input
- Returns device key string

**These patterns mean device config is essentially a composition of existing behaviors, not a new paradigm.**

### Sources

**Primary source:** Existing codebase patterns in `tui.py` (`_config_screen`), `screen.py` (`render_config_screen`, `SETTINGS`), `validation.py`, `registry.py`
**Confidence:** HIGH -- all patterns are verified in working code

---

## v3.2 Features Research: Visual Dividers for Action Workflows

**Focus:** Lightweight separators between workflow steps in flash, add-device, remove-device, and flash-all
**Researched:** 2026-01-30
**Confidence:** HIGH (verified with Docker, Yarn, npm/inquirer.js CLI patterns)

---

### Table Stakes

Features users expect in professional CLI tools with multi-step workflows. Missing these = workflow feels unpolished.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Visual step separation | Users need to scan back through output; separators signal step boundaries | LOW | Simple character-based dividers (--- or ---) |
| Consistent placement | Dividers always appear in same position relative to content | LOW | Before prompts, between phases, between devices |
| Color inheritance | Dividers use existing theme colors for visual coherence | LOW | Already have theme.border (muted teal) and theme.subtle |
| Lightweight rendering | Dividers don't slow down output or clutter simple workflows | LOW | Single print statement, no animations |
| Work without Unicode | Fallback to ASCII dashes when UTF-8 unavailable | LOW | Already have _supports_unicode() in tui.py |

### Differentiators

Features that set kalico-flash apart from typical CLI tools. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Device-labeled dividers | Flash-all shows --- 1/N DeviceName --- for each device | MEDIUM | Helps user track multi-device flash progress visually |
| Step-labeled dividers | Show step count in flash-all (step 1, step 2, step 3) | LOW | Already common in Docker/yarn; reinforces progress |
| Adaptive width | Dividers span terminal width for clean edge-to-edge look | MEDIUM | Need to detect terminal width reliably (shutil.get_terminal_size) |
| Silent mode respected | Dividers disappear when --quiet flag is used | LOW | Respects existing output conventions |
| Panel integration | Dividers use same border color as panels for unified aesthetic | LOW | Already have theme.border (100, 160, 180) RGB |

### Anti-Features

Features that seem good but create problems in terminal output.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Fancy Unicode art | "Make it look modern" | Breaks on ASCII-only terminals, looks busy, hard to grep | Simple --- already professional |
| Progress bars inside dividers | "Show completion at divider" | Clutters divider area, redraws create flicker | Keep progress separate; divider is static boundary |
| Colored dividers per status | "Green for success, red for fail" | User scans for divider shape, not color; changing color breaks consistency | Use status markers ([OK], [FAIL]) not divider color |
| Animated dividers | "Sliding effect when step completes" | Terminal redraws are jarring; breaks scrollback | Static dividers signal completed steps clearly |
| Multi-line dividers | "Box around each step" | Doubles vertical space; harder to scan output quickly | Single-line divider is cleaner, faster to parse |

### Feature Dependencies

```
[Theme system (EXISTING)]
    +--requires--> [Color detection (EXISTING)]
                       +--enables--> [Colored dividers]

[Unicode detection (EXISTING)]
    +--enables--> [Unicode dividers with ASCII fallback (---)]

[Terminal width detection (NEW)]
    +--enables--> [Adaptive-width dividers]
    +--optional for--> [Fixed-width dividers (60 chars)]

[Output interface (EXISTING)]
    +--requires--> [Divider output method]
                       +--used by--> [Flash workflow]
                       +--used by--> [Add-device wizard]
                       +--used by--> [Flash-all batch]
```

**Dependency Notes:**
- **Theme system enables colored dividers:** Already have `theme.border` and `theme.subtle` defined in theme.py (RGB: 100,160,180 and 100,120,130). Dividers inherit these colors automatically.
- **Unicode detection enables character selection:** tui.py already has `_supports_unicode()` checking LANG/LC_ALL for UTF-8. Reuse this for divider character selection.
- **Terminal width optional:** Can use fixed 60-character dividers initially, add adaptive width later if needed.
- **Output interface needs divider method:** Add `out.step_divider()` and `out.device_divider()` to Output protocol in output.py, implement in CliOutput, NullOutput for testing.

### MVP Definition (Milestone 16)

Launch with minimum viable dividers -- what's needed to improve workflow readability.

- [x] Simple dividers before prompts
  - **Why essential:** Separates user action (input) from system output (info)
- [x] Dividers between flash workflow phases
  - **Why essential:** Discovery -> Config -> Build -> Flash phases need visual breaks
- [x] Device-labeled dividers in flash-all
  - **Why essential:** Multi-device flash needs clear "now flashing X" boundaries
- [x] Unicode detection with ASCII fallback
  - **Why essential:** Can't break on ASCII-only SSH terminals

### Add After Validation (v3.3+)

Features to add once core dividers are working and tested.

- [ ] Adaptive terminal width -- Trigger: user reports dividers look too short/long
- [ ] Step-labeled dividers in flash-all -- Trigger: user confusion about which step is running
- [ ] Quiet mode suppression -- Trigger: when `--quiet` flag is added
- [ ] Divider style customization in settings -- Trigger: user requests different character

### Future Consideration (v4.0+)

Features to defer until usage patterns are established.

- [ ] Theme-specific divider characters -- Why defer: theme system may expand; wait to see what's needed
- [ ] Section headers with dividers -- Why defer: may conflict with panel-based TUI if both are visible

### Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Simple dividers before prompts | HIGH | LOW | P1 |
| Dividers between workflow phases | HIGH | LOW | P1 |
| Device-labeled dividers (flash-all) | HIGH | MEDIUM | P1 |
| Unicode/ASCII fallback | HIGH | LOW | P1 |
| Adaptive terminal width | MEDIUM | MEDIUM | P2 |
| Step-labeled dividers | MEDIUM | LOW | P2 |
| Quiet mode respected | MEDIUM | LOW | P2 |
| Colored dividers (theme integration) | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch -- improves readability for all workflows
- P2: Should have, add when possible -- polish and edge cases
- P3: Nice to have, future consideration -- theme consistency

### Real-World CLI Patterns (from Research)

**Docker Build Output:**
- Uses `Step 1/6 : FROM ubuntu` pattern with step numbers and total count
- Each step separated by blank line and arrow indicator
- **Lesson:** Numbered steps help users track progress through sequential workflows

**Yarn Install Output:**
- Four distinct phases: Resolution -> Fetch -> Link -> Build
- Phase labels printed with timing information
- No explicit dividers; blank lines separate phases
- **Lesson:** Phase labels alone may be sufficient for simple flows; dividers add polish

**NPM Package Installers:**
- Use dash lines for separators
- Inquirer.js provides `new inquirer.Separator()` that defaults to `--------`
- Prompts package supports custom separator characters
- **Lesson:** Industry standard is simple dash/underscore lines, 40-70 chars wide

**Build Tools (Make, CMake):**
- No built-in dividers; rely on command output echoing (`echo "=== Building X ==="`)
- Separator scripts print dash lines calculated from terminal width
- **Lesson:** Users add dividers manually in build scripts because output scanning is hard

**Git Output:**
- Uses conflict markers `<<<`, `===`, `>>>` as semantic dividers during merge
- No visual dividers between commands; blank lines only
- **Lesson:** Git prioritizes machine-parseable output; CLI tools with human workflows benefit from visual structure

### Competitor Feature Analysis

kalico-flash is a niche tool (Klipper firmware flashing), so "competitors" are general CLI workflow tools.

| Feature | Docker Build | Yarn Install | Inquirer.js Prompts | kalico-flash Approach |
|---------|--------------|--------------|---------------------|----------------------|
| Step numbering | Yes (Step 1/6) | No | No | Yes (flash-all: 1/2 DeviceName) |
| Visual dividers | No (blank lines) | No | Yes (Separator class) | Yes (--- or ---) |
| Phase labels | Yes ([stage name]) | Yes (Resolution, Fetch) | No | Yes ([Discovery], [Build]) |
| Color coding | Yes (ANSI colors) | Yes (chalk library) | Yes (ansi colors) | Yes (theme.border) |
| Unicode support | Yes | Yes (respects NO_COLOR) | Yes | Yes (with ASCII fallback) |

**Our approach:**
- Combine Docker's step numbering with Inquirer's explicit dividers
- Lightweight like Yarn (no animations), but clearer than blank lines
- Honor kalico-flash's existing theme system for consistency

### Design Decisions

**Divider Character: box drawings light quadruple dash vs box drawings light horizontal**

**Choice:** Use light quadruple dash (U+2504) for regular dividers, light horizontal (U+2500) for device-labeled dividers

**Rationale:**
- Dotted line is lighter, less intrusive -- good for separating steps within a workflow
- Solid line is stronger -- good for device-labeled sections in flash-all
- Both are in the same Unicode block (Box Drawing) so terminals that support one support both
- ASCII fallback: dotted -> '- ' (dash-space pattern), solid -> '-' (solid dashes)

**Divider Width: Fixed 60 chars vs Terminal Width**

**Choice:** Start with fixed 60 chars, add adaptive width in P2

**Rationale:**
- 60 chars fits 80-column terminals with 2-space indent
- Avoids edge-case bugs (terminal resize mid-output, COLUMNS unset)
- `shutil.get_terminal_size()` is reliable, but adds complexity for marginal gain
- Docker and Yarn use fixed-width output; users don't complain

**Placement Rules**

| Workflow | Divider Location | Example |
|----------|------------------|---------|
| Flash single device | Before each phase change | After [Discovery], before [Config] |
| Flash single device | Before confirmation prompts | Before "Flash Octopus Pro? [Y/n]" |
| Flash-all | Before each device section | --- 1/2 Octopus Pro --- |
| Flash-all | Before build/flash sub-steps | Building firmware... |
| Add-device | Before each wizard prompt | before "Device key:" |
| Remove-device | Before confirmation prompt | before "Remove 'octopus-pro'?" |
| Config menu | Not used (panel-based) | Panel borders provide structure |

**Color: theme.border vs theme.subtle**

**Choice:** Use `theme.border` (100, 160, 180 RGB -- muted teal)

**Rationale:**
- Matches panel border color in TUI for visual consistency
- `theme.subtle` (100, 120, 130) is too dim; dividers might be invisible on dark terminals
- User's intention: dividers should match panel borders (muted teal, not grey)

### Implementation Notes

**Output Interface Addition**

Add to `output.py` Protocol and CliOutput:

```python
def step_divider(self) -> None:
    """Print lightweight divider before workflow steps."""
    # U+2504 if Unicode, else dash-space pattern "- - - - ..."

def device_divider(self, index: int, total: int, device_name: str) -> None:
    """Print device-labeled divider for flash-all batches."""
    # Example: --- 1/2 Octopus Pro ---
```

**Unicode Detection**

Reuse `tui._supports_unicode()` logic:

```python
def _get_divider_char() -> str:
    return "\u2504" if _supports_unicode() else "- "
```

**Width Calculation**

Fixed width for MVP:

```python
DIVIDER_WIDTH = 60
divider = char * DIVIDER_WIDTH
```

Adaptive width (P2):

```python
import shutil
width = shutil.get_terminal_size().columns - 4  # Reserve 4 for indent
```

### Sources

**CLI Best Practices:**
- [Command Line Interface Guidelines](https://clig.dev/)
- [CLI UX best practices: 3 patterns for improving progress displays -- Martian Chronicles](https://evilmartians.com/chronicles/cli-ux-best-practices-3-patterns-for-improving-progress-displays)

**Docker Build Output:**
- [Best practices | Docker Docs](https://docs.docker.com/build/building/best-practices/)
- [Multi-stage | Docker Docs](https://docs.docker.com/build/building/multi-stage/)

**Yarn/NPM Terminal Formatting:**
- [yarn install | Yarn](https://yarnpkg.com/cli/install)
- [inquirer - npm](https://www.npmjs.com/package/inquirer)
- [prompts - npm](https://www.npmjs.com/package/prompts)

**Visual Hierarchy & Separators:**
- [Visual Dividers in User Interfaces: Types and Design Tips](https://blog.tubikstudio.com/visual-dividers-user-interface/)
- [Steps UI design tutorial for better multi-step UX](https://www.setproduct.com/blog/steps-ui-design)

**Terminal Separator Scripts:**
- [GitHub - pjnadolny/separator: A shell script to print separator lines](https://github.com/pjnadolny/separator)

---

## v2.1 Features Research: Panel TUI and Flash All

**Focus:** Panel-based terminal UI redesign, batch flash, config screen, countdown timer
**Researched:** 2026-01-29

---

### Table Stakes

Features that must exist for the panel TUI and Flash All to feel complete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Bordered panel layout with sections | KIAUH and similar Klipper tools use box-drawn panels to organize status, devices, and actions. Users of the ecosystem expect this visual structure. Without it, the redesign is just a restyled menu. | Med | Unicode box chars (rounded corners). Print full screen on each redraw. No curses -- clear and reprint. |
| Device list grouped by category | Registered/New/Blocked grouping provides instant situational awareness. A flat list forces users to mentally classify each device. | Low | Continuous numbering across groups (1-N). Group headers as subheaders within the device panel. |
| Status panel showing last operation result | Users need "what just happened?" feedback without scrolling. KIAUH shows component status in its right panel; kalico-flash needs equivalent for last flash/build outcome. | Med | Persist across menu redraws. Show device name + PASS/FAIL + brief detail. Clear when new operation begins. |
| Two-column action layout | Actions arranged in two columns use terminal width efficiently and reduce vertical scrolling. Standard pattern in KIAUH-style menus. | Low | Calculate from terminal width. Pad with spaces. Fall back to single column on narrow terminals. |
| Flash All: single service bracket | The core value of batch: stop Klipper once, build+flash each device sequentially, restart Klipper once. Per-device stop/start is slow (5+ seconds each) and fragile. | Med | Wrap entire loop in existing `klipper_service_stopped()` context manager. |
| Flash All: continue on failure | If device 2 of 5 fails, devices 3-5 must still be attempted. Aborting on first failure wastes the batch opportunity and leaves remaining devices unflashed. | Low | Collect results in list. Report summary at end. Never abort mid-batch for a single device failure. |
| Per-device progress during Flash All | Users must know which device is processing, which succeeded, which failed. Without this, batch is a black hole. | Med | Print step divider per device: `--- [2/5] Octopus Pro ---`. Show PASS/FAIL inline. Summary table at end. |
| Config screen as separate view | Settings need their own panel that replaces the main view. Cramming settings into the action menu breaks the mental model of "see devices, pick action." | Med | Clear screen, draw config panel with current values, accept edits, return to main on back. |
| Countdown timer with keypress cancel | Flashing firmware is destructive. A 5-second countdown with "press any key to cancel" is standard safety UX for irreversible operations. Especially important for Flash All where multiple devices are at stake. | Low | `select.select()` on stdin with 1-second timeout loop (Unix). Print countdown updating in place with `\r`. |
| Numbered device references | Devices get stable numbers within a session. "Flash 3" means the same device until registry changes. Numbers appear in device panel and are accepted as action input. | Low | Assign at menu draw, store mapping in session state dict. |

### Differentiators

Features that make this feel polished. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Spaced panel headers `[ D E V I C E S ]` | Visual polish matching KIAUH aesthetic. Makes the tool feel intentional and crafted, not cobbled together. | Low | Pure string formatting: insert spaces between chars, wrap in brackets. |
| Truecolor theme with ANSI 16 fallback | 24-bit color on capable terminals (most modern terminals including Pi's default), graceful fallback to ANSI 16 on limited terminals. Modern look without breaking compatibility. | Med | Detect via `COLORTERM` env var. Theme as palette dict. All color through single abstraction. |
| Connection status indicators in device list | Green dot for connected, dim/red for disconnected. Immediate visibility without running a separate command. | Low | Check `/dev/serial/by-id/` at draw time. Brief cache to avoid repeated I/O. |
| Flash All summary table | After batch completes, formatted table: Device / Status / Duration. Much clearer than scrolling through sequential output. | Low | Collect `(device, status, duration)` tuples during loop. Print aligned table at end. |
| Step dividers in terminal output | Visual separators between build phases: `=== Building Firmware ===`. Breaks the wall of make output into scannable sections. | Low | Print before each phase within a flash operation. |
| Screen-aware layout | Adapt panel widths to terminal size via `shutil.get_terminal_size()`. Minimum 60 cols with graceful degradation. | Low | Already stdlib. Clamp widths between min/max. |
| Flash All: skip unchanged configs | If a device's config hash hasn't changed since last build, skip rebuild and go straight to flash. Turns a 5-device batch from 25 minutes to under 5 minutes. | Med | Requires SHA256 comparison already implemented. Announce "Config unchanged, skipping build" per device. |

### Anti-Features

Things to deliberately NOT build. Common mistakes when building panel TUIs.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full curses/ncurses interactive TUI | Massive complexity. Breaks piping, breaks some SSH clients, requires handling resize signals, partial screen updates, and input buffering. Overkill for a menu that redraws after each action. | Print-and-clear: clear screen, print all panels, wait for input. Simple, robust, debuggable. |
| Real-time progress bars (tqdm-style) | Adds dependency (forbidden) or complex custom code. Build output already streams from make. A progress bar fighting subprocess output for the terminal causes visual chaos. | Let make output stream naturally between step dividers. Show spinner only for brief waits (service stop) using simple `\r` overwrite. |
| Async/parallel flash of multiple devices | USB serial flashing is inherently serial. Parallel flash attempts cause USB bus contention and potential firmware corruption. There is no safe way to flash two USB devices simultaneously. | Sequential with continue-on-failure. The service bracket (single stop/start) already provides the batch speed win. |
| Mouse support | Target users SSH into a Pi. Mouse events are unreliable over SSH, especially through tmux/screen. Adds complexity for zero practical benefit. | Keyboard numbers only. Type number, press Enter. |
| Config file editor in TUI | Editing Kconfig values in a custom editor reimplements menuconfig poorly. menuconfig handles option dependencies, validation, and help text. A custom editor would be buggy and incomplete. | Config screen shows tool settings (paths, preferences) only. Kconfig editing launches `make menuconfig` as subprocess (already works). |
| Tab/panel switching with keyboard shortcuts | Alt+1/Alt+2 panel switching is a different UX paradigm than numbered menus. Mixing paradigms confuses users. Also unreliable over SSH. | Single view at a time. Main menu OR config screen. Not tabbed, not split-pane. |
| Undo/rollback for flash operations | Firmware flashing is one-way. "Undo" implies the previous firmware is stored, which it is not. Promising rollback creates false safety expectations. | Countdown timer IS the safety mechanism. Once flashing starts, it completes or fails. |
| Persistent log viewer in TUI | Reimplements `less`/`tail` poorly. Users already have terminal scrollback and can pipe to files. | Print output inline. User scrolls their terminal or redirects to file. |
| Animated loading screens | Spinners and animations over SSH add visual noise and can cause rendering artifacts with slow connections. | Static status messages: "Stopping Klipper..." then "Klipper stopped." |

### Expected Behavior: Panel Layout

The main screen has three visual sections stacked vertically within a single bordered box:

```
+---------------------------------------------+
|           [ S T A T U S ]                   |
|  Last: Octopus Pro flashed successfully     |
+---------------------------------------------+
|           [ D E V I C E S ]                 |
|                                             |
|  Registered                                 |
|    1) Octopus Pro v1.1      * Connected     |
|    2) Nitehawk 36           o Disconnected  |
|                                             |
|  New                                        |
|    3) usb-Klipper_rp2040_E66...             |
|                                             |
|  Blocked                                    |
|    -  Beacon Probe          (excluded)      |
|                                             |
+---------------------------------------------+
|           [ A C T I O N S ]                 |
|                                             |
|  F) Flash device        A) Flash All        |
|  C) Configure           S) Settings         |
|  R) Refresh             Q) Quit             |
|                                             |
+---------------------------------------------+
```

**Key behaviors:**
- Screen clears and redraws fully after each action returns
- Device numbers are input targets: after pressing F, prompt asks "Device number:"
- Status panel updates with result of last action
- Blocked devices shown but not selectable
- New (unregistered) devices shown with truncated serial path
- Actions use letter keys (not numbers) to avoid collision with device numbers

### Expected Behavior: Flash All

```
Flash All: 3 devices queued

[Countdown] Flashing in 5... 4... 3... 2... 1...
            Press any key to cancel.

[Service] Stopping Klipper...
[Service] Klipper stopped.

--- [1/3] Octopus Pro v1.1 -----------------------
[Config]  Loading cached config
[Build]   make clean && make -j4... done (48KB)
[Flash]   Flashing via Katapult... OK
[Verify]  Device reconnected

--- [2/3] Nitehawk 36 ----------------------------
[Config]  Loading cached config
[Build]   make clean && make -j4... done (22KB)
[Flash]   Flashing via Katapult... FAILED
          flashtool.py exited with code 1

--- [3/3] EBB36 ----------------------------------
[Config]  Config unchanged, skipping build
[Flash]   Flashing via Katapult... OK
[Verify]  Device reconnected

[Service] Starting Klipper...
[Service] Klipper started.

+---------------------------------------------+
|         [ S U M M A R Y ]                   |
|                                             |
|  Octopus Pro v1.1    PASS    12.4s          |
|  Nitehawk 36         FAIL    8.2s           |
|  EBB36               PASS    3.1s           |
|                                             |
|  Result: 2/3 succeeded                      |
+---------------------------------------------+
```

**Key behaviors:**
- Countdown before any destructive action (5 seconds default, configurable in settings)
- Single Klipper stop at start, single restart at end
- Each device gets a step divider with index and name
- Failed devices do NOT abort the batch
- Summary table at end with per-device status and duration
- Flash All only includes registered, non-excluded, connected devices
- If no devices qualify, show message and return to menu

### Expected Behavior: Config Screen

```
+---------------------------------------------+
|         [ S E T T I N G S ]                 |
|                                             |
|  1) Klipper directory    ~/klipper          |
|  2) Katapult directory   ~/katapult         |
|  3) Flash method         katapult           |
|  4) Countdown seconds    5                  |
|  5) Auto-skip menuconfig ON                 |
|                                             |
|  B) Back to main menu                       |
+---------------------------------------------+
```

**Key behaviors:**
- Replaces main view entirely (clear + redraw)
- Numbered items for editing: type number, enter new value
- Changes persist to registry JSON immediately
- B returns to main menu
- No nested sub-settings screens

### Expected Behavior: Countdown Timer

```
[Countdown] Flashing in 5... (press any key to cancel)
[Countdown] Flashing in 4...
[Countdown] Flashing in 3...
[Countdown] Flashing in 2...
[Countdown] Flashing in 1...
[Flash] Proceeding...
```

**Key behaviors:**
- Updates in place using `\r` carriage return (single line, no scroll)
- Any keypress during countdown cancels and returns to menu
- Default 5 seconds, configurable in settings (0 = no countdown)
- Used before single flash AND Flash All
- On cancel, print "Cancelled." and return to menu cleanly

### Feature Dependencies

```
Panel Drawing Engine (borders, headers, columns)
  |
  +--> Status Panel (needs operation result data)
  +--> Device Panel (needs registry + discovery at draw time)
  +--> Action Panel (needs letter-key mapping)
  +--> Config Screen (reuses panel drawing, separate view)
  |
Flash All
  |
  +--> Device Panel (selects which devices to flash)
  +--> Service Context Manager (single bracket)
  +--> Per-device build+flash loop
  +--> Result collection --> Summary Table
  |
Countdown Timer (independent, used by Flash and Flash All)
Truecolor Theme (independent, applied to all panel drawing)
```

### MVP Recommendation for v2.1

Build in this order:

1. **Panel drawing engine** -- borders, headers, two-column layout, screen clear+redraw
2. **Device panel with grouping** -- registered/new/blocked, connection status, numbering
3. **Action dispatch with letter keys** -- F/A/C/S/R/Q mapping
4. **Status panel** -- last operation result display
5. **Countdown timer** -- before flash operations
6. **Flash All** -- sequential with continue-on-failure, summary table
7. **Config screen** -- separate view for settings
8. **Truecolor theme** -- color palette applied to all panels

Defer:
- Screen-aware adaptive layout (hardcode 80 cols initially)
- Flash All skip-unchanged optimization (add after basic batch works)

---

## v2.0 Features Research (Preserved)

This section covers the planned v2.0 features. v1.0 feature research is preserved below.

---

## TUI Menu

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Numbered selection (1-9) | Users expect to type a number and press Enter | Low | Single digit works universally |
| Clear menu display | Show options with numbers | Low | Print statements sufficient |
| Return to menu after action | Don't exit after each operation | Low | Simple while loop |
| Exit option | Way to quit cleanly | Low | "0" or "q" to exit |
| TTY detection | Error gracefully if not interactive | Low | Already implemented in v1 |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Arrow key navigation | More polished UX | Medium | Requires curses (stdlib but Windows issues) |
| Search/filter | Quick find in long lists | High | Overkill for <10 devices |
| Animated selection | Visual feedback | Medium | curses dependency |
| Status inline | Show device connection status in menu | Low | Good UX improvement |

### Expected Behavior

**Industry standard (simple CLI menus):**
```
kalico-flash Menu
=================
1. Flash device
2. Add new device
3. List devices
4. Remove device
0. Exit

Choice [1-4, 0 to exit]:
```

**Key behaviors:**
- Invalid input prompts re-entry (don't crash)
- Menu redisplays after each action completes
- Actions that fail return to menu with error message
- Ctrl+C exits cleanly at any point

**Recommendation:** Build simple numbered menu first. curses adds complexity and Windows compatibility issues. Python stdlib curses is NOT available on Windows without third-party wheels (confirmed: [Python curses docs](https://docs.python.org/3/library/curses.html)). Since target is Raspberry Pi Linux, curses would work there, but simple numbered input is sufficient and tested.

**Sources:**
- [Python curses documentation](https://docs.python.org/3/library/curses.html)
- [curses-menu library](https://github.com/pmbarrett314/curses-menu) (third-party, not stdlib)

---

## Safety Checks (Print Status)

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Check before flash | Never flash during active print | Low | Single API call |
| Clear error message | "Printer is currently printing" | Low | String formatting |
| Blocking behavior | Refuse to proceed | Low | Early return |
| Moonraker API integration | Standard approach | Medium | HTTP request to localhost |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Wait-for-idle option | --wait flag to poll until idle | Medium | Polling loop with timeout |
| Progress display | Show print progress while waiting | Low | Nice but unnecessary |
| Multiple state handling | Detect paused, canceling, etc. | Low | Handle edge cases |

### Expected Behavior

**Moonraker API endpoint:**
```
GET http://localhost:7125/printer/objects/query?print_stats
```

**Response includes:**
```json
{
  "status": {
    "print_stats": {
      "state": "standby|printing|paused|complete|error",
      "filename": "...",
      "print_duration": 1234.5
    }
  }
}
```

**State values (from Klipper Status Reference):**
- `standby` - Safe to flash
- `printing` - BLOCK flash
- `paused` - BLOCK flash (user may resume)
- `complete` - Safe to flash
- `error` - Safe to flash (printer already stopped)

**Error message format:**
```
[Safety] Printer is currently printing 'benchy.gcode' (45% complete)
         Cannot flash firmware while print is active.

         Options:
         1. Wait for print to complete
         2. Cancel print via Fluidd/Mainsail
         3. Use --force to override (DANGEROUS)
```

**Fallback behavior:**
- If Moonraker unreachable, warn but allow flash with confirmation
- If printer disconnected (klippy not ready), allow flash (that's why you're flashing!)

**Recommendation:** Check `print_stats.state` - if "printing" or "paused", block. Use Python stdlib `urllib.request` for HTTP (no dependencies). Default timeout 5 seconds.

**Sources:**
- [Moonraker Printer Administration API](https://moonraker.readthedocs.io/en/latest/external_api/printer/)
- [Klipper Status Reference - print_stats](https://www.klipper3d.org/Status_Reference.html)

---

## Post-Flash Verification

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Wait for device reappear | Confirm flash succeeded | Medium | Polling loop |
| Timeout with failure | Don't wait forever | Low | 30-60 second max |
| Success message | "Device reconnected successfully" | Low | Print statement |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Recovery steps on timeout | Numbered list of what to try | Low | High value, low effort |
| Serial prefix change detection | Detect katapult_* vs Klipper_* | Low | Already have pattern matching |
| MCU version verification | Confirm new firmware version | High | Requires Klipper connection |

### Expected Behavior

**Verification flow:**
1. Flash completes (Katapult or make flash reports success)
2. Wait up to 30 seconds for device to reappear in `/dev/serial/by-id/`
3. Check for expected serial pattern (device registry has pattern)
4. Report success or timeout with recovery steps

**Polling strategy (from retry pattern research):**
- Initial wait: 3 seconds (device needs time to reboot)
- Poll interval: 2 seconds
- Max attempts: 15 (30 seconds total)
- Exponential backoff NOT needed (device either works or doesn't)

**Timeout recovery message:**
```
[Flash] Firmware written successfully
[Verify] Waiting for device to reconnect...
[Verify] TIMEOUT - Device did not reappear after 30 seconds

Recovery steps:
1. Check USB cable connection
2. Try unplugging and replugging the board
3. Check if device appears: ls /dev/serial/by-id/
4. If device shows katapult_* prefix, bootloader is active but firmware didn't flash
5. Try flashing again with: kflash --device octopus-pro
6. If still failing, try manual flash: cd ~/klipper && make flash FLASH_DEVICE=...
```

**Sources:**
- [Retry Pattern Best Practices](https://harish-bhattbhatt.medium.com/best-practices-for-retry-pattern-f29d47cd5117)
- [CLI Guidelines - Recoverable Operations](https://clig.dev/)

---

## Skip Menuconfig

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| --skip-menuconfig (-s) flag | Command-line option | Low | argparse addition |
| Cached config detection | Check if .config exists | Low | File existence check |
| Error if no cached config | Don't proceed without config | Low | Early validation |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Config hash comparison | Only skip if config unchanged | Medium | SHA256 of .config |
| Auto-skip when cached | Default to skip if exists | Low | Behavior change |
| --force-menuconfig | Override auto-skip | Low | If auto-skip enabled |

### Expected Behavior

**Klipper's KCONFIG_CONFIG pattern:**
```bash
# Standard Klipper approach for multiple boards
make menuconfig KCONFIG_CONFIG=config.octopus
make KCONFIG_CONFIG=config.octopus -j4
make flash KCONFIG_CONFIG=config.octopus FLASH_DEVICE=/dev/serial/by-id/...
```

**kalico-flash already caches configs:**
```
~/.config/kalico-flash/configs/{device-key}/.config
```

**Implementation:**
1. Check if cached config exists for device
2. If `--skip-menuconfig` and no config: ERROR
3. If `--skip-menuconfig` and config exists: copy to klipper dir, skip menuconfig
4. If no flag: run menuconfig as normal (may update cached config)

**Edge cases:**
- Cached config from different Klipper version: menuconfig may update it
- Config references hardware that changed: user responsibility

**Recommendation:** Simple flag implementation. Don't auto-skip - explicit is better than implicit. User knows when they want to skip.

**Sources:**
- [Klipper Installation - KCONFIG_CONFIG](https://www.klipper3d.org/Installation.html)
- [Voron Automating MCU Updates](https://docs.vorondesign.com/community/howto/drachenkatze/automating_klipper_mcu_updates.html)

---

## Error Messages

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Context (what were we doing) | "[Build] Compilation failed" | Low | Already have phase labels |
| Cause (what went wrong) | "make returned exit code 2" | Low | Capture subprocess output |
| Recovery steps | Numbered list of fixes | Medium | Write good copy |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Log file for details | Write verbose output to file | Medium | File I/O, path handling |
| Pre-populated bug report URL | GitHub issue with context | Medium | URL encoding |
| Error codes | Machine-readable error types | Low | Already have exception hierarchy |

### Expected Behavior

**From CLI Guidelines (clig.dev):**
- Rewrite errors for human understanding
- Position critical information at end (where eyes focus)
- Include debug info responsibly (file, not terminal)
- Group similar errors under single header

**Error message template:**
```
[Phase] What went wrong
        Why it might have happened

        To fix this:
        1. First thing to try
        2. Second thing to try
        3. If still failing, try X

        For more details: ~/.config/kalico-flash/logs/build.log
```

**Example - build failure:**
```
[Build] Firmware compilation failed (exit code 2)
        This usually means a configuration mismatch or missing toolchain.

        To fix this:
        1. Run 'kflash --device octopus-pro' without --skip-menuconfig
        2. In menuconfig, verify MCU type matches your board
        3. Check arm-none-eabi-gcc is installed: arm-none-eabi-gcc --version
        4. Review build log: cat ~/klipper/out/klipper.log
```

**Example - device not found:**
```
[Discovery] Device 'octopus-pro' not connected
            Expected serial pattern: usb-Klipper_stm32h723xx_*

            To fix this:
            1. Check USB cable is connected
            2. Verify device appears: ls /dev/serial/by-id/
            3. If device shows different name, re-register: kflash --add-device
            4. If using CAN bus, note this tool only supports USB devices
```

**Sources:**
- [Command Line Interface Guidelines](https://clig.dev/)
- [Error Handling in CLI Tools](https://medium.com/@czhoudev/error-handling-in-cli-tools-a-practical-pattern-thats-worked-for-me-6c658a9141a9)

---

## Version Detection

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Detect mismatch post-flash | Compare host vs MCU | Medium | Requires Klipper running |
| Warning message | "MCU version mismatch detected" | Low | String formatting |
| Recovery guidance | "Reflash or update Klipper" | Low | Static text |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Pre-flash version check | Warn before flashing | High | MCU must be connected and running |
| Automatic version match | Pull correct git commit | High | Out of scope (dangerous) |

### Expected Behavior

**The problem (from Klipper discourse):**
When host Klipper updates but MCU firmware is old, you get:
```
mcu 'mcu': Command format mismatch: endstop_home oid=%c clock=%u...
```

**Klipper provides this info via:**
- Host version: `git describe --always --tags --long --dirty` in klipper dir
- MCU version: `printer.mcu.mcu_version` via Moonraker API (requires running Klipper)

**Detection approach:**
1. After flash, if Klipper starts successfully, query `printer.mcu.mcu_version`
2. Compare with host version (git describe output)
3. If mismatch, warn but don't fail (flash was successful)

**Challenges:**
- Klipper must restart and connect to MCU first
- Version format: `v0.12.0-148-g1a2b3c4d` (git describe)
- Partial matches may be OK (same major.minor)

**Warning message:**
```
[Verify] Version mismatch detected
         Host Klipper: v0.12.0-148-g1a2b3c4d
         MCU firmware: v0.11.0-284-g5e6f7a8b

         This may cause "Command format mismatch" errors.
         To fix: Update Klipper host (git pull) then reflash all MCUs.
```

**Recommendation:** Implement as informational warning only. Don't block on mismatch - user may have intentional version pinning. LOW priority - most users will see Klipper's own error message anyway.

**Sources:**
- [Klipper MCU Protocol Error](https://klipper.discourse.group/t/mcu-protocol-error-caused-by-running-an-older-version-of-the-firmware/10371)
- [Mainsail MCU Protocol Error FAQ](https://docs.mainsail.xyz/faq/klipper_errors/command-format-mismatch)
- [Klipper Status Reference - mcu object](https://www.klipper3d.org/Status_Reference.html)

---

## Installation Script

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Symlink to PATH | `kflash` command available globally | Low | ln -s |
| Detect existing installation | Don't overwrite without confirmation | Low | File exists check |
| Uninstall instructions | How to remove | Low | Documentation |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Auto-detect PATH location | Find writable bin directory | Medium | Check multiple locations |
| Shell completion | Tab completion for device names | High | Bash/Zsh specific |
| Update mechanism | Check for new versions | High | Network, versioning |

### Expected Behavior

**Installation locations (priority order):**
1. `~/.local/bin/` - User-local, no sudo needed (preferred)
2. `~/bin/` - Alternative user-local
3. `/usr/local/bin/` - System-wide, requires sudo

**Install script (`install.sh`):**
```bash
#!/bin/bash
set -e

INSTALL_DIR="${HOME}/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create bin directory if needed
mkdir -p "$INSTALL_DIR"

# Create symlink
ln -sf "${SCRIPT_DIR}/flash.py" "${INSTALL_DIR}/kflash"

# Make executable
chmod +x "${SCRIPT_DIR}/flash.py"

echo "Installed kflash to ${INSTALL_DIR}/kflash"
echo ""
echo "Ensure ${INSTALL_DIR} is in your PATH:"
echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
echo "  source ~/.bashrc"
```

**Uninstall:**
```bash
rm ~/.local/bin/kflash
```

**PATH considerations:**
- MainsailOS/FluiddPi may not have `~/.local/bin` in PATH by default
- Script should check and advise if not in PATH
- Never modify PATH automatically (user decision)

**Sources:**
- [Beginner's Guide to Executables](https://dev.to/hbalenda/beginner-s-guide-to-usr-local-bin-4fe2)
- [AWS CLI Installation Pattern](https://docs.aws.amazon.com/cli/v1/userguide/install-linux.html)

---

## Device Exclusion

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Mark device as non-flashable | Registry flag | Low | Boolean in JSON |
| Skip in selection menus | Don't offer excluded devices | Low | Filter in display |
| Show in list with status | "(excluded)" annotation | Low | String formatting |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Exclusion reason | "Beacon probe - use Beacon updater" | Low | String field |
| Temporary exclusion | Time-based or flag-based | Medium | Complexity not worth it |
| Pattern-based exclusion | Exclude by serial pattern | Medium | Regex overhead |

### Expected Behavior

**Use case: Beacon probe**
Beacon probe appears in `/dev/serial/by-id/` but should NOT be flashed via kalico-flash - it has its own update tool.

**Registry format:**
```json
{
  "devices": {
    "beacon": {
      "name": "Beacon Probe",
      "mcu": "rp2040",
      "serial_pattern": "usb-Beacon_*",
      "excluded": true,
      "exclusion_reason": "Use Beacon's built-in updater"
    }
  }
}
```

**Behavior:**
- `--list-devices`: Shows device with "(excluded)" status
- Interactive selection: Excluded devices not offered
- `--device beacon`: Error with exclusion reason
- `--add-device`: Option to mark as excluded during registration

**Error message:**
```
[Discovery] Device 'beacon' is excluded from flashing
            Reason: Use Beacon's built-in updater

            To flash anyway: kflash --device beacon --force
            To remove exclusion: kflash --remove-exclusion beacon
```

**Recommendation:** Simple boolean flag with optional reason string. Don't over-engineer with patterns or time-based rules.

---

## All Anti-Features (explicitly excluded)

Things to deliberately NOT build and why:

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| curses-based fancy menus | Windows compat, complexity | Print-and-clear panels |
| Auto-update Klipper source | Dangerous - breaks MCU compatibility | User runs `git pull` manually |
| CAN bus device support | Different discovery mechanism | Separate tool or future version |
| RPi MCU flashing | Different workflow (linux service) | Document manual process |
| Firmware version rollback | Requires storing binaries, complex | User keeps backups |
| GUI/web interface | Out of scope for CLI tool | Moonraker integration later |
| Windows/Mac support | Target is Raspberry Pi | Document Pi-only |
| Interactive prompts mid-flash | Dangerous during flash | All prompts before flash starts |
| Automatic config migration | Kconfig format may change | User re-runs menuconfig |
| Mouse support in TUI | Unreliable over SSH | Keyboard numbers only |
| Parallel device flashing | USB contention, corruption risk | Sequential with continue-on-failure |
| Tab switching / split panes | Wrong paradigm for numbered menus | Single view at a time |

**Key principle:** This tool does ONE thing well - flash USB-connected MCUs on a Raspberry Pi. Resist scope creep.

---

## Feature Dependencies (All Versions)

### v3.3 device config depending on v3.0+ capabilities

| v3.3 Feature | Depends On | Existing Capability |
|--------------|------------|---------------------|
| Device config screen | Config screen pattern | tui.py `_config_screen` |
| Device selection | Device number prompt | tui.py `_prompt_device_number` |
| Panel rendering | Panel system | panels.py `render_panel` |
| Toggle editing | Toggle pattern | tui.py `_config_screen` toggle handler |
| Text editing | Text input pattern | tui.py `_config_screen` path/numeric handler |
| Persistence | Registry save | registry.py `save()` |

### v3.2 dividers depending on v2.1+ capabilities

| v3.2 Feature | Depends On | v2.1+ Capability |
|--------------|------------|------------------|
| Step dividers | Output interface | output.py Protocol |
| Device dividers | Flash-all batch | cmd_flash_all in flash.py |
| Unicode detection | TUI utils | tui._supports_unicode() |
| Colored dividers | Theme system | theme.py get_theme() |

### v2.1 features depending on v2.0 capabilities

| v2.1 Feature | Depends On | v2.0 Capability |
|--------------|------------|-----------------|
| Panel Layout | Themed output | tui.py / output.py |
| Device Panel | Registry + discovery | registry.py, discovery.py |
| Status Panel | Operation results | BuildResult, FlashResult models |
| Flash All | Service bracket, build+flash | service.py, build.py, flasher.py |
| Config Screen | Settings persistence | registry.py (global config) |
| Countdown Timer | TTY input handling | Already available (Unix select) |
| Truecolor Theme | Color abstraction | tui.py theme system |

### v2 features depending on v1 capabilities

| v2 Feature | Depends On | v1 Capability |
|------------|------------|---------------|
| TUI Menu | Phase-labeled output | output.py module |
| Print Status Check | Moonraker connection | New (HTTP to localhost) |
| Post-Flash Verification | USB scanning | discovery.py module |
| Skip Menuconfig | Config caching | config.py module |
| Better Error Messages | Exception hierarchy | errors.py module |
| Version Detection | Moonraker API | New (HTTP to localhost) |
| Installation Script | Entry point | flash.py (already executable) |
| Device Exclusion | Device registry | registry.py module |

---

## Sources and Confidence

| Finding | Confidence | Basis |
|---------|------------|-------|
| Device config follows global config pattern | HIGH | Verified in codebase: tui.py _config_screen, screen.py render_config_screen |
| Three editable fields sufficient for MVP | HIGH | DeviceEntry model has 6 fields; 2 are hardware-derived (read-only), 1 is key (rename is complex) |
| Cycle-toggle for 3-state flash method | HIGH | Established toggle pattern works for boolean; cycle is natural extension for enum |
| "E" action key available | HIGH | Verified ACTIONS list in screen.py: F, A, R, D, C, B, Q used |
| No new modules needed | HIGH | All patterns exist in current codebase |
| Key rename needs config cache migration | HIGH | Config cache stored at `{config_cache_dir}/{device-key}/` per config.py |
| CLI divider patterns | HIGH | Verified with Docker, Yarn, npm/inquirer.js, separator scripts |
| Panel TUI print-and-clear pattern | HIGH | Standard Unix terminal pattern; KIAUH uses this approach |
| KIAUH panel layout style | MEDIUM | WebSearch results describe menu structure; could not fetch exact source |
| Flash All single-bracket pattern | HIGH | Follows from existing `klipper_service_stopped()` context manager design |
| Countdown with `select.select()` | HIGH | Python stdlib, well-documented Unix pattern |
| Continue-on-failure for batch | HIGH | Standard batch processing pattern; CLI UX best practice |
| Sequential-only USB flashing | HIGH | Hardware constraint; USB serial is single-device |
| Truecolor detection via COLORTERM | MEDIUM | Common convention but not standardized |
| CLI progress display patterns | MEDIUM | Verified with Evil Martians CLI UX article |
