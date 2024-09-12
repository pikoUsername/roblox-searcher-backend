from typing import Annotated, Generator
from uuid import UUID

import aiohttp
from fastapi import Depends, HTTPException
from fastapi.params import Header
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers import get_token_service
from app.repos import UserTokenRepository
from app.services.db import get_db_conn
from app.settings import get_settings
from app.web.db import setup_engine, sa_session_factory
from app.web.interfaces import ITokenRepository
from app.web.repos import TokenRepository
from app.web.websettings import WebSettings, get_web_settings


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


async def get_roblox_token_repo() -> UserTokenRepository:
	settings = get_settings()
	connection = await get_db_conn(settings.db_dsn.replace("+asyncpg", ""))
	try:
		yield await get_token_service(settings, connection)
	finally:
		await connection.close()


async def get_redis() -> Redis:
	settings = get_web_settings()
	redis = Redis(host=settings.redis_host, port=settings.redis_port)
	try:
		yield redis
	finally:
		await redis.close()


async def get_client(token_repo: UserTokenRepository = Depends(get_roblox_token_repo)) -> aiohttp.ClientSession:
	settings = get_settings()
	client = aiohttp.ClientSession(
		headers={
			'user-agent': settings.user_agent,
		},
		cookies={
			".ROBLOSECURITY": await token_repo.fetch_token(),
		}
	)
	yield client

	await client.close()


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

