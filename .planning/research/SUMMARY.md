# Project Research Summary

**Project:** kalico-flash v3.0 TUI Redesign & Flash All
**Domain:** Python CLI tool for Klipper firmware building/flashing
**Researched:** 2026-01-29
**Overall Confidence:** HIGH

## Executive Summary

kalico-flash v3.0 introduces a panel-based TUI redesign with truecolor theming and a batch "Flash All" command. Research across stack, features, architecture, and pitfalls reveals a high-confidence path forward with stdlib-only implementation (Python 3.9+, zero dependencies). The recommended approach centers on three foundational decisions: (1) ANSI-aware string utilities as the first building block to prevent panel misalignment, (2) build-then-flash separation to minimize Klipper downtime during batch operations, and (3) service context decomposition to prevent nested stop/start cycles.

The panel TUI follows the print-and-clear pattern with 3-tier theme fallback (truecolor > ANSI 256 > ANSI 16), avoiding curses complexity while delivering modern aesthetics. Batch flash leverages the existing `klipper_service_stopped()` context manager with a critical architectural change: all firmware builds happen BEFORE stopping Klipper, reducing downtime from N × (build + flash) to N × flash-only (30s/device vs 3min/device).

Key risks center on ANSI escape width miscalculation (breaks panel alignment), partial batch completion without recovery info (user doesn't know which boards succeeded), and terminal compatibility across SSH environments. All risks have proven mitigation patterns documented in PITFALLS.md, with critical path identified: ANSI utilities → theme upgrade → panel renderer → batch orchestrator.

## Key Findings

### Recommended Stack

The v3.0 stack extends the existing stdlib-only foundation with terminal rendering capabilities. All new modules leverage Python 3.9+ stdlib without external dependencies, maintaining the project's zero-install philosophy.

**Core technologies:**
- **`shutil.get_terminal_size()`** — Panel width detection with fallback — standard approach, never use `os.get_terminal_size()` (raises on non-TTY)
- **Truecolor ANSI escapes (`\033[38;2;R;G;Bm`)** — 24-bit RGB theming — ECMA-48 standard, validated in zen_mockup.py
- **`re.compile(r"\033\[[0-9;]*m")` for ANSI stripping** — Visible width calculation — critical utility, underpins all panel alignment
- **`termios + select.select()` (Unix) / `msvcrt` (Windows)** — Countdown keypress detection — stdlib for both platforms, requires platform switch
- **Unicode rounded box drawing (U+256D-256F)** — Panel borders — standard characters, present in all modern fonts

**Critical implementation constraint:** ANSI-aware string length utilities (`strip_ansi()`, `display_width()`, `pad_to_width()`) must be built FIRST. Every padding/alignment calculation depends on visible width, not `len()`. Truecolor adds 19 invisible chars per color token; without ANSI-aware utilities, panels will be visually broken despite syntactically correct code.

### Expected Features

Research identified table stakes, differentiators, and anti-features for the panel TUI and batch flash workflow.

**Must have (table stakes):**
- **Bordered panel layout with sections** — Status/Devices/Actions panels provide instant situational awareness (KIAUH-style expected)
- **Device list grouped by category** — Registered/New/Blocked grouping eliminates mental classification burden
- **Flash All: single service bracket** — Stop Klipper once, flash all devices, restart once (core batch value proposition)
- **Flash All: continue on failure** — Device 2 failure must not abort devices 3-5 (partial success is still success)
- **Per-device progress during batch** — Step dividers show `[2/5] Octopus Pro` with PASS/FAIL status
- **Countdown timer with keypress cancel** — 5-second safety window for destructive operations
- **Numbered device references** — Stable session numbers for device selection

**Should have (differentiators):**
- **Truecolor theme with ANSI 16 fallback** — Modern look with graceful degradation (3-tier: truecolor > 256 > 16)
- **Connection status indicators** — Green/dim dots for connected/disconnected devices at draw time
- **Flash All summary table** — Post-batch formatted table with Device/Status/Duration columns
- **Flash All: skip unchanged configs** — SHA256 comparison to skip rebuild when config unchanged (5-device batch: 25min → 5min)

**Defer (v2+):**
- Real-time progress bars — Conflicts with inherited make output, adds complexity
- Mouse support — Unreliable over SSH, no practical benefit
- Async/parallel flash — USB serial is inherently sequential, parallel causes corruption
- Undo/rollback for flash — Firmware flashing is one-way, no previous firmware stored

**Anti-features (deliberately excluded):**
- Full curses/ncurses TUI — Massive complexity, Windows compatibility issues, breaks piping
- Config file editor in TUI — Reimplements menuconfig poorly, loses dependency validation
- Tab/panel switching — Wrong UX paradigm for numbered menus

### Architecture Approach

Hub-and-spoke architecture with `flash.py` as sole orchestrator. Panel TUI adds `panels.py` as pure rendering module (data in, strings out, zero I/O) and extends `theme.py` for truecolor support. Batch flash is orchestrated by `cmd_flash_all()` in `flash.py`, NOT a separate module.

**Major components:**

1. **`panels.py` (NEW)** — Pure rendering engine that takes data and returns multi-line strings. Consumes `theme.py` for styling. Called by `tui.py` for composition. No input handling, no side effects. Functions: `render_status_panel()`, `render_device_panel()`, `render_actions_panel()`, `render_config_panel()`.

2. **`theme.py` (MODIFIED)** — Add truecolor detection via `COLORTERM` env var, extend Theme dataclass with panel-specific fields (panel_border, panel_heading, divider, status_ok/fail). Three-tier fallback: truecolor (RGB) → 256-color → ANSI 16 (existing).

3. **`flash.py::cmd_flash_all()` (NEW)** — Batch orchestrator with two-phase architecture: (1) Build phase with Klipper running: iterate devices, load configs, run menuconfig, make build; (2) Flash phase with Klipper stopped: single `with klipper_service_stopped()` wrapping all devices, flash pre-built binaries sequentially. Critical: extract `_flash_device_only()` without service management to prevent nested context manager.

4. **`tui.py` (MODIFIED)** — Refactor `_render_menu()` to use `panels.py` for rendering. Replace `_settings_menu()` with config panel screen. Panel composition: clear → `render_status_panel()` + `render_device_panel()` + `render_actions_panel()` → print → input.

5. **`output.py` (MODIFIED)** — Add `divider(label: str)` method to Output Protocol for step dividers between batch flash devices.

**Data flow for batch flash:**
```
cmd_flash_all() → preflight checks → build ALL (klipper running) →
single klipper_service_stopped() { flash device 1 → verify → flash device 2 → verify → ... } →
klipper restarts → summary table
```

**Why build-before-stop matters:** Building firmware does NOT require Klipper stopped. Flashing DOES (holds serial port). With 4 devices: old way = 12-20min downtime, new way = 2-4min downtime.

### Critical Pitfalls

Research identified 11 panel/batch-specific pitfalls plus 37 foundational pitfalls. Top 5 critical for v3.0:

1. **ANSI escape width miscalculation (PANEL-1)** — Truecolor adds 19+ invisible chars per token. Using `len()` for padding produces misaligned panels. **Prevention:** Build `strip_ansi(text)`, `display_width(text)`, `pad_to_width(text, width)` utilities FIRST before any panel code. Test with BOTH color and no-color themes.

2. **Batch flash partial completion without recovery info (PANEL-3)** — Device 2 of 4 fails, exception propagates, user has no record of which succeeded. **Prevention:** Catch per-device exceptions, continue to next device, accumulate results as `list[tuple[str, FlashResult | Exception]]`, display summary table after ALL attempts.

3. **Klipper stopped during build phase wastes downtime (PANEL-4)** — Naive batch: stop klipper → (build+flash) × N → restart. Klipper down 12-20min for 4 devices. **Prevention:** Split into build phase (klipper running) and flash phase (klipper stopped once). Build all first, abort if any fails BEFORE stopping klipper.

4. **Service context manager nesting (PANEL-11)** — Calling single-device flash function (which has `with klipper_service_stopped()`) inside batch loop that also has outer context creates nested stop/start. Inner context restarts klipper mid-batch, corrupting serial ports. **Prevention:** Extract `_flash_device_only()` without service management. Batch calls it inside single outer context.

5. **Truecolor not supported in all terminals (PANEL-2)** — PuTTY, old screen sessions, `TERM=xterm` don't support truecolor. Garbled output with literal escape codes. **Prevention:** 3-tier theme: detect via `COLORTERM` env var (`truecolor`/`24bit`) → truecolor; `TERM` contains `256color` → 256-color; else → ANSI 16 (existing). Never remove 16-color baseline.

**Foundation pitfall (from v1.0, still critical):**
- **Klipper service not restarted after flash failure (CP-1)** — Exception between stop and start leaves printer without thermal protection. **Prevention:** Already mitigated by existing `klipper_service_stopped()` context manager with try/finally. Batch flash MUST use single outer context, not per-device contexts.

## Implications for Roadmap

Based on combined research, suggested phase structure prioritizes foundation before features. Critical path: ANSI utilities → theme → panels → batch orchestrator.

### Phase 1: Panel Rendering Foundation
**Rationale:** ANSI-aware string utilities are prerequisite for all panel rendering. Terminal width detection and screen management establish the rendering contract. Building these first creates testable foundation.

**Delivers:**
- ANSI escape stripping utilities (`strip_ansi`, `display_width`, `pad_to_width`)
- Terminal width detection via `shutil.get_terminal_size()` with fallback
- Screen clearing strategy (cursor-home + overwrite vs full-clear to prevent flicker)
- Unicode box drawing detection (`sys.stdout.encoding` + `LANG` check)

**Addresses:** PANEL-1 (ANSI width), PANEL-5 (terminal width), PANEL-6 (screen flicker), PANEL-9 (Unicode detection)

**Stack elements:** `shutil`, `re`, `os`, `sys`

### Phase 2: Truecolor Theme Upgrade
**Rationale:** Theme enhancement is independent and low-risk. Extending existing `theme.py` with truecolor fallback provides immediate visual improvement without disrupting other modules.

**Delivers:**
- Truecolor detection via `COLORTERM` env var
- 3-tier Theme system with RGB/256-color/16-color fallback
- Panel-specific theme fields (panel_border, panel_heading, divider, status indicators)
- Theme dataclass extension with backward-compatible defaults

**Addresses:** PANEL-2 (truecolor compatibility)

**Stack elements:** ANSI truecolor escape sequences (`\033[38;2;R;G;Bm`), color approximation for 256-color fallback

**Avoids:** Breaking existing ANSI 16 theme users

### Phase 3: Panel Renderer Module
**Rationale:** Pure rendering module with no I/O creates testable, reusable component. Built on Phase 1 utilities, consumes Phase 2 theme. Can be developed/tested in isolation before TUI integration.

**Delivers:**
- `panels.py` with `render_status_panel()`, `render_device_panel()`, `render_actions_panel()`, `render_config_panel()`
- DeviceDisplayInfo dataclass for panel data contract
- Two-column layout calculation for actions panel
- Grouped device rendering (Registered/New/Blocked sections)

**Addresses:** Table stakes panel features from FEATURES.md

**Uses:** Phase 1 utilities for alignment, Phase 2 theme for styling

**Implements:** Pure rendering layer from ARCHITECTURE.md component map

### Phase 4: TUI Refactor to Use Panels
**Rationale:** Integrates panel renderer into existing TUI. Refactors `_render_menu()` without changing CLI interface. Preserves `--device KEY` bypass behavior.

**Delivers:**
- Panel-based main screen composition
- Config screen as separate view (replaces `_settings_menu()`)
- Letter-key action dispatch (F/A/C/S/R/Q)
- Status panel integration (last operation result)
- Device panel with connection status checks at draw time

**Addresses:** Table stakes for panel TUI workflow

**Avoids:** INT-1 (breaking existing CLI), INT-2 (bypassing Output protocol)

**Uses:** Phase 3 panels, Phase 2 theme

### Phase 5: Output Protocol Extension
**Rationale:** Small, focused addition to support batch flash step dividers. Extends Protocol and CliOutput consistently.

**Delivers:**
- `divider(label: str)` method in Output Protocol
- Implementation in CliOutput and NullOutput

**Addresses:** Batch flash output formatting

**Stack elements:** Simple string formatting with theme colors

### Phase 6: Batch Flash Architecture
**Rationale:** Depends on all foundation work. Two-phase architecture (build then flash) requires careful orchestration and service context decomposition. High complexity, built on stable base.

**Delivers:**
- `cmd_flash_all()` in `flash.py` with two-phase separation
- `_flash_device_only()` extracted from single-device flow (no service management)
- Per-device exception handling with result accumulation
- BatchFlashResult dataclass for summary

**Addresses:** Flash All table stakes, continue-on-failure, single service bracket

**Avoids:** PANEL-3 (partial completion info), PANEL-4 (build downtime), PANEL-11 (nested context)

**Implements:** Batch orchestrator from ARCHITECTURE.md

### Phase 7: Countdown Timer & Batch UX
**Rationale:** Adds safety countdown and summary table polish. Can start with simple Enter/Ctrl+C approach, upgrade to raw terminal keypress later.

**Delivers:**
- Countdown timer (configurable seconds, default 5s)
- Keypress cancel detection (platform-specific: `termios`+`select` on Unix, `msvcrt` on Windows)
- Batch flash summary table (Device/Status/Duration columns)
- Step dividers between devices

**Addresses:** Countdown safety (table stakes), summary table (differentiator)

**Avoids:** PANEL-7 (keypress detection), PANEL-10 (raw mode conflicts)

**Stack elements:** `termios`, `tty`, `select` (Unix), `msvcrt` (Windows), `time`

### Phase 8: Polish & Optimization
**Rationale:** Optional enhancements that don't affect core functionality. Can be deferred or delivered incrementally.

**Delivers:**
- Flash All: skip unchanged configs (SHA256 comparison)
- Spaced panel headers `[ D E V I C E S ]`
- Screen-aware layout (adaptive panel width)

**Addresses:** Differentiators from FEATURES.md

### Phase Ordering Rationale

- **Foundation first:** ANSI utilities and theme are prerequisites for all rendering. Building them first eliminates integration blockers.
- **Pure modules before integration:** Panel renderer is developed in isolation, then integrated into TUI. Testable components reduce debugging surface.
- **Batch architecture late:** Highest complexity, depends on stable foundation (panels, theme, output protocol extensions). Two-phase build/flash requires careful orchestration.
- **Polish last:** Skip-unchanged optimization and adaptive layout are valuable but not essential for MVP.

**Dependency chain:**
```
Phase 1 (ANSI utilities) ──> Phase 3 (panel renderer) ──> Phase 4 (TUI integration)
Phase 2 (theme) ──────────────────>│                            │
                                                                 │
Phase 5 (output protocol) ──> Phase 6 (batch flash) <───────────┘
                                    │
Phase 7 (countdown UX) ────────────>│
                                    │
Phase 8 (polish) ───────────────────>
```

### Research Flags

**Phases with standard patterns (low research need):**
- **Phase 1 (ANSI utilities):** Regex pattern for ANSI stripping is well-documented, stdlib terminal size detection proven.
- **Phase 2 (theme):** ANSI escape sequences are standardized (ECMA-48), truecolor detection convention is established.
- **Phase 5 (output protocol):** Simple protocol extension following existing pattern.

**Phases needing validation during planning:**
- **Phase 7 (countdown timer):** Platform-specific keypress detection has edge cases (terminal mode restoration on crash, SSH pseudo-terminal behavior). Validate with live SSH testing.

**Phases with high confidence, no research:**
- All other phases based on direct codebase analysis and established patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All stdlib, verified from Python docs and zen_mockup.py validation |
| Features | HIGH | KIAUH-style expectations verified, anti-features clearly documented |
| Architecture | HIGH | Direct codebase analysis, patterns derived from existing hub-and-spoke |
| Pitfalls | HIGH | Domain knowledge + codebase analysis, critical paths identified |

**Overall confidence:** HIGH

### Gaps to Address

**Terminal compatibility edge cases:**
- Some SSH clients (PuTTY with default settings) don't support truecolor. 3-tier fallback handles this, but needs live testing across terminals (PuTTY, kitty, Windows Terminal, tmux, screen).
- Terminal width detection on non-TTY contexts (piped output, cron) already handled by existing `sys.stdin.isatty()` checks, but panel rendering should gracefully degrade.

**Keypress detection platform quirks:**
- Raw terminal mode restoration on exception/signal. `atexit.register()` provides safety net, but SIGHUP during countdown needs testing.
- Start with Enter/Ctrl+C approach for MVP (simple, no raw mode), upgrade to keypress later.

**Batch flash error recovery:**
- If device 2 of 4 fails during build phase (BEFORE klipper stop), abort entire batch without stopping klipper (correct).
- If device 2 fails during flash phase (AFTER klipper stop), continue with devices 3-4 (correct).
- Needs clear user messaging about why some devices were skipped vs attempted.

**All gaps have mitigation strategies documented in PITFALLS.md.** No blockers, just implementation details to validate during development.

## Cross-Cutting Themes

### Safety Invariant: Klipper Always Restarts
Every code path (success, failure, exception, signal) must ensure klipper restarts. Batch flash must use single outer `klipper_service_stopped()` context, not per-device contexts. Existing context manager already provides try/finally safety; batch architecture must not undermine this.

### ANSI Width as Foundation
ANSI-aware string utilities are the single most important technical decision. Truecolor adds 19 invisible chars per token. Every padding/alignment calculation must use `display_width()`, never `len()`. This is not an optimization — it's a correctness requirement. Build these utilities FIRST, before any panel code.

### Progressive Enhancement, Not Replacement
Truecolor theme degrades to ANSI 16. Panel TUI only activates in interactive mode; `--device KEY` bypasses entirely. New features are additive, preserving existing CLI behavior. This maintains backward compatibility for automation.

### Build-Then-Flash Separation
Batch flash value proposition is efficiency: 4 devices × 3min each = 12min build + 4 devices × 30s each = 2min flash = 14min total. But only 2min klipper downtime instead of 14min. This architectural decision (build phase before flash phase) is what makes batch flash worth building.

## Top Recommendations (Prioritized)

1. **Build ANSI utilities first** — `strip_ansi()`, `display_width()`, `pad_to_width()` are prerequisites for all panel rendering. Without these, panels will be visually broken despite syntactically correct code. Test with BOTH color and no-color themes.

2. **Extract `_flash_device_only()` for batch** — Single-device flash currently uses `klipper_service_stopped()` internally. Batch flash needs flash-without-service-management. Extract this BEFORE implementing batch orchestrator to prevent nested context managers.

3. **Build all, then flash all** — Two-phase architecture (build with klipper running, flash with klipper stopped) is the core batch value. Design this separation into the orchestrator from day one. Don't optimize later — it's fundamental.

4. **3-tier theme fallback, never remove ANSI 16** — Truecolor detection is reliable but not universal. Always fall back to ANSI 16 as baseline. Test degradation path explicitly (set `COLORTERM=""` to force fallback).

5. **Continue on failure with result accumulation** — Batch flash must catch per-device exceptions and accumulate results. Summary table showing Device/Status/Duration is essential UX, not polish.

## Conflicts & Tensions

**Inherited stdio vs panel rendering:**
- `make` build uses inherited stdio (per existing conventions in SP-1, SP-5). Real-time compiler output is valuable feedback.
- Panel rendering works best with controlled output.
- **Resolution:** Suspend panels during build phase. Show step divider before build, let make output scroll naturally, show status panel after build completes. Don't fight inherited stdio.

**Truecolor aesthetics vs terminal compatibility:**
- Truecolor provides modern look, matches zen_mockup.py vision.
- Not all terminals support truecolor (PuTTY, old screen).
- **Resolution:** 3-tier fallback with `COLORTERM` detection. Truecolor is enhancement, not requirement.

**Batch efficiency vs safety:**
- Maximum efficiency: parallel flash (faster).
- Reality: USB serial is inherently sequential, parallel causes corruption.
- **Resolution:** Sequential flash with continue-on-failure. Build-then-flash separation provides efficiency win without parallel risk.

**Feature richness vs stdlib-only constraint:**
- Rich TUI libraries (`rich`, `blessed`, `textual`) provide polished UX.
- Project mandates zero external dependencies.
- **Resolution:** Print-and-clear panels with Unicode box drawing and truecolor ANSI. 80% of polish with 0% dependencies. Avoid curses (Windows issues, overkill for numbered menus).

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `tui.py`, `theme.py`, `service.py`, `output.py`, `flash.py`, `models.py` (existing patterns)
- Python stdlib documentation: `shutil`, `re`, `termios`, `tty`, `select`, `msvcrt`, `time`
- ECMA-48 standard (ANSI escape code specification)
- `.working/UI-working/zen_mockup.py` (validates truecolor rendering, escape format, palette)
- `CLAUDE.md` (architecture principles, hub-and-spoke, dataclass contracts)

### Secondary (MEDIUM confidence)
- KIAUH menu patterns (WebSearch results describe structure, exact source not fetched)
- `COLORTERM` env var convention for truecolor detection (common but not standardized)
- Evil Martians CLI UX patterns (progress display best practices)

### Tertiary (LOW confidence)
- None — all findings backed by primary sources or direct codebase analysis

---
*Research completed: 2026-01-29*
*Ready for roadmap: yes*
