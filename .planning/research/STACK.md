# Technology Stack

**Project:** kalico-flash CLI removal and device key internalization
**Researched:** 2026-01-31
**Overall Confidence:** HIGH (all APIs are Python 3.9+ stdlib, patterns proven in codebase)

---

## Scope

This is NOT a greenfield stack selection. kalico-flash is an existing Python 3.9+ stdlib-only tool. This document covers only the stdlib APIs and patterns needed for two changes:

1. Removing argparse CLI, making TUI the sole entry point
2. Auto-generating device keys from display names (slugification)
3. Collision handling for duplicate slugs
4. Migrating existing user-provided keys to auto-generated ones

---

## Required stdlib APIs

### Slug Generation

| Module / Function | Version | Purpose | Why |
|---|---|---|---|
| `re.sub()` | 3.9+ (stable) | Strip non-alphanumeric chars from display name | Single regex `[^a-z0-9]+` handles all special chars in one pass |
| `str.lower()` | 3.9+ | Normalize case before slugifying | Keys must be case-insensitive and filesystem-safe (used as config cache dir names) |
| `str.strip('-')` | 3.9+ | Trim leading/trailing hyphens after regex | Prevents keys like `-octopus-pro-` |

**Prescriptive slug algorithm:**

```python
import re

def slugify(name: str) -> str:
    """Convert display name to filesystem-safe key.

    'Octopus Pro v1.1' -> 'octopus-pro-v1-1'
    'LDO Nitehawk 36'  -> 'ldo-nitehawk-36'
    """
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')
```

**Why `re.sub` over `str.translate`:** One regex replaces all consecutive non-alphanumeric chars with a single hyphen. `str.translate` would need a translation table plus a separate pass to collapse consecutive separators. The regex is more readable and fewer lines.

**Why NOT `unicodedata.normalize`:** Device names are ASCII (MCU identifiers, board brand names like "BTT", "LDO"). NFKD normalization adds complexity with zero benefit for this domain.

**Why NOT `python-slugify` (PyPI):** Stdlib-only constraint. Four lines of `re.sub` does the job.

### Collision Handling

| Module / Function | Version | Purpose | Why |
|---|---|---|---|
| `dict.__contains__` (`in`) | 3.9+ | Check existing keys in registry | Registry devices dict is already in memory; O(1) lookup |

**Prescriptive collision algorithm:**

```python
def unique_key(slug: str, existing_keys: set[str]) -> str:
    """Append numeric suffix if slug collides."""
    if slug not in existing_keys:
        return slug
    n = 2
    while f"{slug}-{n}" in existing_keys:
        n += 1
    return f"{slug}-{n}"
```

Start at 2 (not 1) so the first device gets the clean slug and the second gets `-2`. Matches common conventions (file copies, URLs).

### CLI Removal

| Module / Function | Version | Purpose | Why |
|---|---|---|---|
| `sys.argv` | 3.9+ | Detect `--help` / `--version` without argparse | Two string comparisons replace entire argparse setup |
| `sys.stdin.isatty()` | 3.9+ | Gate TUI entry (already used) | Non-TTY invocations print help and exit |

**No new modules needed.** `flash.py` already imports `sys`. Removing `argparse` is pure deletion.

### Config Cache Migration

| Module / Function | Version | Purpose | Why |
|---|---|---|---|
| `shutil.move()` | 3.9+ | Rename config cache dirs from old keys to new slugs | Works across filesystems (defensive); already imported in `config.py` |
| `Path.exists()` | 3.9+ | Check if old cache dir exists before migration | Already used in `config.py` and `registry.py` |
| `json` (already imported) | 3.9+ | Rewrite devices.json with new keys | Registry already uses atomic JSON writes via tempfile+fsync+rename |

Migration is a one-time operation on first run after upgrade. The registry `load()` method can detect old-style keys (keys that do not match `slugify(entry.name)`) and offer migration.

**Ordering: migrate config dir BEFORE registry save.** If dir move fails, registry is unchanged. If registry save fails after dir move, the orphaned new-key dir is harmless.

