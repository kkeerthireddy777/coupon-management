# Coupon Management

Simple HTTP service that manages coupons and returns the best applicable coupon for a given user and cart, based on eligibility rules and discount logic.

## Tech Stack

- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic

## How to Run

```bash
pip install -r requirements.txt
uvicorn main:app --reload
