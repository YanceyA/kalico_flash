# Project Research Summary

**Project:** kalico-flash v3.2 (Visual Dividers)
**Domain:** Terminal CLI tool for embedded firmware building and flashing
**Researched:** 2026-01-30
**Confidence:** HIGH

## Executive Summary

kalico-flash is a mature Python CLI tool for automating Klipper firmware builds and flashing to USB-connected MCU boards on Raspberry Pi. The current milestone (v3.2) focuses on adding lightweight visual dividers to improve output scannability during multi-step workflows (flash, add-device, remove-device, flash-all). These dividers use Unicode box-drawing characters (┄, ─) with ASCII fallback, themed with truecolor ANSI escapes, and placed strategically between workflow phases and devices.

The recommended approach is stdlib-only implementation (no external dependencies), leveraging existing theme and output systems. Use `shutil.get_terminal_size()` for dynamic width detection, `ansi.display_width()` for ANSI-aware padding, and extend the Output Protocol to add `step_divider()` and `device_divider()` methods. The panel-based TUI foundation from v2.1 and theme system provide truecolor support, Unicode fallback detection, and consistent styling infrastructure that dividers can inherit.

The key risk is visual noise from over-dividing. Mitigation: apply dividers only between major sections (phase boundaries, device switches) using lightweight dashed `┄` for steps and labeled solid `─` for multi-device batches. Critical technical pitfalls include NullOutput protocol violations (add methods to all Output implementations), hardcoded widths breaking on terminal resize (use per-divider width detection), and ANSI escapes leaking into piped output (use theme.border which respects ColorTier fallback).

## Key Findings

### Recommended Stack

The v3.2 divider feature builds on existing stdlib infrastructure with no new dependencies. All required capabilities exist in Python 3.9+ stdlib and the current codebase.

**Core technologies:**
- **shutil.get_terminal_size()**: Dynamic terminal width detection with fallback — call per-divider, not cached at startup
- **re module**: ANSI escape stripping for width calculations — already abstracted in `ansi.display_width()`
- **Unicode box-drawing characters**: Standard U+2500 block (┄ U+2504, ─ U+2500) — detect encoding via existing `_supports_unicode()` in tui.py
- **Existing theme system**: Truecolor ANSI escapes with 3-tier fallback (truecolor → ANSI16 → no-color) — dividers inherit `theme.border` (100,160,180 RGB muted teal)
- **Output Protocol abstraction**: CliOutput and NullOutput implementations — extend with divider methods to maintain pluggability

**Key implementation decisions:**
- **Fixed 60-character width for MVP**, defer adaptive width to v3.3+ (reduces edge-case complexity)
- **Light dashed ┄ for step dividers**, solid ─ for device-labeled dividers (visual hierarchy)
- **ASCII fallback**: ┄ → "- " (dash-space pattern), ─ → "-" (solid dashes) when UTF-8 unavailable
- **Placement rules**: Before prompts, between workflow phases, per-device in flash-all — never during countdown timers or in error output

### Expected Features

Research identified clear "must-have" vs "nice-to-have" divider features based on professional CLI patterns (Docker, Yarn, npm/inquirer.js).

**Must have (table stakes):**
- Simple dividers before prompts — separates user action from system output
- Dividers between workflow phases — Discovery → Config → Build → Flash need visual breaks
- Device-labeled dividers in flash-all — `─── 1/2 Octopus Pro ───` for multi-device clarity
- Unicode detection with ASCII fallback — can't break on legacy SSH terminals

**Should have (competitive):**
- Adaptive terminal width — dividers span edge-to-edge, but acceptable to ship with fixed 60-char width initially
- Step-labeled dividers in flash-all — show step count like Docker ("step 1, step 2, step 3")
- Quiet mode respected — dividers disappear when --quiet flag is used (future)
- Colored dividers — inherit theme.border for visual coherence with panels

**Defer (v3.3+):**
- Theme-specific divider characters — wait to see if theme system expands
- Section headers with dividers — may conflict with panel-based TUI if both visible
- Divider style customization in settings — not requested, defer until user need

