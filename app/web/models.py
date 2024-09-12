import uuid
from datetime import datetime
from enum import Enum
from typing import Sequence

from attr import define, field
from sqlalchemy import Column, DateTime, func, Table, String, ForeignKey, Boolean, Integer, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import registry, relationship


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


def load_models(reg: registry):
	token_model = Table(
		'tokens',
		reg.metadata,
		*IdEntity.mapper_args(),
		Column("expires_at", DateTime, nullable=False)
	)

	reg.map_imperatively(
		Token,
		token_model,
	)

