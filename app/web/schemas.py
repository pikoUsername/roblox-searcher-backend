from dataclasses import dataclass
from typing import Generic, TypeVar, Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel
from pydantic.generics import GenericModel


TData = TypeVar("TData")


@dataclass(frozen=True)
class ErrorResult(GenericModel, Generic[TData]):
    message: str
    data: TData


class BuyGamePassScheme(BaseModel):
    user_id: int



class PlayerData(BaseModel):
    avatar_url: str
    name: str
    display_name: str
    user_id: int


class GamePassInfo(BaseModel):
    id: int
    name: str
    displayName: str
    productId: Optional[int] = None
    price: Optional[float] = None
    sellerName: str
    sellerId: Optional[int] = None
    isOwned: bool


class GameInfo(BaseModel):
    id: int
    name: str
    icon_url: str


class BuyRobuxScheme(BaseModel):
    game_id: int
    robux_amount: int
    paid_amount: Decimal
    roblox_username: str


class TransactionScheme(BaseModel):
    id: int
    roblox_name: str
    robux_amount: int
    paid_amount: Decimal
    successful: bool = False
    completed: bool = False


class RobuxBuyServiceScheme(BaseModel):
    """{"url": "https://www.roblox.com/game-pass/153455721/Husband", "price": 10, "tx_id": 2}"""
    url: str
    price: int
    tx_id: int


class BuyRobuxesThroghUrl(BaseModel):
    url: str
    amount: int
    roblox_username: str
