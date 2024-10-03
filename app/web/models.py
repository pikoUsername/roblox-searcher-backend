import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Sequence

from attr import define, field
from sqlalchemy import Column, DateTime, func, Table, String, Boolean, UUID, DECIMAL, BIGINT, Integer, JSON
from sqlalchemy.orm import registry


class TransactionStatus(Enum):
	completed = "completed"
	closed = "closed"
	pending = "pending"
	pending_to_resolve = "pending_to_resolve"


entity = define(kw_only=True, slots=False)


@entity
class IdEntity:
	id: UUID = field(factory=uuid.uuid4)
	created_at: datetime = field(factory=datetime.now)
	updated_at: datetime = field(factory=datetime.now)

	@staticmethod
	def mapper_args() -> Sequence[Column]:
		return [
			Column("id", UUID, primary_key=True, default=uuid.uuid4, index=True, nullable=False),
			Column("created_at", DateTime, server_default=func.now()),
			Column("updated_at", DateTime, onupdate=func.now(), nullable=True),
		]


@entity
class Token(IdEntity):
	expires_at: datetime
	is_active: bool = field(default=True)

	def is_valid(self):
		return datetime.utcnow() < self.expires_at

	@staticmethod
	def mapper_args() -> Sequence[Column]:
		return [
			Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True, nullable=False),
			Column("created_at", DateTime, server_default=func.now()),
			Column("updated_at", DateTime, onupdate=func.now(), nullable=True),
			Column("expires_at", DateTime, nullable=False),
		]


@entity
class TransactionEntity(IdEntity):
	amount: Decimal
	robux_amount: Decimal
	game_id: int
	gamepass_id: int
	email: str | None = field(default=None)
	status: TransactionStatus = field(default=TransactionStatus.pending.value)
	roblox_username: str

	@staticmethod
	def mapper_args() -> Sequence[Column]:
		return [
			*IdEntity.mapper_args(),  # Общие поля от IdEntity (id, created_at, updated_at)
			Column("amount", DECIMAL, nullable=False),  # Decimal для суммы транзакции
			Column("robux_amount", DECIMAL, nullable=False),  # Decimal для суммы в Robux
			Column("game_id", BIGINT, nullable=False),  # Идентификатор игры
			Column("gamepass_id", BIGINT, nullable=False),  # Идентификатор gamepass
			Column("email", String, nullable=True),  # Email, может быть пустым
			Column("status", String, nullable=False, default=TransactionStatus.pending.value),
			# Статус транзакции
			Column("roblox_username", String, nullable=False),  # Roblox имя пользователя
		]


@entity
class BotToken:
	id: int
	roblox_name: str
	token: str
	is_active: bool = True
	is_selected: bool = False

	@staticmethod
	def mapper_args() -> Sequence[Column]:
		return [
			Column("id", BIGINT, autoincrement=True, nullable=False, primary_key=True, index=True),
			Column("roblox_name", String(255), nullable=True),
			Column("token", String, nullable=False, unique=True),
			Column("is_active", Boolean, nullable=True, default=True, server_default="true"),
			Column("is_selected", Boolean, nullable=False, server_default="false", default=False)
		]


@entity
class Bonuses:
	roblox_name: str
	bonus: int = 0
	activated_for: str | None = field(default=None)
	completed_tasks: str = field(default="[]")

	@staticmethod
	def mapper_args() -> Sequence[Column]:
		return [
			Column("roblox_name", String(255), primary_key=True),
			Column("bonus", Integer, nullable=False, default=0, server_default="0"),
			Column("activated_for", String(255), nullable=True),
			Column("completed_tasks", JSON, server_default="'[]'")
		]


def load_models(reg: registry):
	token_model = Table(
		'tokens',
		reg.metadata,
		*Token.mapper_args(),
	)
	transaction_model = Table(
		'transactions',  # Название таблицы
		reg.metadata,
		*TransactionEntity.mapper_args()  # Используем статический метод для определения колонок
	)

	bot_transaction_model = Table(
		'user_tokens',
		reg.metadata,
		*BotToken.mapper_args(),
	)

	bonus_model = Table(
		'bonuses',
		reg.metadata,
		*Bonuses.mapper_args(),
	)

	reg.map_imperatively(
		Bonuses,
		bonus_model,
	)

	reg.map_imperatively(
		TransactionEntity,
		transaction_model,
	)

	reg.map_imperatively(
		BotToken,
		bot_transaction_model,
	)

	reg.map_imperatively(
		Token,
		token_model,
	)
