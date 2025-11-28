"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import transactions

api_router = APIRouter()

# Include all v1 routers
api_router.include_router(transactions.router)
