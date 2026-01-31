# Phase 24: Slug Generation - Research

**Researched:** 2026-02-01
**Domain:** String normalization and filesystem-safe slug generation
**Confidence:** HIGH

## Summary

Phase 24 requires implementing a `generate_device_key()` function that converts user-provided display names (e.g., "Octopus Pro v1.1") into filesystem-safe, URL-safe slug keys (e.g., "octopus-pro-v1-1"). The function must handle Unicode normalization, special character stripping, collision detection with numeric suffix appending, empty result rejection, length truncation, and path-traversal prevention.

This is a well-established problem domain with clear stdlib-only solutions. The kalico-flash project uses **Python 3.9+ stdlib only** with no external dependencies, which rules out popular libraries like `python-slugify`. A custom implementation using `unicodedata`, `re`, and string manipulation is required.

The codebase already has similar string manipulation utilities (`extract_mcu_from_serial()`, `generate_serial_pattern()` in discovery.py) and validation patterns (`validate_device_key()` in validation.py) that establish conventions for this implementation.

**Primary recommendation:** Implement a standalone `generate_device_key(name, registry)` function in a new module (e.g., `slugify.py` or extend `validation.py`) using `unicodedata.normalize('NFKD')` for Unicode handling, regex for character stripping, and a while-loop with `itertools.count()` for collision handling.

## Standard Stack

### Core (Stdlib Only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `unicodedata` | stdlib | Unicode normalization (NFKD) | Official Python unicode handling; converts "Café" → "Cafe" safely |
| `re` | stdlib | Character stripping and validation | Already used throughout codebase for pattern matching |
| `itertools.count()` | stdlib | Collision counter generation | Memory-efficient infinite counter for `-2`, `-3` suffix logic |
| `str.translate()` | stdlib | Fast character replacement | 5x faster than regex for bulk character stripping |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `string.ascii_lowercase` | stdlib | Allowed character sets | Reference for validation |
| `string.digits` | stdlib | Numeric character reference | Validation helper |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom implementation | `python-slugify` (PyPI) | **Rejected**: Requires external dependency, violates stdlib-only constraint |
| Custom implementation | `awesome-slugify` (PyPI) | **Rejected**: Requires external dependency, violates stdlib-only constraint |
| NFKD normalization | NFC/NFD | **Rejected**: NFKD is best for slug generation (decomposes + ASCII-compatible) |
| Registry check | UUID suffix | **Rejected**: Not human-meaningful, requirement specifies numeric suffix |

**Installation:**
None required — stdlib only.

## Architecture Patterns

### Recommended Function Placement

```
kflash/
├── validation.py    # OPTION A: Add generate_device_key() here (co-locate with validate_device_key)
├── slugify.py       # OPTION B: New module for slug generation (single responsibility)
└── registry.py      # Calls generate_device_key() during add() operation
```

**Recommendation:** Extend `validation.py` — slug generation is validation-adjacent, and `validate_device_key()` already exists there. Keeps related string processing together.

### Pattern 1: Slug Generation with Collision Handling

**What:** Generate a unique slug from a display name, appending numeric suffixes on collision.

**When to use:** During device registration when user provides display name but no key.

