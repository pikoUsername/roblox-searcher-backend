from functools import lru_cache

from pydantic import BaseSettings


class WebSettings(BaseSettings):
	db_dsn: str
	debug: bool = True
	web_debug: bool = True
	log_path: str = "logs/log_{time}.log"

	redis_host: str = "localhost"
	redis_port: int = 6379

	class Config:
		validate_assignment = True
		env_file = "./.env"


@lru_cache
def get_web_settings():
	setting = WebSettings()
	return setting