**Anti-features (explicitly excluded):**
- Fancy Unicode art — breaks on ASCII-only terminals, looks busy, hard to grep
- Progress bars inside dividers — clutters divider area, redraws create flicker
- Colored dividers per status (green/red) — changing color breaks consistency, use status markers instead
- Animated dividers — terminal redraws are jarring, breaks scrollback
- Multi-line dividers (boxes around steps) — doubles vertical space, harder to scan

### Architecture Approach

The v3.2 divider feature is a targeted Output Protocol extension. No new modules required. Dividers integrate into existing workflows via the output abstraction layer.

**Component modifications:**
1. **output.py (Output Protocol)** — Add `step_divider()` and `device_divider(label, index, total)` methods to Protocol, CliOutput, and NullOutput
2. **flash.py (orchestrator)** — Call dividers between workflow phases in cmd_flash, cmd_add_device, cmd_remove_device, cmd_flash_all
3. **tui.py (TUI menu)** — Add dividers before prompts, ensure countdown timer code paths avoid mid-timer dividers
4. **theme.py (styling)** — Dividers consume existing `theme.border` color (no changes needed, already defined)

**Data flow:**
```
flash.py cmd_flash():
  out.phase("Discovery")
  # ... discovery logic ...
  out.step_divider()              # NEW

  out.phase("Config")
  # ... config logic ...
  out.step_divider()              # NEW

  out.phase("Build")
  # ... build logic ...
  out.step_divider()              # NEW

  out.phase("Flash")
  # ... flash logic ...

flash.py cmd_flash_all():
  for i, device in enumerate(devices):
    out.device_divider(device.name, i+1, total)  # NEW
    # ... build + flash device ...
```

**Why no new module:** Dividers are output formatting, not business logic. They belong in the output abstraction layer (output.py) and are called by orchestration logic (flash.py). A separate `dividers.py` module would over-engineer a simple feature.

**Key architectural constraint:** NullOutput must implement all new Protocol methods (pass-through no-ops). This maintains output pluggability for testing and future Moonraker integration. Protocol violations surface at runtime, not compile time, so explicit verification is critical.

### Critical Pitfalls

From PITFALLS.md, the top 5 risks for v3.2 divider implementation:

1. **NullOutput Protocol Violation (DIV-2)** — Adding divider methods to CliOutput but forgetting NullOutput. Protocol violations break testing and future integrations. **Prevention:** Add to Protocol, CliOutput, AND NullOutput in same commit. NullOutput methods should be pass-through (pass), not NotImplementedError.

2. **Hardcoded Width Breaking on Terminal Resize (DIV-1)** — Fixed character count dividers (`"─" * 80`) break when SSH terminal resizes mid-workflow. **Prevention:** Use `shutil.get_terminal_size()` per-divider (already abstracted in `ansi.get_terminal_width()`), fall back to 40 columns minimum.

3. **ANSI Escapes in Redirected Output (DIV-3)** — Colored dividers leak `^[[38;2;100;160;180m` garbage into piped output or log files. **Prevention:** Use `theme.border` (not hardcoded ANSI codes) — theme system already respects ColorTier.NONE for non-TTY contexts.

4. **Unicode Without ASCII Fallback (DIV-4)** — Box-drawing characters (┄, ─) fail on degraded terminals (old SSH clients, Windows CMD, misconfigured locales) showing `?` or mojibake. **Prevention:** Detect encoding via existing `_supports_unicode()` in tui.py, provide ASCII alternatives (`- ` and `-`).

5. **Over-Dividing Creates Visual Noise (DIV-6)** — Adding dividers everywhere clutters output, harder to scan. The Minimalist Zen aesthetic is compromised. **Prevention:** Dividers only between major sections (phase boundaries, device switches). Light dashed ┄ for steps — visually quieter than solid lines.

**Additional high-impact pitfall:**
- **Dividers Interfering with Countdown Timer (DIV-5)** — If dividers print during countdown's `\r` in-place update, the countdown shows multiple lines instead of updating one line. **Prevention:** Never print dividers between countdown start and completion. Place dividers AFTER sections complete.

