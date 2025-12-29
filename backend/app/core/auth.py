import jwt
import httpx
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
import json
import time
from functools import lru_cache

security = HTTPBearer()

class ClerkJWTVerifier:
    def __init__(self):
        self.jwks_cache = {}
        self.jwks_cache_time = 0
        self.cache_duration = 3600  # 1 hour
    
    @lru_cache(maxsize=1)
    def get_clerk_jwks_url(self) -> str:
        """Get Clerk JWKS URL from settings"""
        return settings.CLERK_JWKS_URL
    
    async def get_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Clerk with caching"""
        current_time = time.time()
        
        if (current_time - self.jwks_cache_time) < self.cache_duration and self.jwks_cache:
            return self.jwks_cache
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.get_clerk_jwks_url())
                response.raise_for_status()
                jwks_data = response.json()
                
                self.jwks_cache = jwks_data
                self.jwks_cache_time = current_time
                return jwks_data
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to fetch JWKS: {str(e)}"
            )
    
    def get_signing_key(self, jwks: Dict[str, Any], kid: str) -> str:
        """Extract signing key from JWKS"""
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find appropriate signing key"
        )
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token with Clerk"""
        try:
            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing key ID"
                )
            
            # Get JWKS and signing key
            jwks = await self.get_jwks()
            signing_key = self.get_signing_key(jwks, kid)
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                options={"verify_exp": True, "verify_aud": False}
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}"
            )

# Global verifier instance
clerk_verifier = ClerkJWTVerifier()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user
    Validates JWT token and returns user from database
    """
    try:
        # Verify token with Clerk
        payload = await clerk_verifier.verify_token(credentials.credentials)
        
        # Extract user ID from token
        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user ID"
            )
        
        # Get user from database
        user = db.query(User).filter(User.clerk_id == clerk_user_id).first()
        if not user:
            # Create user if doesn't exist (first time login)
            user_email = payload.get("email", "")
            user = User(
                clerk_id=clerk_user_id,
                email=user_email
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

async def get_optional_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication dependency
    Returns user if authenticated, None otherwise
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        payload = await clerk_verifier.verify_token(token)
        
        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            return None
        
        user = db.query(User).filter(User.clerk_id == clerk_user_id).first()
        return user
        
    except Exception:
        return None

def require_user_access(target_user_id: str, current_user: User) -> None:
    """
    Utility function to ensure user can only access their own data
    """
    if str(current_user.user_id) != target_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own data"
        )