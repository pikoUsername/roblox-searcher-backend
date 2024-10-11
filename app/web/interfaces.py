import abc
from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from typing import Sequence, Optional
from uuid import UUID

from app.web.models import TransactionStatus, Token, TransactionEntity


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


class ITransactionsRepo(ABC):
	@abstractmethod
	async def add_transaction(self, entity: TransactionEntity) -> UUID:
		pass

	@abstractmethod
	async def get_transactions(self, roblox_name: str | None) -> Sequence[TransactionEntity]:
		pass

	@abstractmethod
	async def get_transaction(self, transaction_id: UUID) -> Optional[TransactionEntity]:
		pass

	@abstractmethod
	async def delete_transaction(self, transaction_id: UUID) -> bool:
		pass

	@abstractmethod
	async def update_transaction(self, entity: TransactionEntity) -> bool:
		pass
