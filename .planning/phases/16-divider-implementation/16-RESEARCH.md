# Phase 16: Divider Implementation - Research

**Researched:** 2026-01-30
**Domain:** Python CLI output protocol extension, ANSI terminal rendering
**Confidence:** HIGH

## Summary

This phase extends the Output Protocol with two divider methods and implements them in CliOutput/NullOutput. The codebase already has most building blocks in place: `panels.py` has `render_step_divider()` and `render_action_divider()` functions, `ansi.py` has `get_terminal_width()`, and `theme.py` has the border color palette entry `(100, 160, 180)`.

The main work is: (1) add `step_divider()` and `device_divider()` to the Output Protocol, (2) implement them in CliOutput using existing panel primitives or slight adaptations, (3) add no-op implementations to NullOutput, and (4) add Unicode detection for ASCII fallback.

**Primary recommendation:** Leverage existing `render_step_divider()` and `render_action_divider()` in `panels.py` as the rendering backbone. Add a `supports_unicode()` detection function to `theme.py` or `ansi.py`. Wire through Output Protocol.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.9+ | Everything | Project constraint: no external deps |
| `shutil.get_terminal_size` | stdlib | Terminal width | Already used in `ansi.py` |
| `unicodedata` | stdlib | Character width | Already used in `ansi.py` |

No external libraries needed or permitted.

## Architecture Patterns

### Existing Code Map

```
output.py   → Output Protocol (add methods here)
            → CliOutput (implement rendering here)
            → NullOutput (no-op stubs here)
panels.py   → render_step_divider() — already renders ┄ dividers
            → render_action_divider() — simpler variant
ansi.py     → get_terminal_width() — dynamic width detection
theme.py    → PALETTE["border"] = (100, 160, 180) — muted teal
            → ColorTier — tier detection already exists
```

### Pattern 1: Protocol Extension
**What:** Add methods to `Output` Protocol class, then implement in both `CliOutput` and `NullOutput`.
**Current pattern:** All output methods follow `def method(self, ...) -> None` with `CliOutput` using `self.theme` for styling and `NullOutput` returning `pass`.

### Pattern 2: Rendering Delegation
**What:** CliOutput delegates to `panels.py` render functions, just like `error_with_recovery` delegates to `errors.format_error`.
**When to use:** When rendering logic is complex enough to warrant a pure function.

### Pattern 3: Unicode Detection for ASCII Fallback
**What:** Detect whether terminal supports Unicode box-drawing characters.
**Approach:** Check `sys.stdout.encoding` for UTF-8 compatibility. If encoding is ascii/cp1252/latin-1 or similar, fall back to ASCII dashes.

```python
def supports_unicode() -> bool:
    """Check if stdout encoding supports Unicode box-drawing characters."""
    encoding = getattr(sys.stdout, 'encoding', '') or ''
    return encoding.lower().replace('-', '').startswith('utf')
```

### Anti-Patterns to Avoid
- **Hardcoded width:** Never use `width=80`. Always call `get_terminal_width()`.
- **Importing output.py from panels.py:** Would create circular import. Panels are pure render functions; output.py calls them.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Terminal width | Manual ioctl | `ansi.get_terminal_width()` | Already exists, handles fallback |
| ANSI coloring | Raw escape codes | `theme.rgb_to_ansi()` + PALETTE | Tier-aware, already works |
| Step divider rendering | New function | `panels.render_step_divider()` | Already exists with ┄ character |
| Display width calc | `len()` | `ansi.display_width()` | Handles ANSI codes and CJK |

## Common Pitfalls

### Pitfall 1: Hardcoded Divider Width
**What goes wrong:** Divider renders at 60 or 80 chars regardless of terminal size.
**Why it happens:** `render_step_divider()` currently defaults `total_width=60` and `render_action_divider()` hardcodes `width = 60`.
**How to avoid:** Pass `get_terminal_width()` (or a fraction of it) as the width parameter. The requirements say "adapts to terminal width."

### Pitfall 2: Circular Imports
**What goes wrong:** If `output.py` imports from `panels.py` at module level, and `panels.py` imports from `theme.py`, it works. But if `panels.py` ever imports from `output.py`, circular import.
**How to avoid:** Keep rendering in `panels.py` as pure functions. `output.py` calls them.

