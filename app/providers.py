from fastapi import Depends
from loguru import logger

from app.settings import Settings, get_settings
from app.repos import UserTokenRepository
from app.services.interfaces import BasicDBConnector
from app.services.queue.publisher import BasicMessageSender


async def get_token_service(settings: Settings, connection: BasicDBConnector) -> UserTokenRepository:
	token_service = UserTokenRepository(connection, settings.db_tokens_table)

	await token_service.create_tokens_table()

	return token_service


def get_publisher():
	settings = get_settings()
	logger.info("Setting up basicMessageSender")

	publisher = BasicMessageSender(
		settings.queue_dsn,
		queue=settings.queue_name,
		exchange=settings.exchange_name,
		routing=settings.queue_name,
	)

	publisher.connect()
	logger.info("Connection to publisher has been established")

	return publisher