## Implications for Roadmap

Based on research, suggested phase structure for v3.2:

### Phase 1: Design Specification
**Rationale:** Define clear placement rules before implementation to avoid over-dividing pitfall (DIV-6). The research shows professional CLI tools use dividers sparingly — Docker between build steps, npm/inquirer for menu separators. kalico-flash needs explicit rules for where dividers appear.

**Delivers:**
- Placement rules documented: "dividers before prompts, between workflow phases, per-device in flash-all, never during countdowns or in errors"
- Visual hierarchy defined: light dashed ┄ for steps, solid ─ for device labels
- Character decisions: Unicode ┄/─ with ASCII fallback - / -

**Avoids:** DIV-6 (over-dividing creating visual noise)

**Research flag:** No additional research needed — decisions made based on CLI pattern research (Docker, Yarn, inquirer.js).

---

### Phase 2: Core Divider Implementation
**Rationale:** Implement divider methods in output abstraction layer first. This is the foundation all other phases depend on. Early implementation allows testing in isolation before integrating into workflows.

**Delivers:**
- Output Protocol extended: add `step_divider()` and `device_divider(label, index, total)` methods
- CliOutput implementation: Unicode box-drawing with theme.border color, ANSI-aware padding
- NullOutput implementation: pass-through no-ops (satisfy Protocol contract)
- Terminal width detection: use `ansi.get_terminal_width()` per-divider, fall back to 40 cols
- ASCII fallback: check `_supports_unicode()`, provide dash alternatives

**Uses:**
- shutil.get_terminal_size() (stdlib)
- ansi.display_width() (existing utility)
- theme.border (existing theme system)

**Avoids:**
- DIV-2 (NullOutput protocol violation) — implement in same commit
- DIV-1 (hardcoded width) — dynamic width detection
- DIV-3 (ANSI in redirected output) — use theme.border
- DIV-10 (ANSI width calculation) — use display_width() from day one

**Research flag:** No additional research needed — all stack elements verified (STACK.md).

---

### Phase 3: Workflow Integration
**Rationale:** Add dividers to all command entry points systematically. Must audit all workflows (flash, add-device, remove-device, list-devices, flash-all) to ensure consistency. Inconsistent divider presence confuses users (DIV-7).

**Delivers:**
- cmd_flash: dividers between Discovery, Config, Build, Flash phases
- cmd_add_device: dividers before wizard prompts
- cmd_remove_device: dividers before confirmation prompt
- cmd_flash_all: device-labeled dividers per device
- tui.py menu: dividers between panel and action output

**Implements:** Placement rules from Phase 1

**Avoids:**
- DIV-7 (inconsistent placement across workflows)
- DIV-5 (dividers during countdown timer) — audit TUI countdown code paths
- DIV-9 (dividers in error output) — audit error handling paths

**Research flag:** No additional research needed — integration points clear from codebase analysis (ARCHITECTURE.md).

---

### Phase 4: Edge Cases & Validation
**Rationale:** Handle degraded terminals, long device names, and redirected output. These are the edge cases that break in production SSH environments (Raspberry Pi with varied SSH clients, locale configurations).

**Delivers:**
- Encoding detection: ASCII fallback when UTF-8 unavailable
- Device name truncation: labeled dividers with 50+ char device names fit in 80 cols
- Piped output test: verify `kflash --list-devices > file.txt` has no escape codes when NO_COLOR=1
- Terminal width edge cases: test at 40, 80, 120+ column widths
- Countdown timer integrity: verify timer stays on one line with dividers present

**Avoids:**
- DIV-4 (Unicode without fallback)
- DIV-8 (labeled divider overflow)
- DIV-3 (ANSI in redirected output)

**Research flag:** No additional research needed — edge cases identified in PITFALLS.md.

---

### Phase Ordering Rationale

