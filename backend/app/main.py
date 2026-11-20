import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, bookings, employees, identity, parking, reports, slots
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.mongo import close_client, ping_database
from app.schemas.common import error_response, success_response

logger = logging.getLogger("parking_tracker")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.validate_for_runtime()
    if ping_database():
        from migrations.runner import run_migrations

        applied = run_migrations()
        if applied:
            logger.info("Applied migrations: %s", ", ".join(applied))
    else:
        logger.error("MongoDB is not reachable at %s. Start MongoDB, then restart the API.", settings.mongo_uri)
    yield
    close_client()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError):
        return error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(part) for part in error["loc"][1:]), "message": error["msg"]}
            for error in exc.errors()
        ]
        return error_response(422, "VALIDATION_ERROR", "Some fields are invalid.", details)

    @app.exception_handler(HTTPException)
    async def handle_http_error(_request: Request, exc: HTTPException):
        return error_response(exc.status_code, "HTTP_ERROR", str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return error_response(500, "INTERNAL_ERROR", "Something went wrong on the server. Please try again.")

    api = APIRouter(prefix="/api")

    @api.get("/health", tags=["System"])
    def health():
        database_up = ping_database()
        payload = {"status": "ok" if database_up else "degraded", "database": "up" if database_up else "down"}
        if not database_up:
            return error_response(503, "DATABASE_UNAVAILABLE", "MongoDB is not reachable.", payload)
        return success_response(payload, message="Service is healthy.")

    api.include_router(auth.router)
    api.include_router(identity.router)
    api.include_router(slots.router)
    api.include_router(parking.router)
    api.include_router(bookings.router)
    api.include_router(employees.router)
    api.include_router(reports.dashboard_router)
    api.include_router(reports.reports_router)
    app.include_router(api)
    return app


app = create_app()
