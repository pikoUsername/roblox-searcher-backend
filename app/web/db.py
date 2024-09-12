from typing import Tuple

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import registry as registry_class


def get_db_session(dsn: str) -> Tuple[async_sessionmaker, registry_class]:
	engine = setup_engine(dsn)
	session = sa_session_factory(engine)

	return session, registry


def create_registry() -> registry_class:
	convention = {
		"ix": "ix_%(column_0_label)s",  # INDEX
		"uq": "uq_%(table_name)s_%(column_0_N_name)s",  # UNIQUE
		"ck": "ck_%(table_name)s_%(constraint_name)s",  # CHECK
		"fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",  # FOREIGN KEY
		"pk": "pk_%(table_name)s",  # PRIMARY KEY
	}

	mapper_registry = registry_class(
		metadata=MetaData(
			naming_convention=convention
		),
	)

	return mapper_registry


registry = create_registry()


def setup_engine(dsn: str, echo: bool = False) -> AsyncEngine:
	engine = create_async_engine(
		dsn,
		echo_pool=echo,
		pool_size=50,
	)
	return engine


def sa_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
	session = async_sessionmaker(bind=engine, expire_on_commit=False, autocommit=False, autoflush=False)
	return session
