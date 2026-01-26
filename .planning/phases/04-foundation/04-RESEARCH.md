# Phase 4: Foundation - Research

**Researched:** 2026-01-26
**Domain:** CLI workflow enhancement (skip menuconfig, device exclusion, error messages)
**Confidence:** HIGH

## Summary

This phase adds three interconnected features to the kalico-flash CLI: a `--skip-menuconfig` flag for power users who want to bypass the TUI when a cached config exists, device exclusion to mark devices (like Beacon probes) as non-flashable, and standardized error messages with recovery guidance.

All three features are implementable using Python 3.9+ stdlib only. The existing codebase architecture (hub-and-spoke pattern, dataclass contracts, Output protocol) provides clean extension points for each feature. No external dependencies are required.

**Primary recommendation:** Implement features in this order: (1) error message framework first (affects all user-facing code), (2) device exclusion (schema change with backward compatibility), (3) skip menuconfig flag (depends on existing config.py infrastructure).

## Standard Stack

This phase uses only Python standard library, as required by the project constraints.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| argparse | stdlib | CLI argument parsing | Already in use, short flag support built-in |
| dataclasses | stdlib | Data contracts | Already in use for DeviceEntry, etc. |
| textwrap | stdlib | Error message formatting | Wraps text to 80 columns, preserves indentation |
| json | stdlib | Registry persistence | Already in use for devices.json |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| os | stdlib | Terminal width detection | `os.get_terminal_size()` for dynamic width |
| pathlib | stdlib | Path handling | Already in use throughout codebase |
| fnmatch | stdlib | Pattern matching | Already in use for serial pattern matching |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual text wrapping | textwrap module | textwrap handles edge cases (long words, indentation) |
| Custom flag parsing | argparse | argparse is standard, well-tested, already in use |
| Exception notes (3.11+) | Exception attributes | 3.11+ features not available in Python 3.9 target |

**Installation:**
No additional installation required - all stdlib.

## Architecture Patterns

### Recommended Project Structure

No new files needed. Existing structure accommodates all changes:

```
kalico-flash/
├── flash.py       # Add -s/--skip-menuconfig, --exclude-device, --include-device
├── models.py      # Add flashable: bool to DeviceEntry
├── errors.py      # Enhance exceptions with context and recovery guidance
├── output.py      # Add error_with_recovery() method to Output protocol
├── registry.py    # Handle flashable field in load/save (backward compatible)
├── config.py      # Already has has_cached_config(), validate_mcu()
├── discovery.py   # Filter out non-flashable devices in find_registered_devices()
└── devices.json   # Evolves to include "flashable" field per device
```

### Pattern 1: Backward-Compatible Schema Evolution

**What:** Adding optional fields to JSON schema without breaking existing files.
**When to use:** When evolving devices.json to add `flashable` field.
**Example:**
```python
# Source: Python dataclasses documentation
# In models.py - add flashable with default True
@dataclass
class DeviceEntry:
    key: str
    name: str
    mcu: str
    serial_pattern: str
    flash_method: Optional[str] = None
    flashable: bool = True  # New field with backward-compatible default

# In registry.py - handle missing field gracefully
devices[key] = DeviceEntry(
    key=key,
    name=data["name"],
    mcu=data["mcu"],
    serial_pattern=data["serial_pattern"],
    flash_method=data.get("flash_method"),
    flashable=data.get("flashable", True),  # Default to True if missing
)
```

### Pattern 2: Short and Long Flag Pairing

**What:** Adding short aliases (`-s`, `-d`) to existing long flags.
**When to use:** For frequently-used flags that benefit from brevity.
**Example:**
```python
# Source: Python argparse documentation
parser.add_argument(
    "-s", "--skip-menuconfig",
    action="store_true",
    help="Skip menuconfig if cached config exists",
)
parser.add_argument(
    "-d", "--device",
    metavar="KEY",
    help="Device key to build and flash",
)
```

### Pattern 3: Error Messages with Recovery Guidance

