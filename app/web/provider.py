from typing import Annotated, Generator, Tuple
from uuid import UUID

import aiohttp
from aiohttp import CookieJar
from fastapi import Depends, HTTPException, Request
from fastapi.params import Header
from redis.asyncio import Redis
from seleniumrequests import Firefox
from sqlalchemy.ext.asyncio import AsyncSession
from yarl import URL

from app.providers import get_token_service
from app.repos import UserTokenRepository
from app.services.db import get_db_conn
from app.services.interfaces import BasicDBConnector
from app.settings import get_settings
from app.web.db import setup_engine, sa_session_factory, get_db_session
from app.web.interfaces import ITokenRepository, ITransactionsRepo
from app.web.logger import get_logger
from app.web.repos import TokenRepository, TransactionRepository, BotTokenRepository, BonusesRepository
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


async def transaction_repo_provider(session: AsyncSession = Depends(session_provider)) -> ITransactionsRepo:
	return TransactionRepository(session)


async def bot_token_repo_provider(session: AsyncSession = Depends(session_provider)) -> BotTokenRepository:
	return BotTokenRepository(session)


async def bonuses_repo_provider(session: AsyncSession = Depends(session_provider)) -> BonusesRepository:
	return BonusesRepository(session)


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


def client_provider(request: Request) -> aiohttp.ClientSession:
	return request.app.state.client_session


def requests_driver_provider(request: Request) -> Firefox:
	return request.app.state.driver


def get_client(token: str) -> aiohttp.ClientSession:
	settings = get_settings()

	if not token:
		logger.warning("Token will be empty")
	logger.info(f"Token has been selected, {token[0:150]}")
	cookie_jar = CookieJar(unsafe=True)
	cookie_jar.update_cookies({".ROBLOSECURITY": token}, response_url=URL("roblox.com"))
	client = aiohttp.ClientSession(
		headers={
			'User-Agent': settings.user_agent,
		},
		cookie_jar=cookie_jar
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

