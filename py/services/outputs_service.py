import os
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from PIL import Image

from .outputs_cache_service import OutputsCacheService

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _extract_png_metadata(file_path: str) -> dict:
    try:
        img = Image.open(file_path)
        raw = img.text.get("parameters", "") if hasattr(img, "text") else img.info.get("parameters", "")
        if not raw:
            return {"has_metadata": False}
        return _parse_parameters(raw)
    except Exception:
        return {"has_metadata": False}


def _extract_jpeg_metadata(file_path: str) -> dict:
    try:
        import piexif
        exif = piexif.load(file_path)
        user_comment = exif.get("Exif", {}).get(piexif.ExifIFD.UserComment, b"")
        if isinstance(user_comment, bytes):
            raw = user_comment.decode("utf-8", errors="ignore").lstrip("UNICODE\x00").strip("\x00")
        else:
            raw = str(user_comment)
        if not raw:
            return {"has_metadata": False}
        return _parse_parameters(raw)
    except Exception:
        return {"has_metadata": False}


def _extract_webp_metadata(file_path: str) -> dict:
    try:
        img = Image.open(file_path)
        raw = img.info.get("parameters", "")
        if not raw:
            return {"has_metadata": False}
        return _parse_parameters(raw)
    except Exception:
        return {"has_metadata": False}


