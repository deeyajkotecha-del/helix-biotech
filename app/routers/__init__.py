"""API routers."""
from app.routers.auth import router as auth_router
from app.routers.documents import router as documents_router
from app.routers.admin import router as admin_router
from app.routers.sources import router as sources_router
from app.routers.citations import router as citations_router
from app.routers.company import router as company_router
from app.routers.services import router as services_router

__all__ = ["auth_router", "documents_router", "admin_router", "sources_router", "citations_router", "company_router", "services_router"]
