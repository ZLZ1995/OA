from fastapi import APIRouter

from app.api.v1.archives import router as archives_router
from app.api.v1.auth import router as auth_router
from app.api.v1.finance import router as finance_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.files import router as files_router
from app.api.v1.health import router as health_router
from app.api.v1.print_room import router as print_room_router
from app.api.v1.project_members import router as project_members_router
from app.api.v1.projects import router as projects_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.report_versions import router as report_versions_router
from app.api.v1.roles import router as roles_router
from app.api.v1.users import router as users_router
from app.api.v1.work_orders import router as work_orders_router
from app.api.v1.workflow_logs import router as workflow_logs_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(projects_router)
api_router.include_router(project_members_router)
api_router.include_router(work_orders_router)
api_router.include_router(report_versions_router)
api_router.include_router(files_router)
api_router.include_router(reviews_router)
api_router.include_router(print_room_router)
api_router.include_router(finance_router)
api_router.include_router(archives_router)
api_router.include_router(workflow_logs_router)
api_router.include_router(dashboard_router)
