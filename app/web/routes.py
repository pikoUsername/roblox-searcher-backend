import asyncio
import json
import random
from datetime import datetime
from decimal import Decimal
from typing import Sequence, Annotated

from aiohttp import ClientSession
from fastapi import FastAPI, APIRouter, Request, Depends, HTTPException, Body
from redis.asyncio import Redis
from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from seleniumrequests import Firefox

from app.providers import get_publisher
from app.services.driver import presence_of_any_text_in_element
from app.services.queue.publisher import BasicMessageSender
from app.services.validators import validate_game_pass_url
from app.web.consts import MIN_ROBUXES
from app.web.interfaces import ITokenRepository, ITransactionsRepo
from app.web.logger import get_logger
from app.web.models import TransactionEntity, Bonuses
from app.web.provider import token_repo_provider, get_redis, client_provider, requests_driver_provider, \
	transaction_repo_provider, get_token, bot_token_repo_provider, bonuses_repo_provider
from app.web.repos import BotTokenRepository, BonusesRepository
from app.web.schemas import GamePassInfo, PlayerData, GameInfo, BuyRobuxScheme, TransactionScheme, \
	RobuxBuyServiceScheme, BuyRobuxesThroghUrl, BotTokenResponse, BotUpdatedRequest, BotTokenAddRequest, \
	AddBonusRequest, bonus_rewards, FRIEND_ADDED_BONUS, RobuxAmountResponse, ROBUX_TO_RUBLES_COURSE, WithdrawlResponse, \
	BonusesResponse, SelectBotRequest


# невроятный говнокод


def load_routes(app: FastAPI):
	app.include_router(router)


logger = get_logger()
router = APIRouter(prefix="/api")


def form_games_batch_request(game_ids: list[int]) -> list[dict]:
	result = []
	for id in game_ids:
		result.append({
			"requestId": f"{id}::GameThumbnail:768x432:webp:regular",
			"format": "webp",
			"size": "768x432",
			"targetId": id,
			"token": "",
			"type": "GameThumbnail",
		})
	return result


def form_users_batch_request(users: list[dict]) -> list[dict]:
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
	driver_requests: Firefox = Depends(requests_driver_provider),
	client: ClientSession = Depends(client_provider)
) -> list[PlayerData] | None:
	result = await redis.get(f"players_{player_name}")

	if result:
		logger.info("Found from redis cache")
		result = json.loads(result)
		return [PlayerData(**v) for v in result]

	logger.info("Sending 'search user' request to roblox api")
	response = driver_requests.request("GET", f"https://users.roblox.com/v1/users/search?keyword={player_name}&limit=10")
	if response.status_code == 429:
		logger.error("No search user response")
		await asyncio.sleep(5.0)
		response = driver_requests.request("GET", f"https://users.roblox.com/v1/users/search?keyword={player_name}&limit=10")
	_data = response.json()
	logger.info(str(_data)[0:200])
	users = _data["data"]

	batch_response = await client.post("https://thumbnails.roblox.com/v1/batch", json=form_users_batch_request(users))
	if batch_response.status == 429:
		logger.error("No batch response")
		raise HTTPException(detail="Rate limit exceeded", status_code=429)
	_data = await batch_response.json()
	data = form_users_response(users, _data["data"])

	logger.info(f"lset is placed in players_{player_name}")
	await redis.set(f"players_{player_name}", json.dumps([x.dict() for x in data]))
	await redis.expire(f"players_{player_name}", 3600)

	return data


