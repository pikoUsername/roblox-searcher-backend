from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar, Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

from app.web.models import TransactionStatus

TData = TypeVar("TData")


@dataclass(frozen=True)
class ErrorResult(GenericModel, Generic[TData]):
    message: str
    data: TData


class BonusType(Enum):
    telegram = "tg"
    vk = "vk"
    discord = "ds"
    trust_pilot = "review"
    vk_reviews = "vk_reviews"
    ds_reviews = "ds_reviews"


bonus_rewards: dict[str, int] = {
    BonusType.telegram.value: 5,
    BonusType.vk.value: 5,
    BonusType.discord.value: 5,
    BonusType.trust_pilot.value: 10,
    BonusType.vk_reviews.value: 5,
    BonusType.ds_reviews.value: 5,
}


FRIEND_ADDED_BONUS = 20
ROBUX_TO_RUBLES_COURSE = 0.7


class BasicModel(BaseModel):
    class Config:
        orm_mode = True


class BuyGamePassScheme(BasicModel):
    user_id: int


class RobuxAmountResponse(BasicModel):
    course: float
    instock: int


class PlayerData(BasicModel):
    avatar_url: str
    name: str
    display_name: str
    user_id: int


class GamePassInfo(BasicModel):
    id: int
    name: str
    displayName: str
    productId: Optional[int] = None
    price: Optional[float] = None
    sellerName: str
    sellerId: Optional[int] = None
    isOwned: bool


class GameInfo(BasicModel):
    id: int
    name: str
    icon_url: str


class ActivteCouponRequest(BasicModel):
    player_name: str


class ActivateBonusWithdrawRequest(BasicModel):
    roblox_name: str


class BuyRobuxScheme(BasicModel):
    game_id: int
    robux_amount: int
    paid_amount: Decimal
    roblox_username: str
    email: str | None
    bonus_username: str | None
    bonus_withdrawal_id: int | None


class WithdrawlResponse(BasicModel):
    withdraw_id: int


class BonusesResponse(BasicModel):
    roblox_name: str
    bonus: int = 0
    activated_for: str | None = Field(default=None)
    completed_tasks: str = Field(default="[]")


class BotUpdatedRequest(BasicModel):
    id: int
    roblox_name: str | None
    token: str


class BotTokenResponse(BasicModel):
    id: int
    roblox_name: str
    is_active: bool = True
    is_selected: bool = False


class SelectBotRequest(BasicModel):
    bot_id: int


class BotTokenAddRequest(BasicModel):
    roblox_name: str
    token: str


class AddBonusRequest(BasicModel):
    player_name: str
    type: BonusType


class TransactionScheme(BasicModel):
    id: UUID
    roblox_name: str
    robux_amount: int
    paid_amount: Decimal
    successful: bool = False
    completed: bool = False
    coupon_activated: bool = False


class TransactionResponseScheme(BasicModel):
    amount: Decimal
    robux_amount: Decimal
    game_id: int
    gamepass_id: int
    email: str | None = None
    status: str = Field(default=TransactionStatus.pending.value)
    roblox_username: str
    created_at: datetime | None


class RobuxBuyServiceScheme(BasicModel):
    """{"url": "https://www.roblox.com/game-pass/153455721/Husband", "price": 10, "tx_id": 2}"""
    url: str
    price: int
    tx_id: int


class BuyRobuxesThroghUrl(BasicModel):
    url: str
    amount: int
    roblox_username: str
