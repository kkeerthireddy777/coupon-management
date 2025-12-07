# Coupon Management

A simple HTTP service that manages coupons and returns the best applicable coupon
for a given user and cart, based on eligibility rules and discount logic.



## Tech Stack
- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic



## Project Overview
This service allows:
- Creating coupons with various eligibility rules
- Evaluating all available coupons for a given user and cart
- Selecting the best coupon deterministically based on discount and expiry rules

Data is stored in-memory for simplicity, as required by the assignment.



## APIs Implemented

- `POST /coupons` – Create a new coupon
- `GET /coupons` – List all coupons (for testing/debugging)
- `POST /best-coupon` – Get the best applicable coupon for a user and cart
- `GET /health` – Health check endpoint



## How to Run

### Prerequisites
- Python 3.10 or higher
- pip

### Setup & Run
```bash
pip install -r requirements.txt
python main.py

