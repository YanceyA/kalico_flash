# Phase 13: Config Screen & Settings - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Dedicated TUI screen for viewing and changing settings, with all values persisted in registry JSON global section. Includes a post-command countdown timer. The config screen is accessed from the main screen and returns to it. No new capabilities beyond settings management and countdown.

</domain>

<decisions>
## Implementation Decisions

### Screen layout & navigation
- Numbered flat list of all settings (no grouped sections)
- Status panel at top + Settings panel below (same bordered panel style as main screen)
- Full clear + redraw when entering config screen (separate screen, not overlay)
- Dedicated key on main screen actions panel opens config (e.g. C)
- Esc or B returns to main screen

### Settings editing flow
- Editing mechanism is Claude's discretion per setting type (toggle vs typed input) — to be refined during testing
- Each setting row shows name + current value inline (e.g. "1. Skip menuconfig: ON")
- Instant redraw after any change (no confirmation flash)
- Auto-save on change — each change writes to registry JSON immediately, no separate save step

### Countdown timer behavior
- Displays below command output (inline after output, before clearing to return to menu)
- Themed line using project color palette, styled to match panel aesthetic
- Default duration: 5 seconds
- Any keypress skips countdown immediately
- Countdown applies to: flash, flash all, add device, remove device actions only
- No countdown for: refresh (instant), config screen navigation (instant)

### Settings inventory & defaults
- **Skip menuconfig** — toggle (ON/OFF), default: OFF
- **Stagger delay** — seconds between device flashes in batch mode, default: 2s
- **Return delay** — countdown duration after commands, default: 5s
- **Klipper directory** — path to Klipper/Kalico source, default: ~/klipper
- **Katapult directory** — path to Katapult source, default: ~/katapult
- **Config cache directory** — where .config files are cached per device, default: ~/.config/kalico-flash/configs/
- Directory settings edited by typing path inline (press number, type path, Enter)
- All settings persisted in registry JSON global section

### Claude's Discretion
- Exact key mapping for config screen access (C suggested but flexible)
- Toggle vs cycle vs type-input per setting type
- Exact panel sizing and spacing
- How invalid paths are handled for directory settings
- Countdown text wording and animation style

</decisions>

<specifics>
## Specific Ideas

- Settings should feel like the main screen — same panel style, same interaction patterns (numbered items, single keypress where possible)
- Directory settings use type-then-Enter since they need arbitrary text input
- 6 total settings: 1 toggle, 2 numeric, 3 directory paths

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-config-screen-settings*
*Context gathered: 2026-01-29*
