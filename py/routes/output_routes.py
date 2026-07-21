import logging
import jinja2
from aiohttp import web

from ..config import config
from ..services.settings_manager import get_settings_manager
from ..services.server_i18n import server_i18n
from ..services.service_registry import ServiceRegistry

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


class OutputRoutes:
    def __init__(self):
        self.lora_scanner = None
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(config.templates_path),
            autoescape=True
        )

    async def init_services(self):
        self.lora_scanner = await ServiceRegistry.get_lora_scanner()

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
            await self.init_services()

            is_initializing = (
                self.lora_scanner._cache is None
                or (
                    hasattr(self.lora_scanner, 'is_initializing')
                    and self.lora_scanner.is_initializing()
                )
                or (
                    hasattr(self.lora_scanner, '_is_initializing')
                    and self.lora_scanner._is_initializing
                )
            )

            settings_object = settings
            user_language = settings_object.get('language', 'en')
            settings_manager = (
                settings_object
                if not isinstance(settings_object, _SettingsProxy)
                else settings_object._resolve()
            )

            server_i18n.set_locale(user_language)

            if not hasattr(self.template_env, '_i18n_filter_added'):
                self.template_env.filters['t'] = server_i18n.create_template_filter()
                self.template_env._i18n_filter_added = True

            template = self.template_env.get_template('outputs.html')
            rendered = template.render(
                is_initializing=is_initializing,
                settings=settings_manager,
                request=request,
                t=server_i18n.get_translation,
                version=self._get_app_version(),
            )

            return web.Response(
                text=rendered,
                content_type='text/html'
            )

        except Exception as e:
            logger.error(f"Error handling outputs request: {e}", exc_info=True)
            return web.Response(
                text="Error loading outputs page",
                status=500
            )

    def setup_routes(self, app: web.Application):
        app.router.add_get("/outputs", self.handle_outputs_page)
