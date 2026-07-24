import io
import logging
import os
import jinja2
from aiohttp import web
from PIL import Image

from ..config import config
from ..services.settings_manager import get_settings_manager
from ..services.server_i18n import server_i18n
from ..services.outputs_service import OutputsService

logger = logging.getLogger(__name__)


class _SettingsProxy:
    def __init__(self):
        self._manager = None

    def _resolve(self):
        if self._manager is None:
            self._manager = get_settings_manager()
        return self._manager

    def get(self, *args, **kwargs):
        return self._resolve().get(*args, **kwargs)

    def __getattr__(self, item):
        return getattr(self._resolve(), item)


settings = _SettingsProxy()


def _get_output_dir():
    try:
        import folder_paths
        return folder_paths.get_output_directory()
    except (ImportError, AttributeError):
        pass

    output_path = settings.get("outputs_path", "")
    if output_path and os.path.isdir(output_path):
        return output_path

    fallback = os.path.join(os.path.dirname(__file__), "..", "..", "output")
    return os.path.abspath(fallback)


_THUMBNAIL_MAX_SIZE = 300


def _generate_thumbnail(file_path: str, size: int = _THUMBNAIL_MAX_SIZE) -> bytes:
    img = Image.open(file_path)
    img.thumbnail((size, size), Image.LANCZOS)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


class OutputRoutes:
    def __init__(self):
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(config.templates_path),
            autoescape=True
        )
        self._service = None

    def _get_service(self):
        if self._service is None:
            self._service = OutputsService(_get_output_dir())
        return self._service

    def _get_app_version(self) -> str:
        import os
        version = "1.0.0"
        short_hash = "stable"
        try:
            import toml

            current_file = os.path.abspath(__file__)
            root_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            )
            pyproject_path = os.path.join(root_dir, "pyproject.toml")

            if os.path.exists(pyproject_path):
                with open(pyproject_path, "r", encoding="utf-8") as f:
                    data = toml.load(f)
                    version = (
                        data.get("project", {}).get("version", "1.0.0").replace("v", "")
                    )

            git_dir = os.path.join(root_dir, ".git")
            if os.path.exists(git_dir):
                try:
                    import git
                    repo = git.Repo(root_dir)
                    short_hash = repo.head.commit.hexsha[:7]
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Failed to read version info: {e}")

        return f"{version}-{short_hash}"

    async def handle_outputs_page(self, request: web.Request) -> web.Response:
        try:
            user_language = settings.get("language", "en")
            settings_manager = (
                settings
                if not isinstance(settings, _SettingsProxy)
                else settings._resolve()
            )

            server_i18n.set_locale(user_language)

            if not hasattr(self.template_env, "_i18n_filter_added"):
                self.template_env.filters["t"] = server_i18n.create_template_filter()
                self.template_env._i18n_filter_added = True

            template = self.template_env.get_template("outputs.html")
            rendered = template.render(
                is_initializing=False,
                settings=settings_manager,
                request=request,
                t=server_i18n.get_translation,
                version=self._get_app_version(),
            )

            return web.Response(text=rendered, content_type="text/html")

        except Exception as e:
            logger.error(f"Error handling outputs request: {e}", exc_info=True)
            return web.Response(text="Error loading outputs page", status=500)

    async def handle_list(self, request: web.Request) -> web.Response:
        try:
            folder = request.query.get("path") or request.query.get("folder")
            sort = request.query.get("sort_by", "created_at").replace(":desc", "").replace(":asc", "")
            order = "desc"
            if ":asc" in request.query.get("sort_by", ""):
                order = "asc"
            elif request.query.get("order") == "asc":
                order = "asc"

            page = int(request.query.get("page", 1))
            page_size = int(request.query.get("page_size", 100))

            service = self._get_service()
            result = service.scan_outputs(
                folder=folder,
                sort=sort,
                order=order,
                page=page,
                page_size=page_size,
            )

            return web.json_response(result)

        except Exception as e:
            logger.error(f"Error listing outputs: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def handle_thumbnail(self, request: web.Request) -> web.Response:
        try:
            path = request.query.get("path", "")
            if not path:
                return web.Response(status=400, text="path required")

            output_dir = _get_output_dir()
            full_path = os.path.normpath(os.path.join(output_dir, path))
            if not full_path.startswith(os.path.normpath(output_dir)):
                return web.Response(status=403, text="invalid path")

            if not os.path.isfile(full_path):
                return web.Response(status=404, text="file not found")

            size = int(request.query.get("size", str(_THUMBNAIL_MAX_SIZE)))
            size = max(50, min(size, 600))

            data = _generate_thumbnail(full_path, size)
            return web.Response(body=data, content_type="image/jpeg")

        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}", exc_info=True)
            return web.Response(status=500, text=str(e))

    async def handle_detail(self, request: web.Request) -> web.Response:
        try:
            path = request.query.get("path", "")
            if not path:
                return web.json_response({"error": "path required"}, status=400)

            service = self._get_service()
            detail = service.get_output_detail(path)
            if not detail:
                return web.json_response({"error": "not found"}, status=404)

            return web.json_response(detail)

        except Exception as e:
            logger.error(f"Error getting output detail: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def handle_folders(self, request: web.Request) -> web.Response:
        try:
            service = self._get_service()
            tree = service.get_folder_tree()
            return web.json_response({"folders": list(tree.keys()), "tree": tree})
        except Exception as e:
            logger.error(f"Error listing output folders: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def handle_delete(self, request: web.Request) -> web.Response:
        try:
            path = request.query.get("path", "")
            if not path:
                return web.json_response({"error": "path required"}, status=400)

            service = self._get_service()
            success = service.delete_by_path(path)
            if success:
                return web.json_response({"success": True, "path": path})
            return web.json_response({"error": "file not found"}, status=404)

        except Exception as e:
            logger.error(f"Error deleting output: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    def setup_routes(self, app: web.Application):
        output_dir = _get_output_dir()
        if os.path.isdir(output_dir):
            app.router.add_static("/outputs_static", output_dir)
            logger.info(f"Added static route for outputs: /outputs_static -> {output_dir}")

        app.router.add_get("/outputs", self.handle_outputs_page)
        app.router.add_get("/api/lm/outputs/list", self.handle_list)
        app.router.add_get("/api/lm/outputs/thumbnail", self.handle_thumbnail)
        app.router.add_get("/api/lm/outputs/detail", self.handle_detail)
        app.router.add_get("/api/lm/outputs/folders", self.handle_folders)
        app.router.add_delete("/api/lm/outputs/delete", self.handle_delete)
