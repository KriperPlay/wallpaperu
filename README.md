# wallpaperu 
<img width="150" height="150" alt="" src="https://github.com/user-attachments/assets/63a733bd-bfb4-4170-aec4-a1fc943ef30d" />

# About
(Project written by me, documentation written by DeepSeek)

wallpaperu - a small command‑line tool that composes abstract wallpapers from procedurally placed PNG shapes. Each wallpaper is built from a **color theme**, a set of **shapes**, and a **display template** (resolution). Shapes are randomly scaled, rotated, recolored and packed onto a solid background without overlaps.

---

## Table of Contents

1. [Project structure](#project-structure)
2. [Requirements & installation](#requirements--installation)
3. [Quick start](#quick-start)
4. [CLI reference](#cli-reference)
5. [Configuration (`vars.py`)](#configuration-varspy)
6. [Shape assets](#shape-assets)
7. [How it works](#how-it-works)
8. [Examples](#examples)
9. [Extending the project](#extending-the-project)
10. [Known issues & notes](#known-issues--notes)

---

## Project structure

```
.
├── vars.py          # All configuration: themes, templates, shape catalogues
├── wallpaperu.py    # CLI entry point + generation logic
└── shapes-png/      # Source shape assets (transparent PNGs, one per shape name)
    ├── Square.png
    ├── Circle.png
    ├── Gem.png
    └── ...
```

---

## Requirements & installation

**Runtime:** Python 3.10+ (the code uses `math.hypot`, f‑strings with nested quotes, and `dict` ordering is relied upon implicitly).

**Dependencies:**

| Package  | Purpose                                  |
|----------|------------------------------------------|
| `Pillow` | Image loading, resizing, rotation, paste |
| `click`  | Command‑line interface                   |
| `tqdm`   | Progress bar while placing shapes        |

Install:

```bash
pip install pillow click tqdm
```

Make sure the `shapes-png/` directory exists next to `wallpaperu.py` and contains the required PNG files (see [Shape assets](#shape-assets)).

---

## Quick start

```bash
python wallpaperu.py --theme midnight_coral --shapes Gem,Gem,Pill --template Phone_QHD
```

The result is saved in the current working directory as:

```
<theme>-<template>-<DD.MM.YYYY-HH:MM>.png
```

> ⚠️ Always pass `--shapes` explicitly — see [Known issues](#known-issues--notes).

---

## CLI reference

`wallpaperu.py` exposes a single Click command: `generate`.

| Option     | Short | Default      | Description |
|------------|-------|--------------|-------------|
| `--theme`  | `-t`  | `red`        | Name of a preset from `PRESETS`. Any key of `vars.PRESETS` is valid. |
| `--shapes` | `-s`  | *(see note)* | Comma‑separated list of shape names. Duplicates are allowed and encouraged — each occurrence produces one shape. |
| `--template` | `-d` | `Phone_QHD` | Key of `template_display` — selects the output resolution. |

Available templates:

| Template      | Resolution  |
|---------------|-------------|
| `Phone_FHD`   | 1080 × 2400 |
| `Phone_QHD`   | 1440 × 3200 |
| `Desktop_FHD` | 1920 × 1080 |
| `Desktop_QHD` | 2560 × 1440 |

Shape names must be chosen from `vars.list_figures`. They are split into three groups that determine which color from the theme palette is used (see [Themes](#themes-presets)).

---

## Configuration (`vars.py`)

### Themes (`PRESETS`)

Each preset is a list of **four hex colors** used in fixed positions:

```python
"theme_name": [background, basic, organic, effect]
```

| Index | Role            | Applied to shapes in group |
|-------|-----------------|-----------------------------|
| `0`   | Background fill | —                           |
| `1`   | Color           | `group_basic`               |
| `2`   | Color           | `group_organic`             |
| `3`   | Color           | `group_effects`             |

Two families ship by default:

- **Basic** — `red`, `green`, `blue`, `purple`, `orange`
- **Styled** — `mint_choco`, `midnight_coral`, `forest_gold`, `plum_rose`, `carbon_lime`, `teal_sand`, `eggplant_pop`, `olive_retro`, `bordeaux_mint`, `night_champagne`

### Templates (`template_display`)

A `dict` mapping template name → `(width, height)` in pixels. Adding a new entry makes it immediately available via `--template`.

### Shape catalogues

| List             | Purpose                                                        |
|------------------|----------------------------------------------------------------|
| `list_figures`   | Master list of all valid shape names (used in help text).      |
| `group_basic`    | Geometric primitives — colored with `PRESETS[t][1]`.          |
| `group_organic`  | Blobs, clovers, cookies, hearts — colored with `PRESETS[t][2]`. |
| `group_effects`  | Bursts, booms, puffy shapes — colored with `PRESETS[t][3]`.    |

> A shape that is **not** present in any of the three groups will cause `color_choice()` to return `None`, which will crash `prepare_shape()`. Keep the groups in sync with `list_figures`.

### Asset path

```python
SHAPES_DIR = 'shapes-png/'
```

Change this if your PNGs live elsewhere.

---

## Shape assets

Every name in `list_figures` must correspond to a file `<Name>.png` inside `SHAPES_DIR`.

Requirements for each PNG:

- **Format:** PNG with an alpha channel.
- **Content:** A single solid silhouette (any color — it is overwritten).
- **Transparency:** The area outside the silhouette must be fully transparent.
- **Size:** Arbitrary. Images are auto‑cropped to their alpha bounding box and rescaled.
- **Orientation:** Any — shapes are randomly rotated by default.

Any remaining opaque pixels are replaced with the theme color while preserving the alpha channel.

---

## How it works

The generation pipeline (`generate()` in `wallpaperu.py`):

1. **Resolve the canvas** — `canvas_size = template_display[template]`; background is filled with `PRESETS[theme][0]`.
2. **Map shapes to colors** — `color_choice()` returns `(filename, hex_color)` for every entry in `--shapes`, picking the palette slot based on which group the shape belongs to.
3. **Prepare each shape** — `prepare_shape()`:
   - crops to the alpha bounding box (`_trim`),
   - scales it to a random fraction of `base_side` (range `0.5–0.9`, aspect ratio preserved),
   - rotates it by a random angle and re‑crops,
   - recolors it while preserving alpha.
4. **Compute the base size** — `resize_for_template()`:
   - portrait (mobile): `0.60 × width / 1024`
   - landscape (desktop): `0.45 × height / 1024`
5. **Pack the shapes** — `place_shapes()`:
   - sorts shapes by area, largest first,
   - for each shape, tries up to **12 times** to find a free spot via `random_coord()`, shrinking it by 10 % on each failure,
   - gives up on a shape after 12 attempts (prints a warning and continues).
6. **Position search** — `random_coord()` uses rejection sampling:
   - samples up to 400 random centers,
   - rejects positions whose clearance (`distance − r₁ − r₂`) is below `gap = 60 px`,
   - keeps the **freest** of up to 30 candidates (largest clearance) so shapes spread out rather than clump,
   - `bleed = 0.2` allows shapes to extend up to 20 % of their radius past the canvas edge.
7. **Composite** — each shape is pasted with its own alpha mask, then the image is saved.

Progress is reported via `tqdm`.

---

## Examples

```bash
# Portrait, vivid red theme
python wallpaperu.py -t red -s Circle,Square,Triangle -d Phone_FHD

# Desktop wallpaper with mixed organic + effect shapes
python wallpaperu.py -t forest_gold -s Gem,Heart,Boom,Sunny -d Desktop_QHD

# Repetition is allowed — several of the same shape
python wallpaperu.py -t carbon_lime -s Pill,Pill,Pill -d Phone_QHD

# Minimal single‑shape wallpaper
python wallpaperu.py -t night_champagne -s Circle -d Desktop_FHD

# List all available themes (from the help text)
python wallpaperu.py --help
```

<img width="640" height="360" alt="mint_choco-Desktop_QHD-01 11 2026-15:43" src="https://github.com/user-attachments/assets/6727998b-ea35-4c22-ab6f-99d3e5207590" />

---

## Extending the project

### Adding a theme

```python
# vars.py
PRESETS["ocean_dusk"] = ["#0B1D2A", "#0E5A7A", "#4FC3F7", "#FFB74D"]
```

### Adding a template

```python
template_display["Tablet_QHD"] = (1600, 2560)
```

### Adding a shape

1. Drop `MyShape.png` (transparent silhouette) into `shapes-png/`.
2. Add `"MyShape"` to `list_figures` **and** to exactly one of `group_basic`, `group_organic`, or `group_effects`.
3. Run with `-s MyShape`.

### Reusing the engine programmatically

```python
import random
from vars import PRESETS, template_display, SHAPES_DIR
from wallpaperu import prepare_shape, place_shapes, resize_for_template
from PIL import Image

random.seed(42)                       # reproducible layout
canvas = template_display["Desktop_FHD"]
base   = resize_for_template(canvas)[0]
bg     = Image.new("RGB", canvas, PRESETS["plum_rose"][0])

shapes = [
    prepare_shape(SHAPES_DIR + "Gem.png", base, PRESETS["plum_rose"][2]),
    prepare_shape(SHAPES_DIR + "Fan.png", base, PRESETS["plum_rose"][2]),
]
for shape, pos in place_shapes(canvas, shapes):
    bg.paste(shape, pos, mask=shape)

bg.save("out.png")
```

Note that `random.seed(...)` before calling `prepare_shape` / `place_shapes` makes the output deterministic — the CLI does not expose a `--seed` flag (see below).

---

## Known issues & notes

1. **No `--seed` option.** `generate()` accepts a `seed` parameter, but it is not registered as a Click option, so it is always `None` from the CLI. Use the programmatic API (above) if you need reproducibility.
4. **Canvas position by bleed.** With `bleed = 0.2`, shapes may be pasted at negative coordinates. Pillow clips them automatically, so this is safe — but partial shapes at the edges are by design, not a bug.
5. **Missing group membership.** A shape present in `list_figures` but absent from all three groups returns `None` from `color_choice()` and crashes. Keep the lists aligned.
8. **Packing is heuristic.** If many large shapes are requested for a small template, some will be shrunk repeatedly and eventually skipped with a `"None space for a figure - pass"` message. Increase the number of shapes carefully or reduce `base_side`.