@router.get("/search/{game_id}/gamepass")
async def search_gamepass_by_id(
	game_id: int,
	redis: Redis = Depends(get_redis),
	client: ClientSession = Depends(client_provider)
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


@router.get("/search/games")
async def search_game(
	player_id: int,
	redis: Redis = Depends(get_redis),
	client: ClientSession = Depends(client_provider)
) -> list[GameInfo]:
	player_games = await redis.get(f"player_game_{player_id}")

	if player_games:
		logger.info("Found games from redis cache")
		result = json.loads(player_games)
		return [GameInfo(**v) for v in result]
	response = await client.get(f"https://games.roblox.com/v2/users/{player_id}/games")
	if response.status == 429:
		logger.warning("Rate limit reached")
		return []
	data: list[dict] = (await response.json())['data']
	game_ids = [x['rootPlace']['id'] for x in data]
	response = await client.post("https://thumbnails.roblox.com/v1/batch", json=form_games_batch_request(game_ids))
	if response.status == 400 or response.status == 429:
		logger.warning("Rate limit reached")
		return []
	batch_data: list[dict] = (await response.json())['data']

	player_games = []

	logger.info(batch_data)
	for image, game in zip(batch_data, data):
		player_games.append(
			GameInfo(
				name=game['name'],
				id=game['rootPlace']['id'],
				icon_url=image['imageUrl'],
			)
		)

	logger.info(f"Lset to player_game_{player_id}")
	logger.info(f"Player games: {player_games}")
	await redis.set(f"player_game_{player_id}", json.dumps([x.dict() for x in player_games]))
	await redis.expire(f"player_game_{player_id}", 360)

	return player_games


@router.post("/buy_robux", response_model=TransactionScheme)
async def buy_robux(
	data: BuyRobuxScheme,
	redis: Redis = Depends(get_redis),
	client: ClientSession = Depends(client_provider),
	publisher: BasicMessageSender = Depends(get_publisher),
	transaction_repo: ITransactionsRepo = Depends(transaction_repo_provider),
	requests_driver: Firefox = Depends(requests_driver_provider),
	bonuses_repo: BonusesRepository = Depends(bonuses_repo_provider),
) -> TransactionScheme | None:
	ok = await redis.get(f"withdrawl_{data.bonus_withdrawal_id}")
	if data.robux_amount <= MIN_ROBUXES and not ok:
		raise HTTPException(detail="Need to be highed, and has to have withdrawl id", status_code=400)

	logger.info(f"SEarching in place: {data.game_id}")
	universe_response = await client.get(f"https://apis.roblox.com/universes/v1/places/{data.game_id}/universe")
	if universe_response.status == 429:
		logger.error("No universe response")
		raise HTTPException(detail="No unvierse response", status_code=429)

	_data = await universe_response.json()

	logger.info(f"Universe find... {_data}")

	universe_id = _data["universeId"]
	response = await client.get(
		f"https://games.roblox.com/v1/games/{universe_id}/game-passes?limit=100&sortOrder=1")

	if response.status == 429:
		logger.error("No gamepass response")
		raise HTTPException(detail="Rate limit for gamepasses", status_code=429)

	json_response = await response.json()

	logger.info(f"Raw response: {json_response}")
	_temp: list[dict] = json_response['data']
	gamepasses = [GamePassInfo(**v) for v in _temp]

	logger.info(f"Lset to game_{data.game_id}")
	logger.info(f'Gamepasses: {_temp}')

	real_gamepass_price = round(int(data.robux_amount) * 1.429)
	logger.info(f"Real gamepass price: {real_gamepass_price}, gamepasses of user: {gamepasses}")
	found_gamepass: GamePassInfo | None = None
	for game_pass in gamepasses:
		if game_pass.price == real_gamepass_price and game_pass.sellerName == data.roblox_username:
			found_gamepass = game_pass

	if not found_gamepass:
		raise HTTPException(detail="Not found gamepasses with that amount", status_code=402)

	message = RobuxBuyServiceScheme(
			url=f"https://www.roblox.com/game-pass/{found_gamepass.id}/",
			tx_id=1,
			price=real_gamepass_price,
		)

	try:
		WebDriverWait(requests_driver, 3).until(
			presence_of_any_text_in_element((By.CSS_SELECTOR, ".inventory-button"))
		)
	except TimeoutException:
		pass
	else:
		raise HTTPException(detail="Gamepass is already bought, create new one", status_code=409)

	entity = TransactionEntity(
		amount=data.paid_amount,
		robux_amount=real_gamepass_price,
		game_id=data.game_id,
		gamepass_id=found_gamepass.id,
		email=data.email,
		roblox_username=data.roblox_username,
	)

	await transaction_repo.add_transaction(entity)

	logger.info(f"Sending transaction!!!!!, found gamepass: {found_gamepass}")
	logger.info(f"Message to bot service: {message}")
	publisher.send_message(message.dict())
	logger.info("WAITING")

	tx = TransactionScheme(
		id=entity.id,
		roblox_name=entity.roblox_username,
		robux_amount=real_gamepass_price,
		paid_amount=entity.amount,
		successful=False,
		coupon_activated=False,
	)

	if data.bonus_username:
		bonus = await bonuses_repo.get_bonus_by_username(data.bonus_username)
		if not bonus:
			return tx
		tx.coupon_activated = True
		bonus.bonus += FRIEND_ADDED_BONUS

		await bonuses_repo.update_bonus(roblox_username=data.bonus_username, bonus=bonus.bonus)

	return tx


@router.post("/buy_robux/check")
async def buy_robux_check(
	data: BuyRobuxScheme,
	client: ClientSession = Depends(client_provider),
	requests_driver: Firefox = Depends(requests_driver_provider)
) -> bool:

	logger.info(f"SEarching in place: {data.game_id}")
	universe_response = await client.get(f"https://apis.roblox.com/universes/v1/places/{data.game_id}/universe")
	if universe_response.status == 429:
		logger.error("No universe response")
		raise HTTPException(detail="No unvierse response", status_code=429)

	_data = await universe_response.json()

	logger.info(f"Universe find... {_data}")

	universe_id = _data["universeId"]
	response = await client.get(
		f"https://games.roblox.com/v1/games/{universe_id}/game-passes?limit=100&sortOrder=1")

	if response.status == 429:
		logger.error("No gamepass response")
		raise HTTPException(detail="Rate limit for gamepasses", status_code=429)

	json_response = await response.json()

	logger.info(f"Raw response: {json_response}")
	_temp: list[dict] = json_response['data']
	gamepasses = [GamePassInfo(**v) for v in _temp]

	logger.info(f'Gamepasses: {_temp}')

	real_gamepass_price = round(int(data.robux_amount) * 1.429)
	logger.info(f"Real gamepass price: {real_gamepass_price}, gamepasses of user: {gamepasses}")
	found_gamepass: GamePassInfo | None = None
	for game_pass in gamepasses:
		if game_pass.price == real_gamepass_price and game_pass.sellerName == data.roblox_username:
			found_gamepass = game_pass

	if not found_gamepass:
		raise HTTPException(detail="Not found gamepasses with that amount", status_code=402)

	requests_driver.get(f"https://www.roblox.com/game-pass/{found_gamepass.id}/")
	logger.info(f"Redirecting bot to link: https://www.roblox.com/game-pass/{found_gamepass.id}/")
	try:
		WebDriverWait(requests_driver, 3).until(
			presence_of_any_text_in_element((By.CSS_SELECTOR, ".inventory-button"))
		)
	except TimeoutException:
		logger.info("Oh yes!!")
		return True

	return False


@router.get("/robux_amount_and_course")
async def robux_amount(
	redis: Redis = Depends(get_redis),
	driver_requests: Firefox = Depends(requests_driver_provider),
) -> RobuxAmountResponse:
	logger.info('Getting player id')
	_temp = driver_requests.find_element(By.CSS_SELECTOR, "a.text-link.dynamic-overflow-container")
	link = _temp.get_attribute("href")
	parts = link.split("/")
	logger.info(f"Parts: {parts}")
	user_id = bytes(parts[4], 'utf8')
	key = f"bot_current_amount_{user_id}"
	response = await redis.get(key)
	if response:
		return RobuxAmountResponse(instock=int(response), course=ROBUX_TO_RUBLES_COURSE)

	url = f"https://economy.roblox.com/v1/users/{user_id.decode('utf8')}/currency"

	logger.info(f"Sending request, url: {url}")
	response = driver_requests.request("GET", url)
	logger.info(f"Response of currency getter: {response.text}")
	if response.status_code != 200:
		raise HTTPException(detail="Cannot get robux amount", status_code=response.status_code)
	robux = response.json()['robux']
	logger.info(f"Robux amount: {robux}")

	await redis.set(key, robux)
	await redis.expire(key, 360)

	return RobuxAmountResponse(instock=robux, course=ROBUX_TO_RUBLES_COURSE)


@router.post("/buy_robux/url")
async def buy_robux_by_url(
	data: BuyRobuxesThroghUrl,
	publisher: BasicMessageSender = Depends(get_publisher)
) -> TransactionScheme | None:
	if not validate_game_pass_url(data.url):
		raise HTTPException(status_code=400, detail="Не правильный url")
	logger.info("Sending transaction!!!!!")
	publisher.send_message(
		RobuxBuyServiceScheme(
			url=data.url,
			tx_id=1,
			price=data.amount,
		).dict()
	)
	logger.info("WAITING")
	return TransactionScheme(
		id=random.randint(0, 10) + random.randint(0, 100),
		roblox_name=data.roblox_username,
		robux_amount=data.amount,
		paid_amount=Decimal(data.amount * 0.7),
	)


START_PREFIX = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items"


@router.get("/bot")
async def get_bots(
	token: str = Depends(get_token),
	token_repo: BotTokenRepository = Depends(bot_token_repo_provider),
) -> Sequence[BotTokenResponse]:
	results = await token_repo.get_all()

	return [BotTokenResponse.from_orm(obj) for obj in results]


@router.patch("/bot")
async def update_bot(
	bot_update_form: BotUpdatedRequest,
	token: str = Depends(get_token),
	token_repo: BotTokenRepository = Depends(bot_token_repo_provider),
) -> BotTokenResponse | None:
	if val := await token_repo.get_by_token(bot_update_form.token):
		if val.token == bot_update_form.token:
			raise HTTPException(detail="You gave same token!!", status_code=409)
	if not bot_update_form.token.startswith(START_PREFIX):
		raise HTTPException(detail="Start prefix is incorrect", status_code=400)
	result = await token_repo.update(
		bot_token_id=bot_update_form.id,
		roblox_name=bot_update_form.roblox_name,
		token=bot_update_form.token,
		is_active=True,
	)
	return BotTokenResponse.from_orm(result)


@router.delete("/bot/{bot_id}")
async def delete_bot(
	bot_id: int,
	token: str = Depends(get_token),
	token_repo: BotTokenRepository = Depends(bot_token_repo_provider),
) -> bool:
	ok = await token_repo.delete(bot_id)

	return ok


@router.post("/bot")
async def create_bot(
	body: BotTokenAddRequest,
	token: str = Depends(get_token),
	token_repo: BotTokenRepository = Depends(bot_token_repo_provider),
) -> BotTokenResponse:
	if not body.token.startswith(START_PREFIX):
		raise HTTPException(detail="Start prefix is incorrect", status_code=400)
	if await token_repo.get_by_token(body.token):
		raise HTTPException(detail="Conflict", status_code=409)

	result = await token_repo.create(
		roblox_name=body.roblox_name,
		token=body.token,
	)

	return BotTokenResponse.from_orm(result)


@router.post("/bot/select")
async def select_bot(
	body: SelectBotRequest,
	token: str = Depends(get_token),
	token_repo: BotTokenRepository = Depends(bot_token_repo_provider),
) -> BotTokenResponse:
	bot_token, err = await token_repo.select_bot(body.bot_id)
	if err:
		raise HTTPException(status_code=400, detail=err)
	return BotTokenResponse.from_orm(bot_token)


@router.post("/auth/token")
async def verify_token(
		token: str,
		token_repo: Annotated[ITokenRepository, Depends(token_repo_provider)] = None
) -> bool:
	token = await get_token(token, token_repo)
	return bool(token)


@router.get("/bonuses/{player_name}")
async def bonuses(
	player_name: str,
	bonuses_repo: BonusesRepository = Depends(bonuses_repo_provider),
) -> BonusesResponse:
	result = await bonuses_repo.get_bonus_by_username(player_name)
	if not result:
		result = await bonuses_repo.create_bonus(roblox_username=player_name)
	return BonusesResponse.from_orm(result)


@router.post("/bonuse/add")
async def add_bonus(
	body: AddBonusRequest,
	bonuses_repo: BonusesRepository = Depends(bonuses_repo_provider),
) -> BonusesResponse:
	bonus = await bonuses_repo.get_bonus_by_username(body.player_name)
	if not bonus:
		bonus = await bonuses_repo.create_bonus(roblox_username=body.player_name)
	tasks: list[str] = json.loads(bonus.completed_tasks)

	if body.type.value in tasks:
		raise HTTPException(status_code=400, detail="Вы уже выполнили это задание")
	tasks.append(body.type.value)
	bonus.tasks = tasks
	bonus.bonus += bonus_rewards[body.type.value]

	await bonuses_repo.update_bonus(body.player_name, bonus.bonus, tasks)

	return BonusesResponse.from_orm(bonus)


@router.post("/activate_coupon")
async def activate_coupon(
	player_name: str,
	bonuses_repo: BonusesRepository = Depends(bonuses_repo_provider),
) -> BonusesResponse:
	bonus = await bonuses_repo.get_bonus_by_username(player_name)
	if not bonus:
		bonus = await bonuses_repo.create_bonus(roblox_username=player_name)
	return BonusesResponse.from_orm(bonus)


@router.post("/activate_bonus_withdraw")
async def activate_bonus_withdraw(redis: Redis = Depends(get_redis)) -> WithdrawlResponse:
	withdraw_id = random.randint(0, 100000)
	await redis.set(f"withdrawl_{withdraw_id}", 'true')
	await redis.expire(f"withdrawl_{withdraw_id}", 3600)

	return WithdrawlResponse(withdraw_id=withdraw_id)


_start_time = datetime.now()


@router.get("/heartbeat")
async def heartbeat():
	return {"uptime": datetime.now() - _start_time, "ok": True}
