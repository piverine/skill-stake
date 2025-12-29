"""
Unit tests for JWT middleware
Tests token validation with various token states and user data isolation scenarios
Requirements: 1.3, 1.4
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.core.auth import ClerkJWTVerifier, get_current_user
from app.models.user import User
import jwt
import json
from datetime import datetime, timedelta

class TestJWTMiddleware:
    """Test JWT middleware functionality"""
    
    def test_public_routes_no_auth_required(self, client):
        """Test that public routes don't require authentication"""
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        
        # Test API status endpoint
        response = client.get("/api/v1/status")
        assert response.status_code == 200

    def test_protected_routes_require_auth(self, client):
        """Test that protected routes require authentication"""
        # Test auth endpoints without token
        response = client.post("/api/v1/auth/verify")
        assert response.status_code == 401
        assert "Authorization header missing" in response.json()["detail"]
        
        response = client.get("/api/v1/auth/user")
        assert response.status_code == 401

    def test_invalid_auth_header_format(self, client):
        """Test various invalid authorization header formats"""
        # Missing Bearer prefix
        response = client.post(
            "/api/v1/auth/verify",
            headers={"Authorization": "invalid_token"}
        )
        assert response.status_code == 401
        assert "Invalid authorization header format" in response.json()["detail"]
        
        # Empty Bearer token
        response = client.post(
            "/api/v1/auth/verify",
            headers={"Authorization": "Bearer "}
        )
        assert response.status_code == 401

    @patch('app.core.auth.clerk_verifier.verify_token')
    def test_valid_token_authentication(self, mock_verify, client, sample_user):
        """Test successful authentication with valid token"""
        # Mock successful token verification
        mock_verify.return_value = {
            "sub": "user_test123",
            "email": "test@example.com",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp()
        }
        
        response = client.post(
            "/api/v1/auth/verify",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user"]["clerk_id"] == "user_test123"
        assert data["user"]["email"] == "test@example.com"

    @patch('app.core.auth.clerk_verifier.verify_token')
    def test_expired_token_rejection(self, mock_verify, client):
        """Test rejection of expired tokens"""
        # Mock expired token
        mock_verify.side_effect = jwt.ExpiredSignatureError("Token has expired")
        
        response = client.post(
            "/api/v1/auth/verify",
            headers={"Authorization": "Bearer expired_token"}
        )
        
        assert response.status_code == 401
        assert "Token has expired" in response.json()["detail"]

    @patch('app.core.auth.clerk_verifier.verify_token')
    def test_invalid_token_rejection(self, mock_verify, client):
        """Test rejection of invalid tokens"""
        # Mock invalid token
        mock_verify.side_effect = jwt.InvalidTokenError("Invalid token")
        
        response = client.post(
            "/api/v1/auth/verify",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    @patch('app.core.auth.clerk_verifier.verify_token')
    def test_user_data_isolation(self, mock_verify, client, db_session):
        """Test that users can only access their own data"""
        # Create two users
        user1 = User(clerk_id="user_1", email="user1@example.com")
        user2 = User(clerk_id="user_2", email="user2@example.com")
        db_session.add_all([user1, user2])
        db_session.commit()
        
        # Test access with user1 token
        mock_verify.return_value = {
            "sub": "user_1",
            "email": "user1@example.com"
        }
        
        response = client.get(
            "/api/v1/auth/user",
            headers={"Authorization": "Bearer user1_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["clerk_id"] == "user_1"
        assert data["email"] == "user1@example.com"
        
        # Test access with user2 token
        mock_verify.return_value = {
            "sub": "user_2", 
            "email": "user2@example.com"
        }
        
        response = client.get(
            "/api/v1/auth/user",
            headers={"Authorization": "Bearer user2_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["clerk_id"] == "user_2"
        assert data["email"] == "user2@example.com"

    @patch('app.core.auth.clerk_verifier.verify_token')
    def test_new_user_creation(self, mock_verify, client, db_session):
        """Test automatic user creation for new Clerk users"""
        # Mock token for new user not in database
        mock_verify.return_value = {
            "sub": "new_user_123",
            "email": "newuser@example.com"
        }
        
        response = client.get(
            "/api/v1/auth/user",
            headers={"Authorization": "Bearer new_user_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["clerk_id"] == "new_user_123"
        assert data["email"] == "newuser@example.com"
        
        # Verify user was created in database
        user = db_session.query(User).filter(User.clerk_id == "new_user_123").first()
        assert user is not None
        assert user.email == "newuser@example.com"

    def test_optional_authentication_endpoint(self, client):
        """Test endpoint that works with or without authentication"""
        # Test without authentication
        response = client.get("/api/v1/auth/user/optional")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert "No authentication provided" in data["message"]

    @patch('app.core.auth.clerk_verifier.verify_token')
    def test_optional_authentication_with_token(self, mock_verify, client, sample_user):
        """Test optional authentication endpoint with valid token"""
        mock_verify.return_value = {
            "sub": "user_test123",
            "email": "test@example.com"
        }
        
        response = client.get(
            "/api/v1/auth/user/optional",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user"]["clerk_id"] == "user_test123"

class TestClerkJWTVerifier:
    """Test ClerkJWTVerifier class functionality"""
    
    @pytest.fixture
    def verifier(self):
        return ClerkJWTVerifier()
    
    @patch('httpx.AsyncClient.get')
    async def test_jwks_caching(self, mock_get, verifier):
        """Test JWKS caching functionality"""
        # Mock JWKS response
        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": [{"kid": "test", "kty": "RSA"}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # First call should fetch from API
        jwks1 = await verifier.get_jwks()
        assert mock_get.call_count == 1
        
        # Second call should use cache
        jwks2 = await verifier.get_jwks()
        assert mock_get.call_count == 1  # No additional API call
        assert jwks1 == jwks2

    @patch('httpx.AsyncClient.get')
    async def test_jwks_fetch_failure(self, mock_get, verifier):
        """Test JWKS fetch failure handling"""
        # Mock failed response
        mock_get.side_effect = Exception("Network error")
        
        with pytest.raises(Exception) as exc_info:
            await verifier.get_jwks()
        
        assert "Unable to fetch JWKS" in str(exc_info.value)

    def test_signing_key_extraction(self, verifier):
        """Test signing key extraction from JWKS"""
        jwks = {
            "keys": [
                {
                    "kid": "test_key",
                    "kty": "RSA",
                    "n": "test_n",
                    "e": "AQAB"
                }
            ]
        }
        
        # This would normally extract the key, but we'll test the structure
        try:
            verifier.get_signing_key(jwks, "test_key")
        except Exception:
            # Expected to fail without proper RSA key data
            pass
        
        # Test missing key
        with pytest.raises(Exception) as exc_info:
            verifier.get_signing_key(jwks, "missing_key")
        
        assert "Unable to find appropriate signing key" in str(exc_info.value)