def _parse_parameters(raw: str) -> dict:
    result = {"has_metadata": True}
    lines = raw.split("\n")

    prompt_lines = []
    neg_prompt_start = -1
    for i, line in enumerate(lines):
        if line.startswith("Negative prompt:"):
            neg_prompt_start = i
            break
        prompt_lines.append(line)

    result["prompt"] = "\n".join(prompt_lines).strip()

    if neg_prompt_start >= 0:
        neg = lines[neg_prompt_start][len("Negative prompt:"):].strip()
        result["negative_prompt"] = neg

    params_text = raw.split("Negative prompt:", 1)[-1] if "Negative prompt:" in raw else raw
    param_str = params_text.split("\n", 1)[-1] if "\n" in params_text else params_text

    patterns = {
        "steps": r"Steps:\s*(\d+)",
        "sampler": r"Sampler:\s*([^,]+)",
        "cfg_scale": r"CFG scale:\s*([\d.]+)",
        "seed": r"Seed:\s*(\d+)",
        "size": r"Size:\s*(\d+x\d+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, param_str)
        if match:
            result[key] = match.group(1).strip()

    model_name = re.search(r"Model:\s*([^,]+)", param_str)
    if model_name:
        result["checkpoint"] = model_name.group(1).strip()
    else:
        model_hash = re.search(r"Model hash:\s*([^,]+)", param_str)
        if model_hash:
            result["checkpoint"] = model_hash.group(1).strip()

    return result


def _extract_file_metadata(file_path: str) -> dict:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".png":
        return _extract_png_metadata(file_path)
    elif ext in (".jpg", ".jpeg"):
        return _extract_jpeg_metadata(file_path)
    elif ext == ".webp":
        return _extract_webp_metadata(file_path)
    return {"has_metadata": False}


def _make_cache_key(entry_path: str, stat) -> tuple:
    return (os.path.getmtime(entry_path) if hasattr(stat, 'st_mtime') else stat.st_mtime, stat.st_size)


def _make_image_dict(filename: str, full_path: str, rel: str, stat, meta: dict) -> dict:
    resolution = meta.get("size", "")
    return {
        "filename": filename,
        "file_name": filename,
        "relative_path": rel,
        "file_path": full_path.replace(os.sep, "/"),
        "preview_url": f"/outputs_static/{rel}",
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "resolution": resolution,
        "sampler": meta.get("sampler", ""),
        "cfg": float(meta["cfg_scale"]) if meta.get("cfg_scale") else None,
        "steps": int(meta["steps"]) if meta.get("steps") else None,
        "seed": int(meta["seed"]) if meta.get("seed") else None,
        "checkpoint": meta.get("checkpoint", ""),
        "prompt": meta.get("prompt", ""),
        "negative_prompt": meta.get("negative_prompt", ""),
        "has_metadata": meta.get("has_metadata", False),
    }


def _build_preview_url(relative_path: str) -> str:
    return f"/outputs_static/{relative_path}"


class OutputsService:
    def __init__(self, output_dir: str):
        self._output_dir = output_dir
        self._cache = OutputsCacheService.get_instance()

    def _get_output_dir(self) -> str:
        return self._output_dir

    def scan_outputs(
        self,
        folder: Optional[str] = None,
        sort: str = "created_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        output_dir = self._get_output_dir()
        scan_dir = (
            os.path.join(output_dir, folder)
            if folder
            else output_dir
        )

        if not os.path.isdir(scan_dir):
            return {"images": [], "total": 0, "total_pages": 0, "folders": [], "items": []}

        # Walk filesystem to discover current state
        discovered: List[Dict] = []
        folders_set: Set[str] = set()

        if folder:
            for entry in os.scandir(scan_dir):
                if entry.is_dir():
                    folders_set.add(entry.name)
                    continue
                ext = os.path.splitext(entry.name)[1].lower()
                if ext not in IMAGE_EXTENSIONS:
                    continue
                stat = entry.stat()
                rel = os.path.join(folder, entry.name).replace(os.sep, "/")
                discovered.append({
                    "filename": entry.name,
                    "full_path": entry.path,
                    "relative_path": rel,
                    "folder": folder,
                    "stat": stat,
                })
        else:
            for root, dirs, files in os.walk(scan_dir):
                rel = os.path.relpath(root, output_dir)
                for d in dirs:
                    key = os.path.join(rel, d).replace(os.sep, "/") if rel != "." else d
                    folders_set.add(key)
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext not in IMAGE_EXTENSIONS:
                        continue
                    full_path = os.path.join(root, f)
                    stat = os.stat(full_path)
                    subfolder = rel if rel != "." else None
                    discovered.append({
                        "filename": f,
                        "full_path": full_path,
                        "relative_path": os.path.join(subfolder, f).replace(os.sep, "/") if subfolder else f,
                        "folder": subfolder or "",
                        "stat": stat,
                    })

        # Extract metadata: use cache for unchanged files, PIL for new/changed
        cached_paths = {d["relative_path"]: d for d in discovered}
        existing = self._cache.get_cache_entries(list(cached_paths.keys())) if self._cache.is_cache_populated() else {}

        new_entries: List[Dict] = []
        for d in discovered:
            rel = d["relative_path"]
            cached = existing.get(rel)
            if cached and cached["mtime"] == d["stat"].st_mtime and cached["size"] == d["stat"].st_size:
                meta = {
                    "has_metadata": bool(cached["has_metadata"]),
                    "sampler": cached["sampler"] or "",
                    "cfg_scale": str(cached["cfg"]) if cached["cfg"] is not None else None,
                    "steps": str(cached["steps"]) if cached["steps"] is not None else None,
                    "seed": str(cached["seed"]) if cached["seed"] is not None else None,
                    "size": cached["resolution"] or "",
                }
                model_name_val = cached.get("checkpoint", "")
                if model_name_val:
                    meta["checkpoint"] = model_name_val
                meta_prompt = cached.get("prompt", "")
                meta_neg = cached.get("negative_prompt", "")
                if meta_prompt:
                    meta["prompt"] = meta_prompt
                if meta_neg:
                    meta["negative_prompt"] = meta_neg
            else:
                meta = _extract_file_metadata(d["full_path"])
                new_entries.append({
                    "filename": d["filename"],
                    "file_path": d["full_path"].replace(os.sep, "/"),
                    "relative_path": rel,
                    "folder": d["folder"],
                    "size": d["stat"].st_size,
                    "mtime": d["stat"].st_mtime,
                    "created_at": datetime.fromtimestamp(d["stat"].st_ctime).isoformat(),
                    "sampler": meta.get("sampler", ""),
                    "cfg": float(meta["cfg_scale"]) if meta.get("cfg_scale") else None,
                    "steps": int(meta["steps"]) if meta.get("steps") else None,
                    "seed": int(meta["seed"]) if meta.get("seed") else None,
                    "checkpoint": meta.get("checkpoint", ""),
                    "resolution": meta.get("size", ""),
                    "prompt": meta.get("prompt", ""),
                    "negative_prompt": meta.get("negative_prompt", ""),
                    "has_metadata": meta.get("has_metadata", False),
                })

        # Cache newly extracted metadata
        if new_entries:
            self._cache.cache_outputs(new_entries)

        # Purge stale entries (files in cache but no longer on disk)
        discovered_paths = {d["relative_path"] for d in discovered}
        stale = [rel for rel in existing if rel not in discovered_paths]
        if stale:
            self._cache._delete_batch(stale)

        # Build full dicts for the response
        all_images = []
        for d in discovered:
            rel = d["relative_path"]
            cached = existing.get(rel)
            if cached and cached["mtime"] == d["stat"].st_mtime and cached["size"] == d["stat"].st_size:
                all_images.append(self._build_from_cache(cached, rel))
            else:
                for ne in new_entries:
                    if ne["relative_path"] == rel:
                        all_images.append(ne)
                        break

        # Sort
        reverse = order == "desc"
        if sort == "created_at":
            all_images.sort(key=lambda x: x["created_at"], reverse=reverse)
        else:
            all_images.sort(key=lambda x: x["filename"].lower(), reverse=reverse)

        total = len(all_images)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        paged = all_images[start:end]

        return {
            "images": paged,
            "total": total,
            "total_pages": total_pages,
            "folders": sorted(folders_set),
            "items": paged,
        }

    def _build_from_cache(self, cached: dict, relative_path: str) -> dict:
        return {
            "filename": cached["filename"],
            "file_name": cached["filename"],
            "relative_path": relative_path,
            "file_path": cached["file_path"],
            "preview_url": _build_preview_url(relative_path),
            "size": cached["size"],
            "created_at": cached["created_at"],
            "resolution": cached["resolution"] or "",
            "sampler": cached["sampler"] or "",
            "cfg": cached["cfg"],
            "steps": cached["steps"],
            "seed": cached["seed"],
            "checkpoint": cached.get("checkpoint", ""),
            "prompt": cached.get("prompt", ""),
            "negative_prompt": cached.get("negative_prompt", ""),
            "has_metadata": bool(cached["has_metadata"]),
        }

    def get_output_detail(self, relative_path: str) -> Optional[Dict]:
        cached = self._cache.get_output_detail(relative_path)
        if not cached:
            return None
        return {
            "filename": cached["filename"],
            "file_name": cached["filename"],
            "relative_path": relative_path,
            "file_path": cached["file_path"],
            "preview_url": _build_preview_url(relative_path),
            "size": cached["size"],
            "created_at": cached["created_at"],
            "resolution": cached["resolution"] or "",
            "sampler": cached["sampler"] or "",
            "cfg": cached["cfg"],
            "steps": cached["steps"],
            "seed": cached["seed"],
            "checkpoint": cached.get("checkpoint", ""),
            "prompt": cached.get("prompt", ""),
            "negative_prompt": cached.get("negative_prompt", ""),
            "has_metadata": bool(cached["has_metadata"]),
        }

    def delete_by_path(self, relative_path: str) -> bool:
        full_path = os.path.normpath(os.path.join(self._output_dir, relative_path))
        if not full_path.startswith(os.path.normpath(self._output_dir)):
            return False
        if os.path.isfile(full_path):
            os.remove(full_path)
            self._cache.delete_by_path(relative_path)
            return True
        return False

    def get_folder_tree(self) -> dict:
        output_dir = self._get_output_dir()
        if not os.path.isdir(output_dir):
            return {}
        tree = {}
        for entry in os.scandir(output_dir):
            if entry.is_dir():
                tree[entry.name] = {}
        return tree
