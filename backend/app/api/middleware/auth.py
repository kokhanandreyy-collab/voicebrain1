from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request
import jwt
import structlog
from infrastructure.config import settings

logger = structlog.get_logger()

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Initialize default state
        request.state.user_id = None
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Decode and verify token
                payload = jwt.decode(
                    token, 
                    settings.SECRET_KEY, 
                    algorithms=["HS256"], 
                    options={"verify_signature": True}
                )
                
                # Extract user identifier (usually 'sub')
                user_id = payload.get("sub")
                if user_id:
                    request.state.user_id = user_id
                    # Bind user_id to logging context for this request
                    structlog.contextvars.bind_contextvars(user_id=user_id)
                    
            except jwt.ExpiredSignatureError:
                return JSONResponse(
                    {"code": "auth_error", "message": "Token has expired"}, 
                    status_code=401
                )
            except jwt.InvalidTokenError:
                return JSONResponse(
                    {"code": "auth_error", "message": "Invalid authentication token"}, 
                    status_code=401
                )
            except Exception as e:
                logger.error("Middleware auth unexpected error", error=str(e))
                return JSONResponse(
                    {"code": "auth_error", "message": "Authentication failed"}, 
                    status_code=401
                )
        
        response = await call_next(request)
        return response
