from typing import Annotated, Generator, Tuple
from uuid import UUID

import aiohttp
from fastapi import Depends, HTTPException
from fastapi.params import Header
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers import get_token_service
from app.repos import UserTokenRepository
from app.services.db import get_db_conn
from app.services.interfaces import BasicDBConnector
from app.settings import get_settings
from app.web.db import setup_engine, sa_session_factory
from app.web.interfaces import ITokenRepository
from app.web.logger import get_logger
from app.web.repos import TokenRepository
from app.web.websettings import WebSettings, get_web_settings


logger = get_logger(__name__)


async def session_provider(settings: WebSettings = Depends(get_web_settings)) -> AsyncSession:
	engine = setup_engine(settings.db_dsn)
	session = sa_session_factory(engine)

	sus = session()
	try:
		yield sus
	finally:
		await sus.close()


async def token_repo_provider(session: AsyncSession = Depends(session_provider)) -> ITokenRepository:
	return TokenRepository(session)


async def get_roblox_token_repo() -> Tuple[UserTokenRepository, BasicDBConnector]:
	settings = get_settings()
	connection = await get_db_conn(settings.db_dsn.replace("+asyncpg", ""))
	token_service = await get_token_service(settings, connection)
	return token_service, connection


async def get_redis() -> Redis:
	settings = get_web_settings()
	redis = Redis(host=settings.redis_host, port=settings.redis_port)
	try:
		yield redis
	finally:
		await redis.close()


def client_provider() -> aiohttp.ClientSession: ...


async def get_client(token_repo: UserTokenRepository) -> aiohttp.ClientSession:
	settings = get_settings()
	token = await token_repo.fetch_token()
	if not token:
		logger.warning("Token will be empty")
	logger.info(f"Token has been selected, {token[0:150]}")
	client = aiohttp.ClientSession(
		headers={
			'User-Agent': settings.user_agent,
		},
		cookies={
			".ROBLOSECURITY": token,
		}
	)
	return client


async def get_token(
	token: Annotated[str, Header()] = None,
	token_repo: Annotated[ITokenRepository, Depends(token_repo_provider)] = None
) -> UUID:
	if token is None:
		raise HTTPException(status_code=403, detail="Token is incorrect")
	try:
		token = UUID(token)
	except ValueError:
		raise HTTPException(status_code=400, detail="Invalid format of token")
	if not await token_repo.validate_token(token):
		raise HTTPException(status_code=403, detail="Invalid or expired token")
	return token

