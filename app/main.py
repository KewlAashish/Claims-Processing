from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import claims, members, policies
from app.persistence.database import create_all
from app.services.errors import ConflictError, NotFoundError, ValidationError


def create_app() -> FastAPI:
    create_all()
    app = FastAPI(title="Claims Processing System")
    app.include_router(members.router)
    app.include_router(policies.router)
    app.include_router(claims.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def validation_handler(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict_handler(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return app


app = create_app()
