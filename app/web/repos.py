import uuid
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.web.interfaces import ITokenRepository, ITransactionsRepo
from app.web.models import Token, TransactionEntity


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


class TransactionRepository(ITransactionsRepo):
	def __init__(self, db: AsyncSession):
		self.db = db

	async def add_transaction(self, entity: TransactionEntity) -> UUID:
		self.db.add(entity)
		await self.db.commit()
		return entity.id

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