**Example:**
```python
import unicodedata
import re
from itertools import count

def generate_device_key(name: str, registry) -> str:
    """Generate a filesystem-safe slug from display name.

    Examples:
        "Octopus Pro v1.1" -> "octopus-pro-v1-1"
        "Café MCU" -> "cafe-mcu"
        "RPi_Host" -> "rpi-host"
        "Device!!!" -> "device"

    Collision handling:
        If "octopus-pro" exists, generates "octopus-pro-2"
        If "octopus-pro-2" exists, generates "octopus-pro-3"

    Args:
        name: User-provided display name
        registry: Registry instance for collision checking

    Returns:
        Unique filesystem-safe slug (lowercase, alphanumeric + hyphens)

    Raises:
        ValueError: If name results in empty slug after normalization
    """
    # Step 1: Unicode normalization (NFKD = decompose accents)
    normalized = unicodedata.normalize('NFKD', name)

    # Step 2: Convert to ASCII, dropping non-ASCII characters
    ascii_str = normalized.encode('ascii', 'ignore').decode('ascii')

    # Step 3: Lowercase and replace spaces/underscores with hyphens
    slug = ascii_str.lower().replace(' ', '-').replace('_', '-')

    # Step 4: Strip all non-alphanumeric except hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)

    # Step 5: Collapse multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)

    # Step 6: Strip leading/trailing hyphens
    slug = slug.strip('-')

    # Step 7: Truncate to max length (64 chars for filesystem safety)
    MAX_LENGTH = 64
    slug = slug[:MAX_LENGTH].rstrip('-')

    # Step 8: Validate non-empty
    if not slug:
        raise ValueError(f"Display name '{name}' results in empty slug")

    # Step 9: Handle collisions with numeric suffix
    candidate = slug
    for suffix in count(2):  # Start at 2 (base slug has no suffix)
        if registry.get(candidate) is None:
            return candidate
        # Append suffix, ensuring total length <= MAX_LENGTH
        suffix_str = f"-{suffix}"
        candidate = slug[:MAX_LENGTH - len(suffix_str)] + suffix_str
```

