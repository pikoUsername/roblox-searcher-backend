import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Sequence, Tuple
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.web.interfaces import ITokenRepository, ITransactionsRepo
from app.web.models import Token, TransactionEntity, BotToken, Bonuses


class TokenRepository(ITokenRepository):
	def __init__(self, db: AsyncSession):
		self.db = db

	async def create_token(self, expiry_minutes: int) -> UUID:
		token_id = uuid.uuid4()
		expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
		token = Token(id=token_id, expires_at=expires_at)
		self.db.add(token)
		await self.db.commit()
		return token_id

	async def validate_token(self, token_id: str) -> bool:
		token = await self.db.get(Token, token_id)
		if token and datetime.utcnow() < token.expires_at:
			return True
		elif token:
			await self.db.delete(token)
			await self.db.commit()
		return False

	async def revoke_token(self, token_id: str) -> bool:
		token = self.db.get(Token, token_id)
		if token:
			await self.db.delete(token)
			await self.db.commit()
			return True
		return False

	async def get_token(self, token_id: str) -> Token | None:
		token = await self.db.get(Token, token_id)
		return token


class BotTokenRepository:
	def __init__(self, db: AsyncSession):
		self.db = db

	async def create(self, roblox_name: str, token: str, is_active: bool = True) -> BotToken:
		new_bot_token = BotToken(roblox_name=roblox_name, token=token.replace(" ", ""), is_active=is_active)
		self.db.add(new_bot_token)
		await self.db.commit()
		await self.db.refresh(new_bot_token)
		return new_bot_token

	async def get(self, bot_token_id: int) -> Optional[BotToken]:
		stmt = select(BotToken).where(BotToken.id == bot_token_id)
		result = await self.db.execute(stmt)
		return result.scalars().one_or_none()

	async def get_by_token(self, token: str) -> Optional[BotToken]:
		stmt = select(BotToken).where(BotToken.token == token)
		result = await self.db.execute(stmt)
		return result.scalars().one_or_none()

	async def get_all(self) -> Sequence[BotToken]:
		stmt = select(BotToken)
		result = await self.db.execute(stmt)
		return result.scalars().all()

	async def update(self, bot_token_id: int, roblox_name: Optional[str] = None, token: Optional[str] = None,
	                 is_active: Optional[bool] = None) -> Optional[BotToken]:
		bot_token = await self.get(bot_token_id)
		if not bot_token:
			return None

		if roblox_name is not None:
			bot_token.roblox_name = roblox_name
		if token is not None:
			bot_token.token = token.replace(" ", "")
		if is_active is not None:
			bot_token.is_active = is_active

		await self.db.commit()
		await self.db.refresh(bot_token)
		return bot_token

	async def delete(self, bot_token_id: int) -> bool:
		bot_token = await self.get(bot_token_id)
		if not bot_token:
			return False

		await self.db.delete(bot_token)
		await self.db.commit()
		return True

	async def select_bot(self, bot_token_id: int) -> Tuple[BotToken | None, str | None]:
		bot_token = await self.get(bot_token_id)
		if not bot_token:
			return None, "No bot token"
		if not bot_token.is_active:
			return None, "bot token is not active"
		bot_token.is_selected = True
		await self.db.commit()
		await self.db.refresh(bot_token)

		return bot_token, None


class BonusesRepository:
	def __init__(self, session: AsyncSession):
		self.session = session

	async def create_bonus(self, roblox_username: str, bonus: int = 0, activated_for: str = None) -> Bonuses:
		new_bonus = Bonuses(roblox_name=roblox_username, bonus=bonus, activated_for=activated_for)
		self.session.add(new_bonus)
		await self.session.commit()
		return new_bonus

	async def get_bonus_by_username(self, roblox_username: str) -> Bonuses:
		result = await self.session.execute(select(Bonuses).where(Bonuses.roblox_name == roblox_username))
		return result.scalars().first()

	async def update_bonus(self, roblox_username: str, bonus: int, completed_tasks: list[str] = None, activated_for: str = None) -> Bonuses:
		bonus_record = await self.get_bonus_by_username(roblox_username)
		if bonus_record:
			bonus_record.bonus = bonus
			if not completed_tasks:
				completed_tasks = []
			bonus_record.completed_tasks = json.dumps(completed_tasks)
			bonus_record.activated_for = activated_for
			await self.session.commit()
		return bonus_record

	async def delete_bonus(self, roblox_username: str) -> None:
		bonus_record = await self.get_bonus_by_username(roblox_username)
		if bonus_record:
			await self.session.delete(bonus_record)
			await self.session.commit()


class TransactionRepository(ITransactionsRepo):
	def __init__(self, db: AsyncSession):
		self.db = db

	async def add_transaction(self, entity: TransactionEntity) -> UUID:
		self.db.add(entity)
		await self.db.commit()
		return entity.id

	async def get_transactions(self, roblox_name: str) -> Sequence[TransactionEntity]:
		stmt = select(TransactionEntity).where(TransactionEntity.roblox_username == roblox_name)
		result = await self.db.execute(stmt)

		return result.scalars().unique().all()

	async def get_transaction(self, transaction_id: UUID) -> Optional[TransactionEntity]:
		# Получаем транзакцию по ID
		transaction = await self.db.get(TransactionEntity, transaction_id)
		return transaction

	async def delete_transaction(self, transaction_id: UUID) -> bool:
		# Удаляем транзакцию по ID
		transaction = await self.db.get(TransactionEntity, transaction_id)
		if transaction:
			await self.db.delete(transaction)
			await self.db.commit()
			return True
		return False

	async def update_transaction(self, entity: TransactionEntity) -> bool:
		# Обновляем информацию о транзакции
		await self.db.merge(entity)
		return True
