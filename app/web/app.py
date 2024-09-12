"""
задача этого сервиса
делать поиск по имени геймпасса, отправлять в очередь для покупки геймпасса
делать поиск по нику игрока (по 3 апи, и менять их по очереди), и фильтровать ввод
"""

from dotenv import load_dotenv
from fastapi import FastAPI

from app.providers import get_token_service
from app.repos import UserTokenRepository
from app.services.db import get_db_conn
from app.settings import get_settings
from app.web.db import get_db_session, registry
from app.web.logger import configure_logging, LoggingSettings
from app.web.middlewares.init import load_middlewares
from app.web.models import load_models
from app.web.routes import load_routes
from app.web.websettings import get_web_settings


async def get_app(debug: bool = True) -> FastAPI:
	load_dotenv()

	app = FastAPI(debug=debug)
	websettings = get_web_settings()

	configure_logging(LoggingSettings(path=websettings.log_path))

	load_middlewares(app)
	load_models(registry)
	load_routes(app)

	return app