- **Design first (Phase 1)** avoids rework. Divider placement decisions are UX-critical and inform all implementation.
- **Output layer before workflow integration (Phase 2 → 3)** allows isolated testing. Methods work correctly before wiring into 5+ command entry points.
- **Edge cases last (Phase 4)** because they're validation, not core functionality. The divider feature works on modern terminals after Phase 3 — Phase 4 ensures it works everywhere.

**Dependency order:**
```
Phase 1 (rules) → Phase 2 (methods) → Phase 3 (integration) → Phase 4 (validation)
                         ↓
                  NullOutput must be implemented here (same commit as CliOutput)
```

### Research Flags

**All phases have standard patterns (skip research-phase):**
- **Phase 1 (Design):** CLI divider patterns researched (FEATURES.md sources: Docker, Yarn, inquirer.js). Decisions documented.
- **Phase 2 (Implementation):** Stdlib APIs verified (shutil, re), existing utilities confirmed (ansi.py, theme.py). Stack complete (STACK.md).
- **Phase 3 (Integration):** Codebase analysis complete (ARCHITECTURE.md). All entry points identified (flash.py, tui.py).
- **Phase 4 (Validation):** Edge cases identified (PITFALLS.md). Test scenarios defined.

No phase requires deeper research. All decisions can be made from existing research artifacts.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All stdlib APIs verified (shutil, re). Existing codebase utilities confirmed (ansi.py, theme.py). Zero new dependencies. |
| Features | HIGH | CLI divider patterns verified from Docker, Yarn, npm/inquirer.js. Table stakes vs differentiators clearly defined. Anti-features explicitly documented. |
| Architecture | HIGH | Direct codebase analysis of output.py, flash.py, tui.py. Component boundaries clear. No new modules required — Output Protocol extension only. |
| Pitfalls | HIGH | 10 specific pitfalls identified from terminal output research, ANSI handling, Protocol patterns, and SSH environment constraints. Prevention strategies documented per pitfall. |

**Overall confidence:** HIGH

### Gaps to Address

No major gaps remain. All decisions can be made from current research. Minor validation points:

- **Theme.border color intensity:** Mockup shows muted teal (100,160,180 RGB). Verify this is visible on dark terminals during Phase 2 testing. If too dim, adjust to (120,180,200) RGB.

- **Countdown timer code path audit:** Phase 3 requires explicit code review of `tui.py` countdown implementation. Research identifies the risk (DIV-5) but doesn't provide line numbers. Implementation must trace all code paths that call the countdown timer and verify dividers don't interrupt.

- **SSH terminal encoding edge case:** Research assumes `_supports_unicode()` check (LANG/LC_ALL env vars) is sufficient for UTF-8 detection. If users report mojibake on Raspberry Pi SSH, may need to add `sys.stdout.encoding` check as additional signal. Defer until user reports — env var check is industry standard.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis** — Direct inspection of output.py, theme.py, ansi.py, flash.py, tui.py. Output Protocol structure, theme system, existing utilities, command entry points all verified.
- **Python stdlib documentation** — shutil.get_terminal_size(), re module, sys.stdout.encoding verified from official Python 3.9+ docs.
- **Unicode consortium** — Box Drawing block (U+2500-U+257F) verified from official Unicode charts. Characters ┄ (U+2504), ─ (U+2500) confirmed in standard.

### Secondary (MEDIUM confidence)
- **CLI pattern research** — Docker build output (Step 1/6 pattern), Yarn install output (phase labels), npm inquirer.js (Separator class) patterns verified from documentation and GitHub repositories.
- **Terminal separator scripts** — Community patterns for terminal width detection and separator rendering from GitHub (pjnadolny/separator) and CommandLineFu.
- **CLI UX best practices** — Evil Martians CLI UX article on progress displays, clig.dev guidelines on error messages and recoverable operations.

### Tertiary (LOW confidence)
- **Visual hierarchy in UI** — Generic UX principles (blog.tubikstudio.com visual dividers article, setproduct.com steps UI design). Principles applied but source authority limited to general design guidance, not terminal-specific.

---
*Research completed: 2026-01-30*
*Ready for roadmap: yes*