**What:** Structured error messages that include context, explanation, and recovery steps.
**When to use:** All error paths in the CLI.
**Example:**
```python
# Source: Command Line Interface Guidelines (clig.dev)
# Error output should fit 80 columns, include context, and guide recovery

def format_error(
    error_type: str,
    message: str,
    context: dict,
    recovery: str,
) -> str:
    """Format an error message with context and recovery guidance.

    Output format (plain ASCII, no color, 80-column):

    [FAIL] Device not found: octopus-pro

    The device 'octopus-pro' is not registered. This can happen if the
    device was removed or if the device key was mistyped.

    To see registered devices, run `python flash.py --list-devices`. To
    register a new device, run `python flash.py --add-device`.
    """
    lines = [f"[FAIL] {error_type}: {message}"]
    lines.append("")

    # Wrap context and recovery to 80 columns
    import textwrap
    if context:
        context_text = " ".join(f"{k}={v}" for k, v in context.items())
        lines.extend(textwrap.wrap(context_text, width=80))

    if recovery:
        lines.append("")
        lines.extend(textwrap.wrap(recovery, width=80))

    return "\n".join(lines)
```

### Pattern 4: Filtered Device Lists for Selection

**What:** Showing excluded devices in selection menus but preventing their selection.
**When to use:** Interactive device selection when non-flashable devices exist.
**Example:**
```python
# Show all devices but only allow selecting flashable ones
for i, (entry, device) in enumerate(matched):
    if entry.flashable:
        out.device_line(str(i + 1), f"{entry.key} ({entry.mcu})", device.path)
    else:
        out.device_line("--", f"{entry.key} [excluded]", "(not flashable)")

# Filter to flashable devices for selection
flashable_matched = [(e, d) for e, d in matched if e.flashable]
```

### Anti-Patterns to Avoid

- **Generic error messages:** Never output "Operation failed" without context. Always include what failed, why, and how to recover.
- **Color/Unicode in errors:** Project decision requires plain ASCII only, no ANSI escape codes.
- **Breaking backward compatibility:** Never remove fields from devices.json. Add new fields with defaults.
- **Silent failures:** Never swallow exceptions. Always propagate with added context.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text wrapping to 80 columns | Manual line splitting | `textwrap.wrap()` or `textwrap.fill()` | Handles long words, indentation, edge cases |
| Short flag parsing | Manual argv parsing | argparse `-s` syntax | Already in use, handles help generation |
| JSON field defaults | Manual dict.get() everywhere | Dataclass default values + registry.load() | Consistent, type-checked, single source of truth |

**Key insight:** The stdlib textwrap module handles all the edge cases for 80-column formatting that would be tedious to implement manually (words longer than width, preserving indentation, handling existing newlines).

## Common Pitfalls

### Pitfall 1: Dataclass Field Ordering

**What goes wrong:** Adding a field with a default before a field without a default causes TypeError.
**Why it happens:** Python dataclass __init__ requires non-default arguments before default arguments.
**How to avoid:** Always add new fields with defaults at the END of the dataclass, or give all existing fields defaults.
**Warning signs:** `TypeError: non-default argument 'X' follows default argument`

### Pitfall 2: Shared Mutable Default Values

**What goes wrong:** Using `flashable: list = []` shares the list across all instances.
**Why it happens:** Default values are evaluated once at class definition time.
**How to avoid:** Use `field(default_factory=list)` for mutable defaults. For this phase, `flashable: bool = True` is immutable and safe.
**Warning signs:** Changes to one instance affect others unexpectedly.

### Pitfall 3: Silent Config Validation Skip

**What goes wrong:** Skip menuconfig flag skips MCU validation too, leading to firmware mismatch.
**Why it happens:** Developer assumes "skip config" means "skip all config-related steps."
**How to avoid:** Always run MCU validation regardless of skip flag. The flag only skips the TUI, not validation.
**Warning signs:** User flashes wrong firmware because cached config was for different MCU.

### Pitfall 4: Error Message Line Length Overflow

**What goes wrong:** Error messages exceed 80 columns when context is long.
**Why it happens:** String concatenation without width checking.
**How to avoid:** Use `textwrap.fill(text, width=80)` for all prose in error messages. Diagnostic commands can be on their own line.
**Warning signs:** Messages wrap awkwardly in terminal or truncate important information.

### Pitfall 5: Excluded Device Still Selected via --device Flag

**What goes wrong:** User explicitly passes `--device beacon` for an excluded device, expecting override.
**Why it happens:** Exclusion check only in interactive selection, not explicit device lookup.
**How to avoid:** Check `flashable` flag in BOTH interactive selection AND explicit `--device` lookup. Per CONTEXT.md decision: hard error with no override.
**Warning signs:** User confused when device appears in `--list-devices` but cannot be flashed.

## Code Examples

Verified patterns from official documentation:

### Adding Short Flags to argparse

