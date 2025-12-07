from typing import List, Optional, Dict, Tuple
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import date

# ---------------------------
# Data Models
# ---------------------------

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


# ---------------------------
# In-memory "storage"
# ---------------------------

# code -> Coupon
COUPONS_DB: Dict[str, Coupon] = {}

# (userId, couponCode) -> usageCount
USAGE_PER_USER: Dict[Tuple[str, str], int] = {}


# ---------------------------
# Business Logic Functions
# ---------------------------

def compute_cart_value(cart: Cart) -> float:
    return sum(item.unitPrice * item.quantity for item in cart.items)


def compute_items_count(cart: Cart) -> int:
    return sum(item.quantity for item in cart.items)


def get_cart_categories(cart: Cart) -> List[str]:
    return list({item.category for item in cart.items})


def is_within_date_range(coupon: Coupon, today: Optional[date] = None) -> bool:
    if today is None:
        today = date.today()
    return coupon.startDate <= today <= coupon.endDate


def has_remaining_usage(coupon: Coupon, user: UserContext) -> bool:
    if coupon.usageLimitPerUser is None:
        return True
    key = (user.userId, coupon.code)
    used = USAGE_PER_USER.get(key, 0)
    return used < coupon.usageLimitPerUser


def user_eligibility_ok(elig: Eligibility, user: UserContext, is_first_order: bool) -> bool:
    if elig.allowedUserTiers and user.userTier not in elig.allowedUserTiers:
        return False

    if elig.minLifetimeSpend is not None and user.lifetimeSpend < elig.minLifetimeSpend:
        return False

    if elig.minOrdersPlaced is not None and user.ordersPlaced < elig.minOrdersPlaced:
        return False

    if elig.firstOrderOnly and not is_first_order:
        return False

    if elig.allowedCountries and user.country not in elig.allowedCountries:
        return False

    return True


def cart_eligibility_ok(elig: Eligibility, cart: Cart) -> bool:
    cart_value = compute_cart_value(cart)
    if elig.minCartValue is not None and cart_value < elig.minCartValue:
        return False

    items_count = compute_items_count(cart)
    if elig.minItemsCount is not None and items_count < elig.minItemsCount:
        return False

    categories = get_cart_categories(cart)

    if elig.applicableCategories:
        # at least one item from these categories
        if not any(c in elig.applicableCategories for c in categories):
            return False

    if elig.excludedCategories:
        if any(c in elig.excludedCategories for c in categories):
            return False

    return True


def compute_discount(coupon: Coupon, cart_value: float) -> float:
    dtype = coupon.discountType.upper()
    if dtype == "FLAT":
        discount = coupon.discountValue
    elif dtype == "PERCENT":
        discount = cart_value * (coupon.discountValue / 100.0)
        if coupon.maxDiscountAmount is not None:
            discount = min(discount, coupon.maxDiscountAmount)
    else:
        discount = 0.0

    # discount cannot exceed cart value and cannot be negative
    return max(0.0, min(discount, cart_value))


def pick_best_coupon(coupons: List[tuple[Coupon, float]]) -> Optional[tuple[Coupon, float]]:
    """
    coupons: list of (coupon, discountAmount)
    Rule:
     1. Highest discount
     2. If tie, earliest endDate
     3. If still tie, lexicographically smaller code
    """
    if not coupons:
        return None

    coupons.sort(
        key=lambda cd: (
            -cd[1],           # highest discount first
            cd[0].endDate,    # earliest endDate
            cd[0].code        # lexicographically smaller code
        )
    )
    return coupons[0]


def increment_usage(coupon: Coupon, user: UserContext) -> None:
    key = (user.userId, coupon.code)
    USAGE_PER_USER[key] = USAGE_PER_USER.get(key, 0) + 1


# ---------------------------
# FastAPI App & Routes
# ---------------------------

app = FastAPI(title="Coupon Management Service")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/coupons", response_model=Coupon)
def create_coupon(coupon: Coupon):
    code_upper = coupon.code.upper()
    if code_upper in COUPONS_DB:
        # You can also choose to overwrite; here we reject.
        raise HTTPException(status_code=400, detail="Coupon code already exists")

    coupon.code = code_upper
    COUPONS_DB[code_upper] = coupon
    return coupon


@app.get("/coupons", response_model=List[Coupon])
def list_coupons():
    return list(COUPONS_DB.values())


@app.post("/best-coupon", response_model=BestCouponResponse)
def get_best_coupon(payload: BestCouponRequest):
    user: UserContext = payload.user
    cart: Cart = payload.cart

    cart_value = compute_cart_value(cart)
    today = date.today()

    # For this assignment, we treat "first order" as ordersPlaced == 0
    is_first_order = (user.ordersPlaced == 0)

    candidate_discounts: List[tuple[Coupon, float]] = []

    for coupon in COUPONS_DB.values():
        # 1. date validity
        if not is_within_date_range(coupon, today):
            continue

        # 2. usage limit per user
        if not has_remaining_usage(coupon, user):
            continue

        # 3. eligibility checks
        elig = coupon.eligibility
        if not user_eligibility_ok(elig, user, is_first_order):
            continue

        if not cart_eligibility_ok(elig, cart):
            continue

        # 4. compute discount
        discount = compute_discount(coupon, cart_value)
        if discount > 0:
            candidate_discounts.append((coupon, discount))

    best = pick_best_coupon(candidate_discounts)

    if best is None:
        return BestCouponResponse(coupon=None, discountAmount=0.0)

    best_coupon, best_discount = best

    # Optionally "consume" usage here
    increment_usage(best_coupon, user)

    return BestCouponResponse(coupon=best_coupon, discountAmount=best_discount)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,  # keep False to avoid Windows reload issues
    )