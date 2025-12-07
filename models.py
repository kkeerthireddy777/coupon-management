from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date


class Eligibility(BaseModel):
    # User based
    allowedUserTiers: Optional[List[str]] = None
    minLifetimeSpend: Optional[float] = None
    minOrdersPlaced: Optional[int] = None
    firstOrderOnly: Optional[bool] = None
    allowedCountries: Optional[List[str]] = None

    # Cart based
    minCartValue: Optional[float] = None
    applicableCategories: Optional[List[str]] = None
    excludedCategories: Optional[List[str]] = None
    minItemsCount: Optional[int] = None


class Coupon(BaseModel):
    code: str
    description: str
    discountType: str  # "FLAT" or "PERCENT"
    discountValue: float
    maxDiscountAmount: Optional[float] = None

    startDate: date
    endDate: date

    usageLimitPerUser: Optional[int] = None
    eligibility: Eligibility = Field(default_factory=Eligibility)


class UserContext(BaseModel):
    userId: str
    userTier: str  # e.g. NEW, REGULAR, GOLD
    country: str
    lifetimeSpend: float
    ordersPlaced: int


class CartItem(BaseModel):
    productId: str
    category: str
    unitPrice: float
    quantity: int


class Cart(BaseModel):
    items: List[CartItem]


class BestCouponRequest(BaseModel):
    user: UserContext
    cart: Cart


class BestCouponResponse(BaseModel):
    coupon: Optional[Coupon]
    discountAmount: float