```python
# Source: https://docs.python.org/3/library/argparse.html
parser.add_argument(
    "-s", "--skip-menuconfig",
    action="store_true",
    help="Skip menuconfig if cached config exists",
)

parser.add_argument(
    "-d", "--device",
    metavar="KEY",
    help="Device key to build and flash",
)

# Exclusion management (not mutually exclusive - can run separately)
parser.add_argument(
    "--exclude-device",
    metavar="KEY",
    help="Mark a device as non-flashable",
)
parser.add_argument(
    "--include-device",
    metavar="KEY",
    help="Mark a device as flashable",
)
```

### Backward-Compatible JSON Load

```python
# Source: Python dataclasses documentation
# Registry.load() with backward-compatible field handling

for key, data in raw.get("devices", {}).items():
    devices[key] = DeviceEntry(
        key=key,
        name=data["name"],
        mcu=data["mcu"],
        serial_pattern=data["serial_pattern"],
        flash_method=data.get("flash_method"),
        flashable=data.get("flashable", True),  # Backward compatible
    )
```

### Text Wrapping for Error Messages

```python
# Source: https://docs.python.org/3/library/textwrap.html
import textwrap

def wrap_error_prose(text: str, width: int = 80) -> str:
    """Wrap prose text to specified width, preserving paragraphs."""
    paragraphs = text.split("\n\n")
    wrapped = [textwrap.fill(p, width=width) for p in paragraphs]
    return "\n\n".join(wrapped)

# Usage in error output
recovery = (
    "The device 'octopus-pro' is registered but marked as non-flashable. "
    "Non-flashable devices cannot be flashed to prevent accidental damage. "
    "To make this device flashable, run `python flash.py --include-device octopus-pro`."
)
print(wrap_error_prose(recovery, width=80))
```

### Checking Cached Config Existence

```python
# Source: Existing config.py has_cached_config() method
from config import ConfigManager

config_mgr = ConfigManager(device_key, klipper_dir)

if args.skip_menuconfig:
    if config_mgr.has_cached_config():
        # Load cached config and skip TUI
        config_mgr.load_cached_config()
        out.phase("Config", f"Using cached config for {device_key}")
    else:
        # Warn and launch menuconfig anyway (per CONTEXT.md decision)
        out.warn(f"No cached config for '{device_key}', launching menuconfig")
        # Fall through to menuconfig
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Generic exception messages | Exceptions with context attributes | Always best practice | Better debugging, user guidance |
| Hardcoded column width | `os.get_terminal_size()` fallback to 80 | Python 3.3+ | Adaptive formatting |
| Exception notes (add_note) | Not available | Python 3.11+ | Can't use in 3.9 target |

**Deprecated/outdated:**
- Exception `add_note()` method: Available in Python 3.11+ but project targets 3.9, so use exception attributes instead

## Open Questions

Things that couldn't be fully resolved:

1. **Exact error message wording**
   - What we know: Format is defined (prose paragraphs, 80 columns, diagnostic commands inline)
   - What's unclear: Exact wording for each error category (ERR-06 lists 6 categories)
   - Recommendation: Planner should define error templates, implementer refines wording during implementation

2. **Interactive selection with only excluded devices**
   - What we know: Excluded devices shown with [excluded] marker, not selectable
   - What's unclear: What happens when ALL connected registered devices are excluded?
   - Recommendation: Error with message "No flashable devices connected. Found N excluded device(s)." followed by list

## Sources

### Primary (HIGH confidence)
- [Python argparse documentation](https://docs.python.org/3/library/argparse.html) - short flags, metavar, mutually exclusive groups
- [Python dataclasses documentation](https://docs.python.org/3/library/dataclasses.html) - field defaults, ordering rules
- [Python textwrap documentation](https://docs.python.org/3/library/textwrap.html) - wrap(), fill(), TextWrapper

### Secondary (MEDIUM confidence)
- [Command Line Interface Guidelines](https://clig.dev/) - error message best practices, exit codes, stderr usage
- Existing codebase (flash.py, models.py, errors.py, config.py, registry.py) - architecture patterns, extension points

### Tertiary (LOW confidence)
- None - all findings verified with official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all stdlib, already in use
- Architecture: HIGH - codebase reviewed, extension points identified
- Pitfalls: HIGH - verified with Python documentation, common patterns documented

**Research date:** 2026-01-26
**Valid until:** 90 days (stable stdlib APIs, no external dependencies)
