from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.auth import clerk_verifier
import logging

logger = logging.getLogger(__name__)

class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically verify JWT tokens for protected routes
    """
    
    def __init__(self, app, protected_paths: list = None):
        super().__init__(app)
        self.protected_paths = protected_paths or [
            "/api/v1/stakes",
            "/api/v1/quiz", 
            "/api/v1/upload",
            "/api/v1/user"
        ]
        self.public_paths = [
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public paths
        if any(request.url.path.startswith(path) for path in self.public_paths):
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Check if path requires authentication
        requires_auth = any(
            request.url.path.startswith(path) for path in self.protected_paths
        )
        
        if requires_auth:
            try:
                # Extract token from Authorization header
                auth_header = request.headers.get("Authorization")
                if not auth_header:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Authorization header missing"}
                    )
                
                if not auth_header.startswith("Bearer "):
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Invalid authorization header format"}
                    )
                
                token = auth_header.split(" ")[1]
                
                # Verify token
                payload = await clerk_verifier.verify_token(token)
                
                # Add user info to request state for use in endpoints
                request.state.user_id = payload.get("sub")
                request.state.user_email = payload.get("email")
                request.state.token_payload = payload
                
                logger.info(f"Authenticated request for user: {payload.get('sub')}")
                
            except HTTPException as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail}
                )
            except Exception as e:
                logger.error(f"Authentication middleware error: {str(e)}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authentication failed"}
                )
        
        return await call_next(request)