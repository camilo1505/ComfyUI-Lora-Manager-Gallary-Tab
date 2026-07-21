# AGENTS.md

This file provides guidance for agentic coding assistants working in this repository.
See `CLAUDE.md` for a more detailed architectural overview.

## Development Commands

### Backend

```bash
# requirements-dev.txt already includes -r requirements.txt
pip install -r requirements-dev.txt

# Standalone server (settings.json required, see below)
python standalone.py --port 8188

# All tests (performance tests are skipped by default)
pytest

# Include performance tests
pytest -m performance

# Specific test
pytest tests/test_recipes.py::test_function_name

# With coverage (as in CI)
COVERAGE_FILE=coverage/backend/.coverage pytest \
  --cov=py --cov=standalone \
  --cov-report=term-missing \
  --cov-report=html:coverage/backend/html \
  --cov-report=xml:coverage/backend/coverage.xml \
  --cov-report=json:coverage/backend/coverage.json
```

### Frontend

```bash
npm install
cd vue-widgets && npm install && cd ..

npm test                    # All tests (JS + Vue)
npm run test:js             # JS tests only
npm run test:vue            # Vue widget tests only
npm run test:coverage       # Full coverage report

# Vue widgets dev
cd vue-widgets
npm run dev                 # Build in watch mode
npm run build               # Production build → web/comfyui/vue-widgets/
npm run typecheck           # TypeScript type checking (vue-tsc --noEmit)
```

### Localization

```bash
python scripts/sync_translation_keys.py   # Run after UI string changes
```

## Setup & Environment

- **Standalone mode**: copy `settings.json.example` to `settings.json` and edit model folder paths. Set `"use_portable_settings": true` to keep settings next to the project root.
- **Dual mode detection**: `os.environ.get("LORA_MANAGER_STANDALONE", "0") == "1"`
- **ComfyUI plugin**: the root `__init__.py` auto-builds Vue widgets on import (via `py/vue_widget_builder.py`)
- CI uses **Python 3.11** and **Node 20**

## Testing

- Backend: `pytest --import-mode=importlib -m "not performance"` (see `pytest.ini`)
- `@pytest.mark.asyncio` for async tests; `asyncio_mode = auto` in pytest.ini
- `@pytest.mark.no_settings_dir_isolation` to allow tests using real filesystem paths
- `@pytest.mark.performance` for benchmarks (skipped by default)
- Fixtures in `tests/conftest.py` mock ComfyUI dependencies; use `tmp_path_factory` for isolation
- Frontend JS tests: `tests/frontend/**/*.test.js` (vitest + jsdom)
- Frontend Vue tests: `vue-widgets/tests/**/*.test.ts` (vitest + @vue/test-utils)
- `pytest.ini` norecursedirs ignores the `py/` source directory to avoid import conflicts

## Architecture

### Backend

- `__init__.py` — ComfyUI plugin entry: registers nodes via `NODE_CLASS_MAPPINGS`, sets `WEB_DIRECTORY = "./web/comfyui"`
- `standalone.py` — Standalone server: mocks `folder_paths` and node modules, starts aiohttp
- `py/lora_manager.py` — `LoraManager` class; `ServiceRegistry` singleton for DI
- Services (`py/services/`): `get_instance()` pattern; `BaseModelService` → LoRA, Checkpoint, Embedding
- `ModelScanner` for file discovery with hash deduplication; `PersistentModelCache` (SQLite)
- Routes (`py/routes/`): registrars per domain → handlers in `py/routes/handlers/` (pure functions)
- `WebSocketManager` broadcasts real-time progress
- Recipes: `py/recipes/base.py`, `py/recipes/parsers/`

### Frontend — Two Separate UI Systems

1. **Standalone Web UI**: `static/` (JS/CSS) + `templates/` (HTML) — vanilla JS, served by standalone server
2. **ComfyUI Widgets**: `web/comfyui/*.js` (vanilla JS) + `vue-widgets/src/` (Vue 3 + TypeScript + PrimeVue)
   - Vue builds to `web/comfyui/vue-widgets/`
   - **Primary stylesheet**: `web/comfyui/lm_styles.css` (NOT `static/css/`)

## Code Style

### Python
- `from __future__ import annotations` for forward references
- Custom exceptions in `py/services/errors.py`; loggers via `logging.getLogger(__name__)`
- All comments in English (per `.github/copilot-instructions.md`)

### JavaScript/TypeScript
- ES modules; camelCase functions, PascalCase classes
- Vue SFC: `<script setup lang="ts">` preferred
- Widgets: `*_widget.js` suffix; use `app.registerExtension()` + `getCustomWidgets`

## Git / Commits

- Follow repo style: `feat(...)`, `fix(...)`, `chore:`, `docs:`
- Mention GitHub issue references, e.g. `(#871)`
- Symlinks require normalized paths throughout the codebase
