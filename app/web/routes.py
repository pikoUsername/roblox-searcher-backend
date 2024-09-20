import json
from datetime import datetime

from aiohttp import ClientSession
from fastapi import FastAPI, APIRouter, Request, Depends, HTTPException
from redis.asyncio import Redis

from app.web.interfaces import ITokenRepository
from app.web.logger import get_logger
from app.web.provider import token_repo_provider, get_token, get_redis, get_client
from app.web.schemas import GamePassInfo, PlayerData


def load_routes(app: FastAPI):
	app.include_router(router)


logger = get_logger()
router = APIRouter(prefix="/api")


def form_batch_request(users: list[dict]) -> list[dict]:
	result = []
	for user in users:
		user_id = user["id"]

		result.append({
			"requestId": f"{user_id}:undefined:AvatarHeadshot:150x150:webp:regular",
			"format": "webp",
			"size": "150x150",
			"targetId": user_id,
			"type": "AvatarHeadshot",
		})
	return result


def form_users_response(users: list[dict], batch_info: list[dict]) -> list[PlayerData]:
	result = []

	for user, batch in zip(users, batch_info):
		result.append(
			PlayerData(
				avatar_url=batch["imageUrl"],
				name=user["name"],
				display_name=user["displayName"],
				user_id=user["id"], 
			)
		)

	return result


@router.post("/create-token")
async def create_token(request: Request, expiry_minutes: int = 60, token_repo: ITokenRepository = Depends(token_repo_provider)) -> dict:
	logger.info(f"Origin host: {request.client.host}")
	if request.client.host not in "127.0.0.1":
		raise HTTPException(status_code=403, detail="Invalid origin host")
	token_id = await token_repo.create_token(expiry_minutes)
	return {
		"token": str(token_id),
		"expires_in": expiry_minutes
	}


@router.get("/search/player/{player_name}")
async def search_player(
	player_name: str,
	redis: Redis = Depends(get_redis),
	client: ClientSession = Depends(get_client)
) -> list[PlayerData] | None:
	result = await redis.get(f"players_{player_name}")

	if result:
		logger.info("Found from redis cache")
		result = json.loads(result)
		return [PlayerData(**v) for v in result]

	logger.info("Sending 'search user' request to roblox api")
	response = await client.get(f"https://users.roblox.com/v1/users/search?keyword={player_name}&limit=10")
	if response.status == 429:
		logger.error("No search user response")
		raise HTTPException(detail="Rate limit exceeded", status_code=429)
	_data = await response.json()
	logger.info(_data)
	users = _data["data"]

	batch_response = await client.post("https://thumbnails.roblox.com/v1/batch", json=form_batch_request(users))
	if batch_response.status == 429:
		logger.error("No batch response")
		raise HTTPException(detail="Rate limit exceeded", status_code=429)
	_data = await batch_response.json()
	data = form_users_response(users, _data["data"])

	logger.info(f"lset is placed in players_{player_name}")
	await redis.set(f"players_{player_name}", json.dumps([x.dict() for x in data]))

	return data


@router.get("/search/{game_id}/gamepass")
async def search_gamepass_by_id(
	game_id: int,
	redis: Redis = Depends(get_redis),
	client: ClientSession = Depends(get_client)
) -> list[GamePassInfo] | None:
	result = await redis.get(f"game_{game_id}")

	if result:
		logger.info("Found from redis cache")
		result = json.loads(result)
		return [GamePassInfo(**v) for v in result]
	logger.info("Sending 'search by gamepasses' request to roblox api")

	universe_response = await client.get(f"https://apis.roblox.com/universes/v1/places/{game_id}/universe")
	if universe_response.status == 429:
		logger.error("No universe response")
		return

	_data = await universe_response.json()

	universe_id = _data["universeId"]
	response = await client.get(f"https://games.roblox.com/v1/games/{universe_id}/game-passes?limit=100&sortOrder=1")
	if response.status == 429:
		logger.error("No gamepass response")
		return

	gamepasses: list[dict] = (await response.json())['data']
	data = [GamePassInfo(**v) for v in gamepasses]

	logger.info(f"Lset to game_{game_id}")
	await redis.set(f"game_{game_id}", json.dumps(gamepasses))

	return data


_start_time = datetime.now()


@router.get("/heartbeat")
async def heartbeat():
	return {"uptime": datetime.now() - _start_time, "ok": True}
