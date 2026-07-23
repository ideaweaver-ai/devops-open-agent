from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.v1 import auth as auth_v1
from app.api.v1 import audit as audit_v1
from app.api.v1 import clusters as clusters_v1
from app.api.v1 import diagnose as diagnose_v1
from app.api.v1 import health as health_v1
from app.api.v1 import integrations as integrations_v1
from app.api.v1 import investigations as investigations_v1
from app.api.v1 import kubernetes_schedules as kubernetes_schedules_v1
from app.api.v1 import llm_usage as llm_usage_v1
from app.api.v1 import system as system_v1
from app.api.v1 import topology as topology_v1
from app.core.aws_env import sanitize_aws_environment
from app.core.config import get_settings
from app.core.errors import sanitize_error_message
from app.core.logging import setup_logging
from app.db.seed import seed_default_admin
from app.db.session import init_auth_db
from app.models.diagnosis import HealthResponse
from app.modules.aws.router import router as aws_v1
from app.modules.cloud_cost_detector.api.routes import router as cloud_cost_v1
from app.modules.performance.api.routes import router as performance_v1
from app.modules.pr_reviewer.api.routes import router as pr_reviewer_v1
from app.modules.security.api.routes import router as security_v1
from app.services.investigation_job_service import InvestigationJobService
from app.services.schedule_runner import schedule_runner
from app.storage.factory import get_audit_store, get_llm_usage_store, get_pr_review_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    sanitize_aws_environment()
    settings = get_settings()
    job_service = InvestigationJobService()
    await job_service.initialize()
    pr_review_store = get_pr_review_store()
    await pr_review_store.initialize()
    await get_llm_usage_store().initialize()
    await get_audit_store().initialize()
    await init_auth_db()
    await seed_default_admin(settings)
    app.state.investigation_job_service = job_service
    schedule_runner.bind_job_service(job_service)
    await schedule_runner.start()
    logger.info(
        "Starting DevOps Open Agent | service={} version={} environment={}",
        settings.service_name,
        settings.version,
        settings.app_env,
    )
    yield
    await schedule_runner.shutdown()
    logger.info("Shutting down DevOps Open Agent")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="DevOps Open Agent",
        description="Open Source AI-Powered DevOps Troubleshooting Platform",
        version=settings.version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["WWW-Authenticate"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error | path={}", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": sanitize_error_message(str(exc))},
        )

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def root_health_check() -> HealthResponse:
        return HealthResponse(
            status="healthy",
            service=settings.service_name,
            version=settings.version,
        )

    app.include_router(health_v1.router, prefix="/api/v1")
    app.include_router(auth_v1.router, prefix="/api/v1")
    app.include_router(system_v1.router, prefix="/api/v1")
    app.include_router(clusters_v1.router, prefix="/api/v1")
    app.include_router(investigations_v1.router, prefix="/api/v1")
    app.include_router(llm_usage_v1.router, prefix="/api/v1")
    app.include_router(audit_v1.router, prefix="/api/v1")
    app.include_router(topology_v1.router, prefix="/api/v1")
    app.include_router(diagnose_v1.router, prefix="/api/v1")
    app.include_router(aws_v1, prefix="/api/v1")
    app.include_router(cloud_cost_v1, prefix="/api/v1")
    app.include_router(pr_reviewer_v1, prefix="/api/v1")
    app.include_router(performance_v1, prefix="/api/v1")
    app.include_router(security_v1, prefix="/api/v1")
    app.include_router(integrations_v1.router, prefix="/api/v1")
    app.include_router(kubernetes_schedules_v1.router, prefix="/api/v1")

    return app


app = create_app()
