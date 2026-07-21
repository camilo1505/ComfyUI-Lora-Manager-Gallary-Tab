# Outputs Gallery — Design Spec

**Date:** 2026-07-21
**Status:** Approved

## Overview

Add a new "Outputs" tab to the standalone web UI that displays images generated with `Save Image (LoraManager)` from ComfyUI's output directory. The page **follows the exact same layout pattern as LORAs / Checkpoints / Embeddings** — folder sidebar on the left, sticky controls bar on top, and a card grid filling the remaining space. It reuses existing UI patterns (folder sidebar, sort controls, card grid) and follows the decoupled "standalone page" route registration pattern used by `stats_routes.py`.

> **Layout reference:** `templates/loras.html` — the Outputs page template is structurally identical, with the same `{% block content %}` including `controls.html`, `breadcrumb.html`, and `folder_sidebar.html`, plus a `<div class="card-grid">`. The only differences are: (1) cards display image thumbnails instead of model previews, (2) no context menu, (3) no bulk-mode overlay, (4) no duplicates banner for MVP.

## Scope (MVP)

- Focus: images only, saved via `Save Image (LoraManager)` node
- Assume user uses `Prompt (LoraManager)` for positive/negative prompt capture
- Reuse sidebar folder browser and sort button panel from existing pages
- Sort: creation date ascending/descending only

## Architecture

### New Files (6)

| File | Purpose |
|------|---------|
| `py/services/outputs_service.py` | Scan output_dir, extract embedded metadata from images |
| `py/routes/outputs_routes.py` | Register GET /outputs page route and REST API endpoints |
| `templates/outputs.html` | Page template extending base.html |
| `static/js/outputs.js` | OutputsPageManager class |
| `static/css/outputs.css` | Page-specific styles (optional — likely unnecessary, all styles come from shared `style.css`) |

### Modified Files (4)

| File | Change | Lines |
|------|--------|-------|
| `templates/components/header.html` | Add nav `<a>` between embeddings and stats | +1 |
| `py/lora_manager.py` | Import + register OutputsRoutes | +2 |
| `standalone.py` | Import + register OutputsRoutes | +2 |
| `locales/en.json` | Add `"outputs": "Outputs"` under `header.navigation` | +1 |

## Backend

### OutputsService (`py/services/outputs_service.py`)

No cache, no SQLite. Scans on every request. Extracts metadata on-the-fly.

```python
class OutputsService:
    def scan_outputs(self, folder: str = None, sort: str = "created_at", order: str = "desc"):
        """Walk output_dir, extract metadata from images, return sorted list + folder tree."""
        
    def get_thumbnail(self, path: str, size: int = 300):
        """Generate and return a thumbnail as webp bytes."""
        
    def get_full_image(self, path: str):
        """Return full-resolution image file."""
        
    def delete_image(self, path: str):
        """Delete an image file. Validate path is within output_dir."""
        
    def open_folder_location(self, path: str):
        """Open file manager at the folder containing the image (standalone mode only)."""
```

Metadata extraction uses `PIL.Image.open()` + `piexif.load()` to read the Structured Diffusion metadata embedded by `SaveImageLM`. Falls back gracefully for images without metadata (shows filename + date only).

### Routes (`py/routes/outputs_routes.py`)

Follows the `StatsRoutes` pattern — creates its own `jinja2.Environment`, registers routes directly via `app.router.add_get()`.

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/outputs` | `handle_outputs_page` | Render outputs.html |
| GET | `/api/lm/outputs/list` | `handle_list` | JSON: images + folders |
| GET | `/api/lm/outputs/thumbnail` | `handle_thumbnail` | Serve thumbnail (webp) |
| GET | `/api/lm/outputs/image` | `handle_image` | Serve full image |
| DELETE | `/api/lm/outputs/delete` | `handle_delete` | Delete image |
| GET | `/api/lm/outputs/download` | `handle_download` | Download with Content-Disposition |
| POST | `/api/lm/outputs/open-folder` | `handle_open_folder` | Open file manager |

### API Response: GET `/api/lm/outputs/list`

```json
{
  "images": [{
    "filename": "ComfyUI_00001_.png",
    "relative_path": "subfolder/ComfyUI_00001_.png",
    "size": 2457600,
    "created_at": "2026-07-21T15:30:00",
    "prompt": "a beautiful landscape...",
    "negative_prompt": "blurry, low quality...",
    "seed": 123456789,
    "sampler": "euler",
    "scheduler": "normal",
    "steps": 20,
    "cfg_scale": 7.0,
    "checkpoint": "sd_xl_base_1.0.safetensors",
    "loras": "detail_slider_v4:0.5",
    "has_metadata": true
  }],
  "total": 42,
  "folders": ["ComfyUI", "ComfyUI_00001_", "test_batch"]
}
```

Query params: `sort=created_at`, `order=asc|desc`, `path=` (optional subfolder filter).

## Frontend

### Template (`templates/outputs.html`)

Extends `base.html`. Sets `page_id = "outputs"`. **Mirrors the exact structure of `templates/loras.html`** (`templates/checkpoints.html`, `templates/embeddings.html`):

```jinja2
{% extends "base.html" %}
{% block page_id %}outputs{% endblock %}

