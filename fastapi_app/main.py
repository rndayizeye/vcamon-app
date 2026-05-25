from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fastapi_app.app.auth import (
    AuthConfigurationError,
    AuthServiceError,
    authenticate_access_token,
    extract_bearer_token,
    get_auth_settings,
    is_public_path,
)
from fastapi_app.app.routers import router


def create_app() -> FastAPI:
    app = FastAPI(title="VCA Monitor API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        settings = get_auth_settings()
        request.state.auth_user = None

        if (
            request.method == "OPTIONS"
            or not settings.enabled
            or is_public_path(request.url.path)
        ):
            return await call_next(request)

        access_token = extract_bearer_token(request.headers.get("Authorization"))
        if not access_token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid bearer token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            user = authenticate_access_token(access_token, settings)
        except AuthConfigurationError as exc:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": str(exc)},
            )
        except AuthServiceError as exc:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"detail": str(exc)},
            )

        if not user:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired access token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.state.auth_user = user
        return await call_next(request)

    app.include_router(router, prefix="/api")

    @app.get("/")
    def read_root():
        return {"message": "VCA Monitor FastAPI Backend is running"}

    @app.get("/health")
    def health_check():
        return {"status": "healthy", "message": "FastAPI backend is operational"}

    return app


app = create_app()
