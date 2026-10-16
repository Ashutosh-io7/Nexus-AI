from fastapi import APIRouter
from app.api.v1.endpoints import churn, customers, playbook

api_router = APIRouter()
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(churn.router, prefix="/churn", tags=["churn"])
api_router.include_router(playbook.router, prefix="/playbook", tags=["playbook"])