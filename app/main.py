"""FastAPI application entry point.

Creates the FastAPI application instance with exception handlers
and middleware configuration.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()
    
    app = FastAPI(
        title="High-Frequency Transaction System",
        description="Core Banking Lite - A fintech portfolio project",
        version="1.0.0",
        debug=settings.DEBUG,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Register API routers
    app.include_router(api_router, prefix="/api/v1")
    
    return app


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers for the application."""
    
    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ) -> JSONResponse:
        """Handle all custom application exceptions.
        
        Returns a consistent JSON error response format.
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": exc.__class__.__name__,
                    "message": exc.message,
                    "status_code": exc.status_code,
                }
            },
        )


# Create the application instance
app = create_app()
