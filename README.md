# AI Image Generator

Streamlit app for reproducible presentation image generation. Prompts, provider settings, and generated images are stored together so runs can be reviewed, reused, and iterated on.

Inspired by [hadley/bananarama](https://github.com/hadley/bananarama).

## Features

- **Google Gemini image generation** — primary path for standard and reference-guided images
- **Reference image support** — upload a photo, pick from a saved library, or inline `[name]` tokens in prompts (Gemini only)
- **Style presets** — save and reuse style prompts stored in `presets.yaml`
- **Generation history** — browse, search, download, and quickly reuse prior prompts

## Examples

### Retro illustration — coffee shop

![Retro illustration](img/retro-illustration-coffee.png)

> **Prompt:** A man at a coffee shop using a MacBook and working with Claude Code. The coffee shop overlooks Monterey Bay.
>
> **Reference image:** none

```yaml
name: Retro illustration
style_prompt: >
  Retro-futurist editorial illustration with sleek shapes, limited contrast,
  soft grain, and a refined late-60s/70s speculative design influence. Muted
  but confident palette. Clean, conceptual, modern, and visually memorable
  for presentation storytelling.
```

---

### Flat 2D kids — coffee shop

![Flat 2D kids](img/flat2d-kids-coffee.png)

> **Prompt:** A man at a coffee shop using a MacBook and working with Claude Code. The coffee shop overlooks Monterey Bay.
>
> **Reference image:** none

```yaml
name: Flat 2d - kids
style_prompt: >
  Flat 2D preschool-style illustration with friendly rounded forms, light blue
  and cream palette, clean edges, playful motion, simple environment design,
  optimistic and cozy mood, highly readable for presentation use.
```

---

### Retro comic book — pickleball

![Retro comic book](img/retro-comic-pickleball.png)

> **Prompt:** A couple dominating a game of pickleball.
>
> **Reference image:** none

```yaml
name: Retro comic book
style_prompt: >
  Retro silver-age comic illustration with clean linework, bright flat colors,
  vintage halftone texture, expressive faces, simplified backgrounds, playful
  dramatic action, nostalgic comic book energy, presentation-friendly composition.
```

---

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your API keys
streamlit run app.py
```

Run tests with:

```bash
python3 -m unittest discover -s tests -v
```

## Project layout

- `app.py` — thin Streamlit shell: page setup, auth, session defaults, sidebar, and tab composition
- `src/ui/` — one module per UI surface (`generate_tab`, `history_tab`, `presets_tab`, `references_tab`, `sidebar`)
- `src/services/` — app-level orchestration such as generate → persist → load
- `src/generator.py` — provider-specific image generation
- `src/database.py` — SQLite persistence
- `src/storage.py` — file storage for generated images
- `src/presets.py` — YAML-backed preset management
- `src/references.py` — saved reference image library
- `src/auth.py` — optional Google OAuth flow

## Provider setup

| Provider | Env var | Notes |
|---|---|---|
| `google-gemini` | `GOOGLE_API_KEY` | Default. Uses Imagen for standard generations and `gemini-2.5-flash-image` when reference images are supplied |
| `openai` | `OPENAI_API_KEY` | Optional placeholder. Install `openai` separately if you decide to use it later |

## Style presets

Presets are stored in `presets.yaml` at the project root — edit it directly in any text editor or manage them via the **Presets** tab in the app.

## Reference images

Upload a one-off reference image in the Generate tab, or save permanent references via the **References** tab. Permanent references are stored in `data/references/` (gitignored).

Reference names are normalized to lowercase slugs. Use letters, numbers, `_`, or `-` if you want predictable prompt tokens such as `[team_logo]`.

## Persistence

### SQLite — `data/db.sqlite3`

Stores generation history only. Path overridden by `DB_PATH` env var.

#### `generations`
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| title | TEXT | Optional human-readable label |
| project_name | TEXT | Deck / presentation grouping |
| tags | TEXT | Comma-separated tags |
| base_prompt | TEXT | Original user prompt |
| style_prompt | TEXT | Style text appended to base prompt |
| final_prompt | TEXT | Combined prompt sent to provider |
| provider | TEXT | e.g. `google-gemini` |
| model | TEXT | e.g. `imagen-4.0-generate-001` |
| settings | TEXT | JSON blob of provider-specific settings |
| output_path | TEXT | Local path to saved image file |
| created_at | TEXT | ISO-8601 UTC timestamp |
