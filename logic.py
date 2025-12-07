from datetime import date
from typing import List, Optional, Tuple
from .models import Coupon, UserContext, Cart, CartItem, Eligibility
from .storage import USAGE_PER_USER


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
    if coupon.discountType.upper() == "FLAT":
        discount = coupon.discountValue
    elif coupon.discountType.upper() == "PERCENT":
        discount = cart_value * (coupon.discountValue / 100.0)
        if coupon.maxDiscountAmount is not None:
            discount = min(discount, coupon.maxDiscountAmount)
    else:
        discount = 0.0
    # discount cannot exceed cart value
    return max(0.0, min(discount, cart_value))


def pick_best_coupon(coupons: List[Tuple[Coupon, float]]) -> Optional[Tuple[Coupon, float]]:
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
            -cd[1],                 # highest discount first
            cd[0].endDate,          # earliest endDate
            cd[0].code              # lexicographically smaller code
        )
    )
    return coupons[0]


def increment_usage(coupon: Coupon, user: UserContext) -> None:
    key = (user.userId, coupon.code)
    USAGE_PER_USER[key] = USAGE_PER_USER.get(key, 0) + 1