# Project Research Summary

**Project:** kalico-flash v2.0
**Domain:** Python CLI firmware build/flash automation for Klipper 3D printers
**Researched:** 2026-01-26 (v2.0 features) | 2026-01-25 (v1.0 baseline)
**Confidence:** HIGH

## Executive Summary

kalico-flash v2.0 adds safety, verification, and UX improvements to the existing firmware flash workflow. Research shows the features fall into three categories: safety checks (print status, version detection), verification (post-flash device check), and polish (TUI menu, better errors, installation). The recommended approach is incremental enhancement of the existing hub-and-spoke architecture, preserving backward compatibility and the stdlib-only constraint.

The core insight: all new features should be gracefully degradable. Moonraker unavailable? Warn but allow flash. Post-flash verification fails? Show recovery steps. TUI unsupported? Fall back to simple numbered prompts. This philosophy prevents any v2.0 addition from breaking the core flash workflow that works reliably in v1.0.

Critical risks center on preserving existing CLI interfaces (automation must not break), avoiding module coupling (new modules must remain "leaves" in the architecture), and maintaining the klipper service restart invariant (still the #1 safety concern from v1.0). The research identified stdlib solutions for all requirements: urllib.request for Moonraker API, simple print/input for TUI menus, and time-based polling for post-flash verification.

## Key Findings

### Recommended Stack (v2.0 additions)

v2.0 requires no new external dependencies. All features can be implemented with Python 3.9+ stdlib modules that are already proven in the v1.0 codebase.

**Core technologies for v2.0:**
- `urllib.request` + `urllib.error` — Moonraker HTTP API calls (timeout 5s, graceful failure)
- `print()` + `input()` + Unicode box chars — Simple TUI menus (curses avoided due to Windows issues)
- `re` + `dataclasses` — Version parsing for git describe format (v0.12.0-85-gd785b396)
- `time.sleep()` + existing discovery.py — Post-flash device polling (2s intervals, 30s timeout)
- Bash script — Installation (symlink to ~/.local/bin, check PATH, verify Python 3.9+)

**Why not curses:** Windows compatibility issues, overkill for simple numbered menus, adds unnecessary complexity. The existing output.py pattern (print with phase labels) already works well.

**v1.0 stack preserved:**
- `argparse`, `subprocess`, `pathlib`, `json`, `hashlib`, `dataclasses`, `contextlib` — All proven patterns
- Context manager for service lifecycle remains the foundational safety pattern
- No external dependencies, no asyncio, no shell=True, no logging module

**Confidence:** HIGH — All recommendations verified against Python stdlib docs and Moonraker official API documentation.

### Expected Features (v2.0 additions)

**Must have (table stakes):**
- Print status check via Moonraker — Block flash if `print_stats.state` is "printing" or "paused"
- Post-flash verification — Poll for device reappearance with Klipper prefix, 30s timeout
- `--skip-menuconfig` flag — Use cached config without TUI (requires existing cache)
- Better error messages — Context + cause + numbered recovery steps for each error type
- Device exclusion — Registry flag to mark Beacon-like devices as non-flashable

**Should have (competitive):**
- TUI menu — Interactive device selection when run with no args (simple print-based, not curses)
- Version mismatch detection — Compare host vs MCU version via Moonraker, warn if different
- Installation script — Symlink to PATH with prerequisite checks

**Defer (v2+):**
- Colored output — Terminal compatibility varies, phase labels sufficient
- CAN bus support — Different discovery mechanism, separate tool
- Multi-device batch flash — Complex error recovery, one-at-a-time is safer
- Automatic Klipper git pull — Dangerous, user manages updates

**v1.0 table stakes preserved:**
All 10 v1.0 table stakes remain critical: USB discovery, JSON registry, menuconfig passthrough, config caching, build orchestration, dual flash methods, service lifecycle, error handling, --device flag, dry-run mode.

**Confidence:** HIGH (Moonraker API), MEDIUM (CLI UX patterns)

### Architecture Approach (v2.0 integration)

v2.0 follows the existing hub-and-spoke pattern. Three new modules are "leaves" that only import models.py and errors.py: moonraker.py (HTTP client for print status/version queries), tui.py (interactive menu wrapper), and messages.py (error message templates). Modified modules maintain existing interfaces to preserve backward compatibility.

**New modules:**
1. **moonraker.py** — MoonrakerClient class with timeout-wrapped urllib.request calls, graceful degradation
2. **tui.py** — Simple print-based menu with numbered selection, no curses dependency
3. **messages.py** — Error message templates with recovery guidance (lookup by error key)

**Modified modules (interface-preserving changes):**
4. **flash.py** — Hub orchestration adds Moonraker pre-check, post-flash verification call, new CLI flags
5. **registry.py** — Schema v2 adds `flashable: bool` and `moonraker_url: str` with backward-compat defaults
6. **flasher.py** — Adds verify_flash_success() function, service lifecycle unchanged
7. **build.py** — Adds optional `clean` parameter to run_build()
8. **discovery.py** — Adds filter_flashable_devices() helper
9. **models.py** — New dataclasses: PrintStatus, McuVersion, VerifyResult

**Key pattern preservation:**
- All new modules are leaves (only import models.py, errors.py)
- flash.py remains the sole orchestrator
- No cross-imports between feature modules
- Output goes through output.py protocol
- Service lifecycle context manager untouched (the foundational safety pattern)

**v1.0 architecture principles preserved:**
- Hub-and-spoke communication (orchestrator coordinates, modules don't call each other)
- DeviceEntry dataclass as shared contract
- Errors propagate upward (domain exceptions → orchestrator catches → user-friendly messages)
- Layer 0 (no deps) → Layer 1 (subprocess) → Layer 2 (orchestrator) build order

**Confidence:** HIGH (extends proven v1.0 architecture)

### Critical Pitfalls (v2.0 additions)

**New v2.0 pitfalls:**

1. **Breaking existing CLI interface (INT-1)** — TUI menu must only activate with no args + TTY. The `--device KEY` flag must continue to work identically for automation. Prevention: TUI is additive, bypass logic preserved, test with piped stdin.

2. **Moonraker connection failures (MOON-1, MOON-3)** — urllib.request can raise URLError, socket.timeout. print_stats.state interpretation is critical ("printing" and "paused" block, "standby"/"complete" allow). Prevention: Wrap all HTTP in try/except, fail open with warning, use correct field (print_stats.state not idle_timeout.state).

3. **Post-flash verification race conditions (VERIFY-1, VERIFY-5)** — Device takes 1-3 seconds to re-enumerate after flash. Klipper service restart may grab device during verification poll. Prevention: Initial 2s delay before polling, poll with 1s intervals for 30s total, verify AFTER klipper restart (not before).

4. **Version comparison logic errors (VER-3)** — String comparison "v0.9.0" > "v0.11.0" is wrong (lexicographic). Prevention: Parse to tuple of ints `(major, minor, patch)`, compare tuples numerically, handle missing tags gracefully.

5. **Module coupling creep (INT-5)** — Adding cross-imports between new modules breaks hub-and-spoke. Prevention: Code review imports at top of each file, only allow models.py and errors.py, flash.py is sole orchestrator.

6. **Schema migration breaks registry (EXCL-2)** — Adding `flashable: bool` to DeviceEntry breaks existing devices.json files. Prevention: Use `data.get("flashable", True)` with default, backward-compatible loading.

7. **TUI encoding failures (TUI-1)** — Unicode box-drawing characters render as garbage over SSH with incorrect terminal encoding. Prevention: Detect encoding with sys.stdout.encoding, provide ASCII fallback for non-UTF-8 terminals.

**v1.0 critical pitfalls still apply:**
- CP-1: Klipper service restart invariant (context manager with finally block)
- CP-2: Validate .config MCU type matches device registry
- CP-5: Atomic writes for all persistence (write to .tmp, verify, rename)
- CP-6: Re-verify device path exists immediately before flash
- SP-1: menuconfig requires inherited stdio
- SP-2: All make commands need cwd=klipper_dir
- SP-3: Never use shell=True (shell injection risk)
- SP-4: All subprocesses need timeouts except menuconfig

**Confidence:** HIGH (derived from domain knowledge + codebase analysis + verified web research)

## Cross-Cutting Themes

### 1. Graceful Degradation as Design Philosophy (NEW for v2.0)

Every v2.0 feature must fail open, never blocking the core flash workflow:
- Moonraker unreachable? Warn but allow flash (user may be recovering from crashed Klipper)
- Post-flash verification timeout? Show recovery steps, don't mark as failure
- Version detection fails? Log "unknown", continue without blocking
- TUI encoding issues? Fall back to ASCII, continue with simple menus

This differs from v1.0 safety-critical operations (klipper restart, config validation) which MUST block on failure.

### 2. Backward Compatibility as Non-Negotiable

Existing automation (scripts using `--device KEY`, cron jobs, SSH commands) must continue to work identically:
- `--device KEY` bypasses TUI entirely (current behavior preserved)
- No new prompts in non-interactive mode
- Exit codes unchanged
- Output format preserved (new features add, don't replace)

### 3. Interface Preservation Through Additive Design

Modified modules maintain existing function signatures:
- flash.py cmd_flash() gains optional parameters with defaults
- registry.py load() returns same RegistryData type, new fields optional
- flasher.py flash_device() unchanged, verify_flash_success() is separate function
- build.py run_build() gains optional clean parameter (default True = current behavior)

New functionality is always opt-in (flags, new functions) never changing existing behavior.

### 4. Subprocess Execution Patterns Remain First-Class Concern (v1.0 principle)

Four different subprocess patterns are needed:
1. **Interactive TUI** (menuconfig): inherited stdio, no timeout, check=False (user can cancel)
2. **Non-interactive build** (make): inherited stdio for streaming output, timeout=300s, check=True
3. **Critical services** (systemctl): captured output for error messages, timeout=30s, check=True
4. **Flash operations**: inherited stdio, timeout=120s, wrapped in service context manager

v2.0 adds fifth pattern:
5. **HTTP requests** (urllib.request): captured output, timeout=5s, graceful failure on URLError

### 5. Device Identity Stability vs. Firmware State (v1.0 principle, v2.0 extension)

The `/dev/serial/by-id/` symlink path contains firmware-determined strings:
- Running Klipper: `usb-Klipper_stm32h723xx_<serial>`
- Running Katapult: `usb-katapult_stm32h723xx_<serial>` (lowercase 'k')
- Hardware serial: `<serial>` portion is stable

v2.0 verification must handle prefix change: device disappears with Katapult prefix, reappears with Klipper prefix after successful flash.

### 6. Safety Through Language-Enforced Invariants (v1.0 principle preserved)

The tool's architecture centers on safety invariants enforced by language constructs:
- Klipper restart → enforced by context manager finally block (v1.0)
- Atomic file writes → enforced by temp-file-then-rename pattern (v1.0)
- Timeout guards → enforced by subprocess.run(timeout=N) on every call (v1.0)
- No shell injection → enforced by never using shell=True (v1.0)
- Graceful degradation → enforced by try/except with default returns (v2.0)

This is superior to documentation or code review because the language runtime guarantees the invariant.

## Top Recommendations (prioritized)

### v2.0 Specific Recommendations

1. **Implement Moonraker Check as Fail-Open**
   - HTTP calls in try/except with timeout=5s
   - URLError or timeout logs warning, returns None (not error)
   - Print status check continues if Moonraker unavailable
   - Only block flash if API confirms active print (printing/paused state)

2. **Preserve --device KEY Bypass Behavior**
   - TUI menu only activates when: (1) no args AND (2) sys.stdin.isatty()
   - --device KEY must skip all interactive prompts (current behavior)
   - Test: `echo "" | python flash.py --device key` should not prompt

3. **Use ASCII Fallback for TUI Box Drawing**
   - Check sys.stdout.encoding before drawing
   - If not UTF-8, use ASCII: `+`, `-`, `|` instead of Unicode box chars
   - Test over SSH with LANG=C to verify fallback

4. **Verify Device AFTER Klipper Restart, Not Before**
   - Verification polling happens after service.py restarts Klipper
   - Device may be locked by Klipper during verification (this is OK)
   - Success criteria: device reappeared with Klipper prefix (not locked/unlocked)

5. **Version Comparison Uses Tuple Parsing**
   - Parse "v0.12.0-85-gd785b396" to (0, 12, 0) tuple
   - Compare tuples: (0, 12, 0) > (0, 9, 0) = True
   - Handle parse failures gracefully (return "unknown", don't crash)

6. **Schema Evolution with Backward-Compat Defaults**
   - New fields use .get(key, default) in registry loading
   - Treat missing field as False (flashable) or sensible default (moonraker_url)
   - Write all fields on save to migrate forward

7. **Error Messages Follow Template Pattern**
   - messages.py defines templates with {context} placeholders
   - Each error includes: title, detail, numbered recovery steps
   - Call format_error(key, **context) for consistent messaging

### v1.0 Recommendations Preserved

8. **Service Lifecycle Context Manager Remains Foundation**
   - klipper_stopped() with finally block is untouchable
   - All v2.0 features must work within this pattern
   - No new code paths that bypass service restart guarantee

9. **Never Use shell=True (v1.0 principle)**
   - Applies to all new subprocess calls in v2.0 modules
   - Device paths and URLs from registry are user-controlled data

10. **Atomic Writes for All New Persistence (v1.0 principle)**
    - Applies to registry schema changes (devices.json)
    - Write to .tmp, verify, os.rename() to final name

## Conflicts & Tensions

### v2.0 Specific Tensions

1. **Feature Richness vs. Graceful Degradation**
   - Tension: Rich features (Moonraker check, version detection) vs. working on minimal systems
   - Resolution: All v2.0 features fail gracefully. If Moonraker unavailable, tool works like v1.0.

2. **TUI Polish vs. Compatibility**
   - Tension: Unicode box drawing looks nice vs. works everywhere (SSH, old terminals)
   - Resolution: ASCII fallback. Function over form. Detect encoding, adapt output.

3. **Backward Compatibility vs. Breaking Changes**
   - Tension: Clean new interface (TUI as default) vs. breaking automation
   - Resolution: TUI is opt-in (no args + TTY only). All existing flags work identically.

4. **Verification Strictness vs. Flash Reliability**
   - Tension: Post-flash verification strict (fail if device doesn't reappear) vs. false failures
   - Resolution: Verification warns on timeout, doesn't block. Show recovery steps, let user decide.

5. **Schema Evolution vs. Migration Pain**
   - Tension: Add new fields to DeviceEntry vs. breaking existing devices.json
   - Resolution: Backward-compatible defaults. Missing fields treated as False/default, not error.

### v1.0 Tensions Preserved

6. **Error Messages vs. Output Brevity** — Be verbose on failure, concise on success
7. **Config Caching Freshness vs. Safety** — Cache aggressively but validate (v2.0 adds --skip-menuconfig flag)
8. **Subprocess Timeout Values** — Conservative defaults for Pi 3 (slowest platform)
9. **Device Pattern Specificity vs. Convenience** — Auto-generate specific patterns, warn on collisions

## Implications for Roadmap

Based on research, suggested phase structure prioritizes safety (Moonraker check), then verification (post-flash), then polish (TUI, error messages, install).

### Phase 1: Moonraker Safety Check
**Rationale:** Highest safety value, prevents flash during active print. Addresses critical pitfall CP-3 (flashing during print). Can be standalone feature that fails gracefully.

**Delivers:**
- moonraker.py module with MoonrakerClient class
- Pre-flight Moonraker API query (timeout 5s)
- Block if print_stats.state is "printing" or "paused"
- Graceful failure if Moonraker unavailable (warn but continue)

**Addresses:** Print status check (table stakes from FEATURES.md)

**Avoids:** MOON-1 (connection refused), MOON-3 (state misinterpretation)

**Research flag:** MEDIUM — Moonraker API is well-documented, but testing requires live Moonraker instance. Phase should include integration testing with real printer.

### Phase 2: Post-Flash Verification
**Rationale:** Provides feedback on flash success. Uses existing discovery.py module with time-based polling. Independent of Phase 1.

**Delivers:**
- flasher.py verify_flash_success() function
- Wait for device reappearance after flash (30s timeout)
- Initial 2s delay, then poll every 1s
- Verify Klipper prefix (not Katapult bootloader)
- Display recovery steps on timeout (don't fail)

**Uses:** time.sleep(), discovery.scan_serial_devices()

**Avoids:** VERIFY-1 (premature check), VERIFY-3 (prefix confusion), VERIFY-5 (race with klipper restart)

**Research flag:** LOW — Polling patterns are standard, discovery module already tested.

### Phase 3: Skip Menuconfig Flag
**Rationale:** High value, low complexity. Builds on existing config.py caching. Enables fast repeat flashing.

**Delivers:**
- --skip-menuconfig flag in flash.py
- Error if no cached config for device
- Pass flag to build.py run_build()
- Preserves existing behavior (menuconfig always runs by default)

**Addresses:** Skip menuconfig (table stakes)

**Avoids:** CM-5 (config flow direction errors)

**Research flag:** LOW — Straightforward flag addition, no new concepts.

### Phase 4: Better Error Messages
**Rationale:** Improves all error paths. Foundation for remaining phases. Can be implemented as messages.py module with template lookup.

**Delivers:**
- messages.py with error templates
- Numbered recovery steps for each error type
- Context-aware formatting (device name, path, MCU type)
- Integration in flash.py error handlers

**Addresses:** Better error messages (table stakes)

**Avoids:** INT-4 (error message regression)

**Research flag:** LOW — Message writing is content work, not technical complexity.

### Phase 5: Device Exclusion
**Rationale:** Unblocks Beacon users. Simple registry schema change with backward-compat defaults.

**Delivers:**
- flashable: bool field in DeviceEntry (default True)
- Backward-compatible registry.py loading (use .get with default)
- discovery.py filter_flashable_devices() helper
- --add-device wizard prompt for exclusion

**Addresses:** Beacon probe exclusion (table stakes)

**Avoids:** EXCL-2 (schema migration)

**Research flag:** LOW — Schema evolution already tested in registry.py.

### Phase 6: TUI Menu
**Rationale:** Major UX improvement but not safety-critical. Depends on better error messages (Phase 4). Can be simple print-based menu first.

**Delivers:**
- tui.py module with numbered menu
- Interactive device selection on no args + TTY
- Action menu (flash, add, list, remove, exit)
- Unicode box drawing with ASCII fallback

**Uses:** print() + input() (no curses dependency)

**Avoids:** TUI-1 (encoding failures), INT-1 (breaking CLI), TUI-4 (screen corruption)

**Research flag:** MEDIUM — Terminal compatibility testing needed. ASCII fallback reduces risk, but SSH testing required.

### Phase 7: Version Detection
**Rationale:** Informational feature, lowest priority. Depends on Moonraker (Phase 1).

**Delivers:**
- Version parsing with regex (handle git describe format)
- Tuple comparison (0, 12, 0) vs (0, 9, 0)
- Query MCU version via Moonraker API
- Warn on mismatch (informational only, don't block)

**Uses:** re module for version parsing, Moonraker API for MCU version

**Avoids:** VER-1 (shallow clone), VER-3 (comparison logic), VER-4 (dirty suffix)

**Research flag:** MEDIUM — git describe parsing needs testing against real Kalico versions. Shallow clone edge case needs handling. Failure mode is informational-only (low risk).

### Phase 8: Installation Script
**Rationale:** One-time setup, improves distribution but not core functionality. Independent of all other phases.

**Delivers:**
- install.sh bash script
- Symlink to ~/.local/bin (or /usr/local/bin with sudo)
- PATH check with instructions
- Python 3.9+ version validation
- Idempotent (can run multiple times)

**Avoids:** INST-1 (permission denied), INST-2 (symlink exists), INST-4 (relative symlink)

**Research flag:** LOW — Standard Linux installation patterns.

### Phase Ordering Rationale

- **Safety first:** Moonraker check (Phase 1) prevents the worst failure mode (flash during print)
- **Verification second:** Post-flash check (Phase 2) provides confidence in flash success
- **Quick wins third:** Skip-menuconfig (Phase 3) is simple, high-value for repeat flashing
- **Foundation before features:** Better errors (Phase 4) before TUI (Phase 6) ensures good UX throughout
- **Low-risk next:** Device exclusion (Phase 5) is simple registry change
- **Complex features last:** TUI (Phase 6) depends on error messages, requires compatibility testing
- **Informational features last:** Version detection (Phase 7) is nice-to-have, not critical
- **Install script separate:** Phase 8 is distribution, not functionality, can be done anytime

**Dependency handling:**
- Phase 1 creates moonraker.py (used by Phase 7 for version query)
- Phase 4 creates messages.py (used by Phase 6 TUI for error display)
- Phase 3, 5, 8 are independent (can parallelize if desired)
- Phase 2 modifies flasher.py (coordinate with service lifecycle, no conflicts)

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Moonraker):** Requires live Moonraker testing, API endpoint validation, error condition testing (URLError, timeout, klippy not ready states)
- **Phase 6 (TUI):** Terminal encoding compatibility testing, Unicode fallback verification, SSH testing with various clients
- **Phase 7 (Version):** git describe format validation against real Kalico versions, shallow clone handling, dirty suffix parsing

Phases with standard patterns (skip research-phase):
- **Phase 2 (Verification):** Time-based polling is well-understood, discovery.py already tested
- **Phase 3 (Skip flag):** Straightforward argparse addition, flag passing pattern known
- **Phase 4 (Error messages):** Content writing, template pattern is standard Python
- **Phase 5 (Exclusion):** Schema evolution with defaults already proven in v1.0
- **Phase 8 (Install):** Standard Linux symlink patterns, well-documented

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | All stdlib solutions verified against Python docs, Moonraker official docs. urllib.request patterns proven. No external deps. |
| **Features** | HIGH | Moonraker API verified from official docs. CLI patterns are industry-standard. Feature list covers all v2.0 requirements from project brief. |
| **Architecture** | HIGH | Extends proven v1.0 hub-and-spoke pattern. No new architectural patterns. New modules follow same "leaf" design. Interface preservation validated. |
| **Pitfalls** | HIGH | Derived from domain knowledge + codebase analysis + verified web research. v1.0 pitfalls still apply. v2.0 adds 7 new pitfalls with concrete prevention. |

**Overall confidence:** HIGH

Research is comprehensive and actionable. All technical questions have stdlib solutions. Architecture preserves existing patterns. Pitfalls have concrete prevention strategies. v2.0 builds incrementally on proven v1.0 foundation.

### Gaps to Address

**Minor gaps to handle during implementation:**

- **Terminal encoding edge cases:** Unicode box drawing fallback logic needs live SSH testing with various clients (PuTTY, iTerm, Windows Terminal). Recommendation: Implement ASCII fallback first (works everywhere), add Unicode as enhancement.

- **Moonraker API version variance:** Different Moonraker versions may have slightly different response schemas or field names. Recommendation: Use .get() with defaults for all API field access, never assume presence.

- **Kalico vs Klipper version format:** Kalico fork may use different git describe format than mainline Klipper (different tag prefixes, branch naming). Recommendation: Version parsing regex should be flexible (handle v prefix optional, commit count optional), gracefully return "unknown" on parse failure.

- **Git shallow clone version detection:** git describe fails on shallow clones (common in Docker, some install scripts). Recommendation: Catch subprocess.CalledProcessError, fall back to reading .version file or git log --oneline -1, return "unknown" if all fail (never crash).

**No blocking gaps:** All features can be implemented with available information. Edge cases are handled via graceful degradation (the v2.0 design philosophy). If a feature can't operate (Moonraker unavailable, git missing, terminal encoding wrong), tool degrades to v1.0 behavior or ASCII output, never crashes.

## Sources

### Primary (HIGH confidence)
- [Moonraker Printer Administration API](https://moonraker.readthedocs.io/en/latest/external_api/printer/) — print_stats endpoint, state values, query endpoint
- [Moonraker Printer Objects](https://moonraker.readthedocs.io/en/latest/printer_objects/) — mcu object, version fields, status reference
- [Python urllib.request documentation](https://docs.python.org/3/library/urllib.request.html) — HTTP client patterns, timeout handling, URLError exceptions
- [Python curses documentation](https://docs.python.org/3/library/curses.html) — Windows limitations verified (not available without third-party wheel)
- kalico-flash v1.0 codebase (flash.py, registry.py, discovery.py, models.py, errors.py, service.py, output.py) — Architecture patterns, existing interfaces, dataclass contracts
- Python 3.9+ stdlib documentation (re, time, dataclasses, contextlib)

### Secondary (MEDIUM confidence)
- [Klipper Status Reference](https://www.klipper3d.org/Status_Reference.html) — MCU object structure, print_stats fields
- [CLI Guidelines](https://clig.dev/) — Error message best practices, recovery steps format
- [Unicode box drawing characters](https://pythonadventures.wordpress.com/2014/03/20/unicode-box-drawing-characters/) — Terminal rendering, ASCII fallback patterns
- Community forums (Klipper discourse, Voron) — Real-world failure modes, user pain points with manual flash workflow

### Tertiary (LOW confidence)
- [PEP 440 Version Identification](https://peps.python.org/pep-0440/) — Version comparison (not directly applicable, git describe format differs from PEP 440)

---
*Research completed: 2026-01-26 (v2.0) | 2026-01-25 (v1.0)*
*Ready for roadmap: yes*
