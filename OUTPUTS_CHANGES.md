# Outputs Gallery Tab — Summary

Adds a new "Outputs" tab between Embeddings and Stats that displays ComfyUI output images with embedded generation metadata.

## Created Files

### Backend
| File | Purpose |
|------|---------|
| `py/services/outputs_service.py` | Scans output directory recursively, extracts generation metadata from PNG/JPG/WEBP (prompt, negative prompt, sampler, CFG, steps, seed, size, checkpoint) via PIL |
| `py/routes/output_routes.py` | Page route (`GET /outputs`), REST API (`GET /api/lm/outputs/list`, `DELETE /api/lm/outputs/delete`), static file serving (`/outputs_static`) |

### Frontend
| File | Purpose |
|------|---------|
| `static/js/outputs.js` | `OutputsPageManager` class — page initialization, independent of LoRAs |
| `static/js/components/controls/OutputsControls.js` | Lightweight controls: sort, refresh, bulk mode, folder sidebar, context menu (download/delete selected) |
| `static/js/components/shared/OutputCard.js` | Card rendering: resolution badge, metadata status, blur toggle, image preview, generation params (sampler/CFG/steps/seed), and a metadata modal (reuses existing `.modal-content` structure) |
| `templates/outputs.html` | Page template extending `base.html` with `page_id=outputs` |
| `templates/components/outputs_controls.html` | Custom controls bar: sort (name/date), refresh, bulk |

## Modified Files

### Backend
| File | Change |
|------|--------|
| `standalone.py` | Added `get_output_directory()` to `MockFolderPaths`, registered `OutputRoutes` |
| `py/lora_manager.py` | Import + register `OutputRoutes` |

### Frontend
| File | Change |
|------|--------|
| `templates/components/header.html` | Added Outputs nav item (between Embeddings and Stats), added `/outputs` path detection |
| `static/js/api/apiConfig.js` | Added `OUTPUTS` to `MODEL_TYPES` and `MODEL_CONFIG` |
| `static/js/state/index.js` | Added `outputs` page state with bulk/recursive search options |
| `static/js/core.js` | Added `'outputs'` to page features (infinite scroll + context menus) |
| `static/js/utils/infiniteScroll.js` | Custom data fetcher for outputs (`/api/lm/outputs/list`), OutputCard delegation setup, recursive folder filter support |
| `static/js/components/Header.js` | Added `/outputs` path detection, skip FilterManager/SearchManager for outputs |
| `static/js/components/controls/index.js` | Added `OutputsControls` to factory |
| `static/js/components/SidebarManager.js` | Added `'Outputs'` display name |
| `static/js/components/initialization.js` | Added `/outputs` page type detection |
| `static/css/components/card.css` | Added styles for output metadata badge, param badges, blur toggle, modal metadata panel |

### Tests
| File | Change |
|------|--------|
| `tests/routes/test_lora_manager_lifecycle.py` | Added `/outputs_static` to expected static routes |

### Locales
| File | Change |
|------|--------|
| `locales/en.json` | Added `header.navigation.outputs`, `outputs.metadataAvailable`, `outputs.metadataUnavailable` |
| All other `locales/*.json` | Synced via `scripts/sync_translation_keys.py` |

### Config
| File | Change |
|------|--------|
| `.gitignore` | Added `pnpm-lock.yaml`, `pnpm-workspace.yaml` |

## Architecture Notes

- **Fully independent** from LoRAs — no imports from `ModelCard.js`, `LorasControls.js`, `ModelModal.js`, or `loraApi.js`
- **No cache/SQLite** — scans output directory on every request (per design spec)
- **Metadata extraction**: reads PNG `tEXt` chunks (ComfyUI `SaveImageLM` format), supports JPEG (piexif) and WEBP
- **Bulk operations**: reuses existing `#bulkContextMenu` element, supports download/delete selected images
- **Folder sidebar**: reuses `SidebarManager` with a custom API client that builds tree from `/api/lm/outputs/list` folders
- **Sort**: by name (A-Z/Z-A) or creation date (newest/oldest)
- **Recursive/Filtered**: sidebar folder click filters non-recursively; "include subfolders" toggle enables recursive scan
- **Blur toggle**: built-in eye icon on every card, toggles CSS blur filter
- **Metadata modal**: reuses existing `.modal-content` / `.modal-header` / `.info-section` / `.info-grid` CSS classes (same visual style as LoRA model modal)
