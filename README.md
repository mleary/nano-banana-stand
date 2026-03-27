# AI Image Generator

Streamlit app for reproducible presentation image generation. Prompts, style settings, and generated images are stored together so every run can be reproduced or iterated on. Inspired by (hadley/bananarama)[https://github.com/hadley/bananarama]

## Features

- **Multi-provider image generation** — Google Gemini (Imagen 3), OpenAI DALL-E 3, fal.ai, Replicate
- **Provider selection in UI** — switch providers without touching config files
- **chatlas integration** — uses [posit-dev/chatlas](https://github.com/posit-dev/chatlas) `ChatGoogle` for Gemini-powered prompt enhancement before generation
- **Style presets** — save and reuse style prompts across generations
- **Full reproducibility** — every generation stores prompt, style, provider, model, settings, and timestamp
- **Generation history** — browse, search, download, and rerun past generations
- **Railway deployment** — persistent volume for database and image storage

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your API keys
streamlit run app.py
```

## Provider setup

| Provider | Env var | Notes |
|---|---|---|
| `google-gemini` | `GOOGLE_API_KEY` | Default. Uses Imagen 3 for generation + `chatlas` ChatGoogle for prompt enhancement |
| `openai` | `OPENAI_API_KEY` | DALL-E 3 / DALL-E 2 |

## chatlas integration

[chatlas](https://github.com/posit-dev/chatlas) by posit-dev is used as the unified LLM interface. When the **Enhance prompt with Gemini** checkbox is enabled, `ChatGoogle` sends your prompt to Gemini for refinement before image generation:

```python
from chatlas import ChatGoogle

chat = ChatGoogle(api_key="...")
enhanced = chat.chat("Improve this image prompt: ...")
```

This makes it easy to swap in other chatlas-supported providers (Anthropic, OpenAI, Azure, Ollama) for the prompt-enhancement step independently from the image generation provider.

## Persistence schema

### `generations`
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| title | TEXT | Optional human-readable label |
| project_name | TEXT | Deck / presentation grouping |
| tags | TEXT | Comma-separated tags |
| base_prompt | TEXT | Original user prompt |
| style_preset_id | INTEGER | FK → style_presets |
| style_prompt | TEXT | Style text appended to base prompt |
| final_prompt | TEXT | Combined prompt sent to provider |
| provider | TEXT | e.g. `google-gemini` |
| model | TEXT | e.g. `imagen-3.0-generate-002` |
| settings | TEXT | JSON blob of provider-specific settings |
| output_path | TEXT | Local path to saved image file |
| created_at | TEXT | ISO-8601 UTC timestamp |

### `style_presets`
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| name | TEXT | Unique preset name |
| description | TEXT | Optional description |
| style_prompt | TEXT | Reusable style text |
| created_at | TEXT | ISO-8601 UTC timestamp |

## Railway deployment

1. Create a Railway project and connect this repo.
2. Add a **Volume** mounted at `/data`.
3. Set environment variables:
   ```
   DB_PATH=/data/db.sqlite3
   STORAGE_DIR=/data/images
   GOOGLE_API_KEY=...
   ```
4. Deploy — Railway reads `railway.toml` for build and start commands.