{% block content %}
    {% include 'components/controls.html' %}
    {% include 'components/breadcrumb.html' %}
    {% include 'components/folder_sidebar.html' %}
    <div class="card-grid" id="outputGrid">
        <!-- Image cards inserted by JS -->
    </div>
{% endblock %}

{% block main_script %}
<script type="module" src="/loras_static/js/outputs.js?v={{ version }}"></script>
{% endblock %}
```

No `{% block additional_components %}` (no context menu needed for MVP).  
No `{% block overlay %}` (no bulk mode for MVP).  
No `{% block page_css %}` (relies entirely on shared `style.css` — card grid, sidebar, controls already styled).

The lightbox is **not rendered server-side**; instead it is created dynamically by the JS `OutputsPageManager` using the existing `.media-viewer-overlay` pattern from `static/css/components/media-viewer.css`.

**i18n note:** This template uses `{{ t('...') }}` for all user-facing strings, consistent with the other pages. The `t()` function and `page_id` are passed to the template context by the route handler.

### JavaScript (`static/js/outputs.js`)

Follows the same class structure as `LoraPageManager` in `static/js/loras.js`:

```javascript
class OutputsPageManager {
    async initialize()           // appCore.initialize(), setup controls, load data
    async loadImages()           // fetch /api/lm/outputs/list
    renderGrid(images)           // create card elements with lazy-loaded thumbnails
    setupSortControls()          // reuse sort-select + direction events from controls.html
    setupFolderSidebar()         // folder click → reload grid filtered by folder
    openLightbox(imageData)      // show full image + metadata panel using shared MediaViewer
    setupKeyboardNav()           // ← → for prev/next, Esc to close
    async copyToClipboard(text)  // clipboard API
    async deleteImage(path)      // confirmation dialog → DELETE API → reload
    async downloadImage(path)    // trigger browser download
    async openFolder(path)       // POST open-folder
}
```

**Key difference from `LoraPageManager`:** the card rendering creates `<img>` elements (lazy-loaded thumbnails via `GET /api/lm/outputs/thumbnail`) instead of model preview images, and the lightbox uses a metadata panel inside `.media-viewer-overlay` to display generation info (prompt, seed, sampler, etc.) rather than model details.

### Card Design (Grid)

Same `.card-grid` / `.model-card` structure from `static/css/components/card.css` used by LORAs/Checkpoints/Embeddings. Each card shows:
- Lazy-loaded thumbnail via `<img>` with `GET /api/lm/outputs/thumbnail`
- Overlay on hover: date, truncated prompt (first 80 chars), seed
- Click → opens lightbox

No CSS changes needed — the existing card grid styles apply as-is.

### Lightbox Design

Reuses the **existing `.media-viewer-overlay`** from `static/css/components/media-viewer.css` (the same component used by `MediaViewer.js` for model example images). Full-screen overlay with:
- Image centered, max 90vh, dark background
- Top-right: close (✕), download, delete buttons
- Bottom panel: all metadata fields, each clickable to copy
- Bottom action buttons: Copy Prompt, Copy All, Copy Seed, Download, Open Folder, Delete
- Keyboard: ←/→ navigate, Esc close

No CSS changes needed — the overlay container, close button, nav arrows, and counter already exist in `media-viewer.css`. The metadata panel is a new child element rendered by JS inside the overlay (not a new CSS component).

## Security

- All file paths validated to be within `output_dir` (path traversal prevention)
- Delete endpoint requires confirmation on frontend
- Static file serving uses aiohttp's built-in path validation

## i18n

New keys in `locales/en.json`:
```json
{
  "header": {
    "navigation": {
      "outputs": "Outputs"
    }
  },
  "outputs": {
    "all_outputs": "All Outputs",
    "no_outputs": "No outputs found",
    "sort_by_date": "Date",
    "ascending": "Oldest first",
    "descending": "Newest first",
    "prompt": "Prompt",
    "negative_prompt": "Negative Prompt",
    "seed": "Seed",
    "sampler": "Sampler",
    "scheduler": "Scheduler",
    "steps": "Steps",
    "cfg_scale": "CFG Scale",
    "checkpoint": "Model",
    "loras": "LoRAs",
    "no_metadata": "No generation metadata found",
    "copy_prompt": "Copy Prompt",
    "copy_all": "Copy All",
    "copy_seed": "Copy Seed",
    "download": "Download",
    "open_folder": "Open Folder",
    "delete": "Delete",
    "delete_confirm": "Are you sure you want to delete this image?",
    "copied": "Copied!"
  }
}
```

After adding keys, run: `python scripts/sync_translation_keys.py`

## Testing

- Backend: unit tests for `OutputsService` (mock `folder_paths`, test metadata extraction from known images)
- Backend: route tests for all endpoints (mock service)
- Frontend: JS tests for `OutputsPageManager` (vitest + jsdom)
- E2E: `lora-manager-e2e` skill to validate full flow

## Out of Scope (Future)

- Video/animated outputs
- Batch delete/select
- Search by prompt text
- Filter by model/LoRA/seed range
- Thumbnail cache on disk
- Drag & drop to reorder
- Export metadata as JSON/CSV
