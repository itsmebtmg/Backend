from fastapi import APIRouter

from app.api.v1.admin.auth import router as admin_auth_router
from app.api.v1.admin.metrics import router as admin_metrics_router
from app.api.v1.admin.orders import router as admin_orders_router
from app.api.v1.health import router as health_router
from app.api.v1.orders import router as orders_router
from app.api.v1.tracking import router as tracking_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(health_router)
api_router.include_router(orders_router)
api_router.include_router(tracking_router)

admin_router = APIRouter(prefix="/admin")
admin_router.include_router(admin_auth_router)
admin_router.include_router(admin_metrics_router)
admin_router.include_router(admin_orders_router)
api_router.include_router(admin_router)
