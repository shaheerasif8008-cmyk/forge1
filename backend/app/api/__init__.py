from fastapi import APIRouter
import logging

from .admin_flags import router as admin_flags_router
from .admin_promotion import router as admin_promotion_router
from .admin_release import router as admin_release_router
from .ai import router as ai_router
from .auth import router as auth_router
from .auth_v2 import router as auth_v2_router
from .admin_auth import router as admin_auth_router
from .beta import router as beta_router
from .metrics import router as metrics_api_router
from .logs import router as logs_router
from .metrics_active import router as metrics_active_router
from .admin_keys import router as admin_keys_router, router_admin_employees as admin_employees_keys_router
from .admin_escalations import router as admin_escalations_router
from .beta_metrics import router as metrics_router
from .employees import router as employees_router
from .employees_invoke import router as employees_invoke_router
from .employees_export import router as employees_export_router
from .health import router as health_router
from .admin_insights import router as admin_insights_router
from .admin_users import router as admin_users_router
from .admin_ai_comms import router as admin_ai_comms_router
from .ai_comms_client import router as ai_comms_client_router
from .marketplace import router as marketplace_router
from .admin_tools import router as admin_tools_router
from .pipelines import router as pipelines_router
from .metrics_client import router as client_metrics_router
from .branding import router as branding_router
from .escalations_client import router as client_escalations_router
from .sandbox import router as sandbox_router
from .error_inspector import router as admin_errors_router
from .rag_v2 import router as rag_v2_router
from .control_plane import router as control_plane_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(auth_v2_router)
api_router.include_router(health_router)
api_router.include_router(employees_router)
api_router.include_router(ai_router)
api_router.include_router(admin_flags_router)
api_router.include_router(admin_release_router)
api_router.include_router(admin_promotion_router)
api_router.include_router(metrics_router)
api_router.include_router(beta_router)
api_router.include_router(metrics_api_router)
api_router.include_router(logs_router)
api_router.include_router(metrics_active_router)
api_router.include_router(admin_keys_router)
api_router.include_router(admin_escalations_router)
api_router.include_router(employees_invoke_router)
api_router.include_router(employees_export_router)
api_router.include_router(admin_employees_keys_router)
api_router.include_router(admin_insights_router)
api_router.include_router(admin_users_router)
api_router.include_router(admin_auth_router)
api_router.include_router(admin_ai_comms_router)
api_router.include_router(ai_comms_client_router)
api_router.include_router(marketplace_router)
api_router.include_router(admin_tools_router)
api_router.include_router(pipelines_router)
api_router.include_router(client_metrics_router)
api_router.include_router(branding_router)
api_router.include_router(client_escalations_router)
api_router.include_router(sandbox_router)
api_router.include_router(admin_errors_router)
api_router.include_router(rag_v2_router)
api_router.include_router(control_plane_router)

logging.getLogger(__name__).info("API routers registered")
