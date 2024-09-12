from dataclasses import dataclass
from typing import Generic, TypeVar, Optional

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
