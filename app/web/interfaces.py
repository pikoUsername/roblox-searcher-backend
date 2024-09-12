import abc
from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from typing import Sequence, Optional
from uuid import UUID

from app.web.models import TransactionStatus, Token


@dataclass
class FetchTransactionsQuery:
	status: TransactionStatus | None = field(default=None)
	transaction_id: UUID | None = field(default=None)
	by_players: list[str] | None = field(default=None)


class ITokenRepository(ABC):
	@abstractmethod
	async def create_token(self, expiry_minutes: int) -> UUID:
		pass

	@abstractmethod
	async def validate_token(self, token_id: UUID) -> bool:
		pass

	@abstractmethod
	async def revoke_token(self, token_id: UUID) -> bool:
		pass

	@abstractmethod
	async def get_token(self, token_id: UUID) -> Token:
		pass