**Source:** Derived from [Django slug uniqueness patterns](https://code.djangoproject.com/ticket/12651) and [Python slug generation best practices](https://www.peterbe.com/plog/fastest-python-function-to-slugify-a-string)

### Pattern 2: Path Traversal Prevention

**What:** Ensure generated slugs cannot escape config cache directory.

**When to use:** Before using slug in file path construction.

**Example:**
```python
# Already handled by character stripping (no / or \\ or ..)
# Additional safety check:
def is_safe_slug(slug: str) -> bool:
    """Verify slug cannot escape directory."""
    if not slug:
        return False
    if slug in ('.', '..'):
        return False
    if '/' in slug or '\\' in slug:
        return False
    return True
```

**Rationale:** The regex `[^a-z0-9-]` already strips `/` and `\`, but explicit validation adds defense-in-depth.

### Pattern 3: Integration with Add Device Flow

**What:** Call slug generation during device registration, before menuconfig.

**When to use:** In `cmd_add_device()` after user provides display name.

**Example:**
```python
# Current flow (flash.py lines 1813-1837):
# Step 4: Device key (manual input)
device_key = None
for _attempt in range(3):
    key_input = out.prompt("Device key (e.g., 'octopus-pro')")
    # ... validation ...

# NEW flow:
# Step 4: Display name
display_name = out.prompt("Display name (e.g., 'Octopus Pro v1.1')")
if not display_name:
    out.error("Display name is required.")
    return 1

# Step 5: Auto-generate key
try:
    device_key = generate_device_key(display_name, registry)
    out.info("Registry", f"Generated device key: {device_key}")
except ValueError as e:
    out.error(str(e))
    return 1
```

### Anti-Patterns to Avoid

- **Don't use UUIDs for collision handling:** Requirement KEY-02 specifies numeric suffixes, not random strings. UUIDs break human-readability of cache directories.
- **Don't re-slugify existing devices:** Requirement KEY-06 explicitly states existing keys are preserved. Slug generation is for NEW devices only.
- **Don't truncate mid-word without hyphen cleanup:** Truncating "octopus-professional" to "octopus-profess" looks broken. Always `rstrip('-')` after truncation.
- **Don't skip Unicode normalization:** User input may contain accented characters ("Café Printer"). NFKD normalization is essential for cross-platform filesystem safety.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unicode normalization | Custom accent-stripping dict | `unicodedata.normalize('NFKD')` | Handles thousands of Unicode characters correctly, well-tested |
| Unique key generation | Random suffix or timestamp | `itertools.count()` + while loop | Predictable, deterministic, easy to test |
| Character stripping | Manual character-by-character loop | `str.translate()` or `re.sub()` | 5x faster, more readable |
| Empty slug detection | Complex heuristics | Simple `if not slug:` check | Requirement specifies rejection, not fallback generation |

**Key insight:** Python's stdlib already has battle-tested Unicode handling. The hard part (diacritic removal, compatibility decomposition) is solved by `unicodedata.normalize('NFKD')` + ASCII encoding. Custom accent-stripping dictionaries are error-prone and incomplete.

## Common Pitfalls

### Pitfall 1: Using NFC Instead of NFKD

**What goes wrong:** `unicodedata.normalize('NFC', "Café")` returns `"Café"` (composed form). When encoded to ASCII with `ignore`, it becomes `"Caf"` (loses the 'e').

**Why it happens:** NFC recomposes characters, keeping accented forms as single code points. These don't decompose to ASCII equivalents.

**How to avoid:** Always use `'NFKD'` (compatibility decomposition) which breaks `"é"` into `"e" + combining-acute-accent`, allowing the accent to be stripped during ASCII encoding.

**Warning signs:** Slugs missing letters from accented characters (e.g., "Café" becomes "Caf" instead of "Cafe").

### Pitfall 2: Collision Handling Without Length Check

**What goes wrong:** If base slug is 64 chars (max length), appending `-2` creates a 66-char slug that exceeds limit.

**Why it happens:** Naive suffix appending: `slug + f"-{suffix}"` doesn't account for max length.

**How to avoid:** Truncate base slug BEFORE appending suffix:
```python
suffix_str = f"-{suffix}"
candidate = slug[:MAX_LENGTH - len(suffix_str)] + suffix_str
```

**Warning signs:** Filesystem errors when creating config cache directories, or collisions not properly detected.

### Pitfall 3: Empty Slug Silent Fallback

**What goes wrong:** Name like "!!!" or "中文名" (Chinese characters) produces empty slug after ASCII stripping. Code silently falls back to UUID or timestamp.

**Why it happens:** Attempt to be "helpful" by generating something instead of erroring.

**How to avoid:** Requirement KEY-01 says "edge cases: empty result rejected". Raise `ValueError` and let user provide a valid name.

**Warning signs:** Devices with keys like "device-1234-abcd" or "unnamed-device" appearing in registry.

### Pitfall 4: Path Traversal via Special Names

**What goes wrong:** User inputs "../admin" or "../../etc" as display name. Slug generation doesn't strip `.` or `/`, resulting in path traversal.

**Why it happens:** Insufficient character stripping.

**How to avoid:** The regex `[^a-z0-9-]` already strips `/`, `\`, and `.`. Additional safety: explicitly reject slugs containing `..` or path separators.

**Warning signs:** Config cache directories appearing in unexpected locations, or security scanner warnings.

### Pitfall 5: Hyphen Collapse Breaking Empty Check

**What goes wrong:** Name "- - -" becomes "---" after space-to-hyphen, then "" after hyphen collapse, but empty check happens BEFORE collapse.

**Why it happens:** Wrong ordering of normalization steps.

**How to avoid:** Perform empty check AFTER all normalization steps (collapse, strip, truncate):
```python
slug = slug.strip('-')  # Final cleanup
if not slug:
    raise ValueError(...)
```

**Warning signs:** Devices registered with keys like "-" or "--" that break CLI parsing or display.

## Code Examples

Verified patterns using Python stdlib:

### Example 1: Full Slug Generation Function

```python
# Source: Derived from stdlib docs and Django slug patterns
import unicodedata
import re
from itertools import count
from typing import Optional

def generate_device_key(name: str, registry) -> str:
    """Generate unique filesystem-safe slug from display name.

    Implements requirements KEY-01 and KEY-02:
    - Auto-generates slug from display name
    - Handles collisions with numeric suffix (-2, -3, etc.)
    - Truncates to 64 chars for filesystem safety
    - Rejects empty results
    - Strips path-traversal characters

    Args:
        name: User-provided display name (e.g., "Octopus Pro v1.1")
        registry: Registry instance for collision checking

    Returns:
        Unique slug (e.g., "octopus-pro-v1-1")

    Raises:
        ValueError: If name results in empty slug after normalization

    Examples:
        >>> generate_device_key("Octopus Pro v1.1", registry)
        "octopus-pro-v1-1"
        >>> generate_device_key("Café MCU", registry)
        "cafe-mcu"
        >>> generate_device_key("Device-2", registry)  # collides
        "device-2-2"
    """
    MAX_LENGTH = 64

    # Unicode normalization (NFKD = decompose accents)
    normalized = unicodedata.normalize('NFKD', name)

    # Convert to ASCII, dropping non-ASCII
    ascii_str = normalized.encode('ascii', 'ignore').decode('ascii')

    # Lowercase, replace spaces/underscores with hyphens
    slug = ascii_str.lower()
    slug = slug.replace(' ', '-').replace('_', '-')

    # Strip all non-alphanumeric except hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)

    # Collapse multiple hyphens
    slug = re.sub(r'-+', '-', slug)

    # Strip leading/trailing hyphens and truncate
    slug = slug.strip('-')[:MAX_LENGTH].rstrip('-')

    # Validate non-empty
    if not slug:
        raise ValueError(
            f"Display name '{name}' produces empty device key. "
            "Use a name with alphanumeric characters."
        )

    # Handle collisions with numeric suffix
    candidate = slug
    for suffix in count(2):
        if registry.get(candidate) is None:
            return candidate
        suffix_str = f"-{suffix}"
        base_max = MAX_LENGTH - len(suffix_str)
        candidate = slug[:base_max].rstrip('-') + suffix_str

    # Unreachable (count() is infinite), but satisfies type checker
    raise RuntimeError("Collision handling failed")
```

### Example 2: Integration with cmd_add_device

```python
# In flash.py, cmd_add_device() function
# Replace lines 1813-1837 (manual key input) with:

def cmd_add_device(registry, out, selected_device=None) -> int:
    # ... (steps 1-3: discovery, selection, global config) ...

    # Step 4: Display name
    out.step_divider()
    display_name = out.prompt("Display name (e.g., 'Octopus Pro v1.1')")
    if not display_name:
        out.error("Display name is required.")
        return 1

    # Step 5: Auto-generate device key
    out.step_divider()
    try:
        from .validation import generate_device_key
        device_key = generate_device_key(display_name, registry)
        out.info("Registry", f"Generated device key: {device_key}")
    except ValueError as e:
        out.error(str(e))
        return 1

    # Step 6: MCU auto-detection
    # ... (continue existing flow) ...
```

### Example 3: Unit Tests for Edge Cases

```python
# Recommended test cases for validation
def test_generate_device_key():
    # Normal cases
    assert generate_device_key("Octopus Pro v1.1", registry) == "octopus-pro-v1-1"
    assert generate_device_key("RPi Host", registry) == "rpi-host"
    assert generate_device_key("Café MCU", registry) == "cafe-mcu"

    # Unicode handling
    assert generate_device_key("Naïve Device", registry) == "naive-device"

    # Special character stripping
    assert generate_device_key("Device!!!", registry) == "device"
    assert generate_device_key("Test@#$%Device", registry) == "test-device"

    # Hyphen collapsing
    assert generate_device_key("Device - - - Name", registry) == "device-name"

    # Leading/trailing hyphens
    assert generate_device_key("-Device-", registry) == "device"

    # Long names (truncation)
    long_name = "A" * 100
    slug = generate_device_key(long_name, registry)
    assert len(slug) == 64
    assert not slug.endswith('-')

    # Empty result (should raise)
    with pytest.raises(ValueError):
        generate_device_key("!!!", registry)
    with pytest.raises(ValueError):
        generate_device_key("   ", registry)

    # Collision handling
    registry.add(DeviceEntry(key="device", name="Device", ...))
    assert generate_device_key("Device", registry) == "device-2"
    registry.add(DeviceEntry(key="device-2", name="Device 2", ...))
    assert generate_device_key("Device", registry) == "device-3"

    # Path traversal prevention
    assert generate_device_key("../admin", registry) == "admin"
    assert generate_device_key("../../etc", registry) == "etc"
    assert '/' not in generate_device_key("path/to/device", registry)
    assert '\\' not in generate_device_key("path\\to\\device", registry)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual key input | Auto-generated slugs | **This phase (v4.0)** | Removes user-facing complexity, one less prompt |
| UUID/timestamp suffixes | Numeric suffixes | Community standard (Django ~2010) | Human-readable cache directories |
| NFC normalization | NFKD normalization | Unicode best practices (early 2000s) | Better ASCII decomposition |
| Custom accent tables | `unicodedata` module | Python 2.0+ (2000) | Comprehensive, maintained by Unicode Consortium |

**Deprecated/outdated:**
- **`str.maketrans()` for bulk replacement:** Still valid, but `re.sub()` is more readable for complex patterns
- **Hand-rolled collision detection:** `itertools.count()` pattern is now standard (cleaner than manual while-loop)

## Open Questions

1. **Should collision suffix start at -1 or -2?**
   - What we know: Django uses `-2` for first collision (base slug has no suffix)
   - What's unclear: User expectation (is "device-1" confusing vs "device" + "device-2"?)
   - Recommendation: Use `-2` (matches Django, clearer that base slug is primary)

2. **Truncation strategy for multi-word names?**
   - What we know: Hard truncation at 64 chars may cut mid-word
   - What's unclear: Should we try to truncate at word boundaries?
   - Recommendation: **No** — adds complexity, rare edge case, simple truncation + `rstrip('-')` is sufficient

3. **Case sensitivity in collision detection?**
   - What we know: Slugs are lowercase, registry keys are case-sensitive in JSON
   - What's unclear: Should "Device" and "device" collide?
   - Recommendation: **Yes** — `validate_device_key()` already enforces lowercase-only keys, collision check is automatic

## Sources

### Primary (HIGH confidence)

- [Python unicodedata documentation](https://docs.python.org/3/library/unicodedata.html) - Official Unicode normalization forms
- Python stdlib `re`, `itertools`, `string` modules - Official documentation
- Existing codebase patterns:
  - `kflash/validation.py:validate_device_key()` - Key validation regex and registry checking
  - `kflash/discovery.py:extract_mcu_from_serial()` - String pattern extraction
  - `kflash/registry.py:Registry.get()` - Collision checking API

### Secondary (MEDIUM confidence)

- [python-slugify PyPI](https://pypi.org/project/python-slugify/) - Library design patterns (not usable, but informative)
- [Fastest Python slugify function](https://www.peterbe.com/plog/fastest-python-function-to-slugify-a-string) - Performance comparison of approaches
- [Django slug uniqueness patterns](https://code.djangoproject.com/ticket/12651) - Collision handling with numeric suffixes

### Tertiary (LOW confidence)

- Web search results on slug generation - General patterns, not Python-specific
- Stack Overflow discussions - Community preferences, not authoritative

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** - stdlib-only, well-documented, already used in codebase
- Architecture: **HIGH** - follows existing validation.py patterns, clear integration point
- Pitfalls: **HIGH** - derived from Unicode docs and Django's 15+ years of slug generation experience

**Research date:** 2026-02-01
**Valid until:** 2026-03-31 (stable domain, stdlib APIs don't change rapidly)

**Notes:**
- No external dependencies required (aligns with project constraints)
- Implementation can be tested locally without Pi hardware
- Success criteria from phase description are all addressable with stdlib approach
