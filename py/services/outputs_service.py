import os
import re
import logging
from datetime import datetime
from typing import Optional

from PIL import Image

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


class OutputsService:
    def __init__(self, output_dir: str):
        self._output_dir = output_dir

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

        images = []
        folders_set = set()

        if folder:
            for entry in os.scandir(scan_dir):
                if entry.is_dir():
                    folders_set.add(entry.name)
                    continue
                ext = os.path.splitext(entry.name)[1].lower()
                if ext not in IMAGE_EXTENSIONS:
                    continue
                stat = entry.stat()
                images.append(self._build_entry(entry, folder, stat))
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
                    images.append(self._build_entry_file(f, full_path, subfolder, stat))


        reverse = order == "desc"
        if sort == "created_at":
            images.sort(key=lambda x: x["created_at"], reverse=reverse)
        else:
            images.sort(key=lambda x: x["filename"].lower(), reverse=reverse)

        total = len(images)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        paged = images[start:end]

        return {
            "images": paged,
            "total": total,
            "total_pages": total_pages,
            "folders": sorted(folders_set),
            "items": paged,
        }

    def _build_entry(self, entry, folder, stat):
        rel = (
            os.path.join(folder, entry.name).replace(os.sep, "/")
            if folder
            else entry.name
        )
        meta = _extract_file_metadata(entry.path)
        return self._make_image_dict(entry.name, entry.path, rel, stat, meta)

    def _build_entry_file(self, filename, full_path, folder, stat):
        rel = (
            os.path.join(folder, filename).replace(os.sep, "/")
            if folder
            else filename
        )
        meta = _extract_file_metadata(full_path)
        return self._make_image_dict(filename, full_path, rel, stat, meta)

    def _make_image_dict(self, filename, full_path, rel, stat, meta):
        resolution = meta.get("size", "")
        return {
            "filename": filename,
            "file_name": filename,
            "relative_path": rel,
            "file_path": full_path.replace(os.sep, "/"),
            "preview_url": f"/outputs_static/{rel}",
            "size": stat.st_size,
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

    def get_folder_tree(self) -> dict:
        output_dir = self._get_output_dir()
        if not os.path.isdir(output_dir):
            return {}

        tree = {}
        for entry in os.scandir(output_dir):
            if entry.is_dir():
                tree[entry.name] = {}
        return tree
