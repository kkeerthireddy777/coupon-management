from typing import Dict, Tuple
from .models import Coupon

# code -> Coupon
COUPONS_DB: Dict[str, Coupon] = {}

# (userId, couponCode) -> usageCount
USAGE_PER_USER: Dict[Tuple[str, str], int] = {}