### Pitfall 3: Unicode Fallback Not Tested
**What goes wrong:** ASCII fallback path (`---`) never exercised because dev terminals all support UTF-8.
**How to avoid:** Add a `supports_unicode()` function that can be overridden/tested. Use it in the render functions.

### Pitfall 4: Device Divider Label Centering Off-by-One
**What goes wrong:** Label `─── 1/3 Octopus Pro ───` not centered when terminal width is odd.
**How to avoid:** Compute left and right sides separately: `left = (width - label_len) // 2`, `right = width - label_len - left`.

## Code Examples

### step_divider() — Output Protocol Addition
```python
# In Output Protocol:
def step_divider(self) -> None: ...

# In CliOutput:
def step_divider(self) -> None:
    from .panels import render_step_divider
    from .ansi import get_terminal_width
    width = get_terminal_width()
    # Use border color (muted teal), not subtle
    print(render_unlabeled_divider(width))
```

### device_divider() — Labeled Divider
```python
# In Output Protocol:
def device_divider(self, index: int, total: int, name: str) -> None: ...

# In CliOutput:
def device_divider(self, index: int, total: int, name: str) -> None:
    from .ansi import get_terminal_width
    t = self.theme
    width = get_terminal_width()
    label = f" {index}/{total} {name} "
    dash = "─" if supports_unicode() else "-"
    side_left = (width - len(label)) // 2
    side_right = width - len(label) - side_left
    line = f"{t.border}{dash * side_left}{label}{dash * side_right}{t.reset}"
    print(line)
```

### Unicode Detection
```python
import sys

def supports_unicode() -> bool:
    encoding = getattr(sys.stdout, 'encoding', '') or ''
    return 'utf' in encoding.lower()
```

### ASCII Fallback Characters
| Unicode | ASCII Fallback |
|---------|---------------|
| ┄ (U+2504) | - |
| ─ (U+2500) | - |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded `width=60` in panels.py | Should use `get_terminal_width()` | This phase | Dividers fill terminal |
| No Unicode detection | `supports_unicode()` function | This phase | ASCII fallback support |
| No divider methods on Output | Protocol-level divider API | This phase | All output backends render dividers |

## Existing Code Details

### render_step_divider() in panels.py (line 176)
- Takes `label` and `total_width=60`
- Uses `┄` (U+2504) character
- Colors: `theme.subtle` for dashes, `theme.dim` for label
- **Gap vs requirements:** Uses `subtle` color, but OUT-03 wants `border` color (muted teal). Width is hardcoded 60.

### render_action_divider() in panels.py (line 205)
- Wrapper around `render_step_divider()` for labeled variant
- Plain variant: `subtle` colored `┄` at width 60
- **Gap vs requirements:** Same color/width issues.

### Output Protocol in output.py (line 11)
- Currently has: `info`, `success`, `warn`, `error`, `error_with_recovery`, `device_line`, `prompt`, `confirm`, `phase`
- No divider methods exist yet.

### Theme border color
- `PALETTE["border"] = (100, 160, 180)` — this is the muted teal #64A0B4 referenced in OUT-03.
- `theme.border` is the pre-built ANSI sequence for this color.

## Open Questions

1. **Should `render_step_divider` be modified or should new functions be created?**
   - What we know: Existing function uses `subtle` color and hardcoded width; requirements want `border` color and dynamic width.
   - Recommendation: Create new render functions or modify existing ones with parameters for color and width. Modifying existing is preferred to avoid duplication — add optional `color` and use `get_terminal_width()` as default.

2. **Where should `supports_unicode()` live?**
   - Recommendation: `ansi.py` — it already handles terminal capability detection (width). Alternatively `theme.py` alongside `supports_color()`.

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `output.py`, `panels.py`, `ansi.py`, `theme.py` in the codebase
- Python stdlib docs: `shutil.get_terminal_size`, `sys.stdout.encoding`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib only, all tools already exist in codebase
- Architecture: HIGH - clear existing patterns to follow (Protocol + CliOutput + NullOutput)
- Pitfalls: HIGH - identified from direct code inspection

**Research date:** 2026-01-30
**Valid until:** 2026-03-01 (stable domain, no external deps)
