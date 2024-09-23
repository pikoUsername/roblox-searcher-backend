import uuid
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.web.interfaces import ITokenRepository
from app.web.models import Token


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
