from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from uuid import UUID


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure tenant isolation"""

    async def dispatch(self, request: Request, call_next):
        """
        Validate that authenticated users can only access their organization's data.
        This is a basic implementation. The real validation happens at the route level
        when checking organization_id from request parameters.
        """
        response = await call_next(request)
        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for global error handling"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            raise
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"},
            )