---

## What NOT to Add

| Temptation | Why Not |
|---|---|
| `click` / `typer` / any CLI lib | Stdlib-only constraint; argparse is being removed, not replaced |
| `python-slugify` (PyPI) | Stdlib-only constraint; 4 lines of `re.sub` does the job |
| `unicodedata` | Device names are ASCII; NFKD normalization is unnecessary complexity |
| `hashlib` for key generation | Hashes are not human-readable; keys appear in config cache paths and logs |
| `uuid` for key generation | Same reason as hashlib |
| `argparse` with reduced flags | Half-measures create confusion; TUI is the sole interface |
| `shlex` / shell parsing | No command-line parsing needed after argparse removal |
| New error types | `RegistryError` already covers key conflicts |

---

## Integration Points

### registry.py

- `Registry.add_device()` currently accepts a `DeviceEntry` with a user-provided `key`. After this change, the caller passes only `name`, `mcu`, `serial_pattern`. The registry (or a helper) generates the key via `slugify(name)` + `unique_key()`.
- `Registry.save()` already handles atomic writes. No change needed.
- Add a `migrate_keys()` method that iterates devices, computes `slugify(entry.name)`, renames mismatched keys, and renames corresponding config cache directories.

### config.py

- `get_config_dir(device_key)` uses the key as a directory name. Slugs are filesystem-safe by construction (lowercase alphanumeric + hyphens), so this continues working unchanged.
- No changes to `ConfigManager` needed.

### models.py

- `DeviceEntry.key` field remains. The key is still stored and used; it is just auto-generated instead of user-provided.
- No schema changes needed.

### flash.py

- Remove `import argparse` and the `_parse_args()` function (and all `--device`, `--add-device`, `--list-devices`, `--remove-device` handling).
- `main()` becomes: check TTY, check `sys.argv` for `--help`/`--version`, load registry, launch TUI.
- The `DEFAULT_BLOCKED_DEVICES` list and helper functions (`_normalize_pattern`, `_build_blocked_list`, `_blocked_reason_for_filename`) stay; they are used by the TUI flow, not just CLI.

---

## Alternatives Considered

| Decision | Chosen | Alternative | Why Not Alternative |
|---|---|---|---|
| Slug generation | `re.sub` (4 lines) | `python-slugify` PyPI package | Stdlib-only constraint; trivial to implement inline |
| Collision suffix | Numeric `-2`, `-3` | UUID suffix | Must be human-readable in filesystem paths and debug output |
| Collision start | Start at 2 | Start at 1 | First device gets clean slug; `-2` clearly means "second" |
| CLI removal | Full removal | Keep `--help` via argparse | Two `sys.argv` checks replace entire argparse; cleaner |
| Cache dir rename | `shutil.move()` | `Path.rename()` | `rename()` fails across filesystems |
| Migration trigger | Detect on `load()` | Separate migration command | Users should not need to know about internal key changes |

---

## Installation

No changes. Zero new dependencies.

```bash
# Nothing to install. Python 3.9+ stdlib only.
```

---

## Confidence Assessment

| Recommendation | Confidence | Basis |
|---|---|---|
| `re.sub` for slugification | HIGH | Python stdlib docs; well-established pattern |
| Numeric suffix for collisions | HIGH | Common convention; trivial to implement |
| Remove argparse entirely | HIGH | TUI already handles all workflows; CLI flags are redundant |
| `shutil.move()` for cache migration | HIGH | Stdlib, well-documented, already imported in codebase |
| No external dependencies | HIGH | Project constraint from CLAUDE.md |

---

## Sources

- Existing codebase: `kflash/registry.py` (atomic save pattern), `kflash/config.py` (`get_config_dir`, `shutil` import), `kflash/flash.py` (argparse usage to remove), `kflash/models.py` (`DeviceEntry` fields)
- Python 3.9 stdlib docs: `re` module, `shutil.move()`, `pathlib.Path`, `sys.argv`
