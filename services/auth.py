"""
JWT Authentication Module for Quantum Portfolio API

Provides JWT-based authentication with support for:
- Access tokens (short-lived)
- Refresh tokens (long-lived)
- Token blacklisting for logout
- Multi-tenant support

Usage:
    from services.auth import create_access_token, verify_token

    # Create token
    token = create_access_token(user_id="user123", tenant_id="tenant456")

    # Verify token
    payload = verify_token(token)
    if payload:
        user_id = payload['sub']
"""

import os
import time
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

# Import Flask separately so it's always available for type hints
from flask import Flask

logger = logging.getLogger(__name__)

# Try to import Flask-JWT-Extended
try:
    from flask_jwt_extended import (
        create_access_token as jwt_create_access_token,
        create_refresh_token as jwt_create_refresh_token,
        decode_token as jwt_decode_token,
        get_jwt_identity,
        get_jwt,
        jwt_required,
        JWTManager,
    )
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("Flask-JWT-Extended not installed. JWT authentication unavailable.")


class TokenDatabase:
    """
    Simple in-memory token blacklist for logout functionality.
    In production, use Redis or database-backed storage.
    """
    
    def __init__(self):
        self._blacklist: Dict[str, float] = {}  # jti -> expiry_timestamp
        self._cleanup_interval = 3600  # 1 hour
        self._last_cleanup = time.time()
    
    def add_to_blacklist(self, jti: str, expiry: float):
        """Add token JTI to blacklist."""
        self._blacklist[jti] = expiry
        self._cleanup_if_needed()
    
    def is_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted."""
        if jti in self._blacklist:
            if time.time() < self._blacklist[jti]:
                return True
            else:
                # Expired, remove from blacklist
                del self._blacklist[jti]
        return False
    
    def _cleanup_if_needed(self):
        """Remove expired tokens from blacklist."""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._blacklist = {
                jti: exp for jti, exp in self._blacklist.items()
                if exp > now
            }
            self._last_cleanup = now


# Global token blacklist
token_db = TokenDatabase()


def init_jwt(app: Flask):
    """
    Initialize JWT authentication for Flask app.
    
    Configures:
    - Secret keys
    - Token expiration
    - Token blacklisting
    - Custom claims
    """
    if not JWT_AVAILABLE:
        logger.error("JWT not available - skipping initialization")
        return False
    
    # Configuration
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(
        minutes=int(os.getenv('JWT_ACCESS_EXPIRY_MINUTES', '60'))
    )
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(
        days=int(os.getenv('JWT_REFRESH_EXPIRY_DAYS', '7'))
    )
    app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'
    app.config['JWT_COOKIE_SECURE'] = os.getenv('JWT_COOKIE_SECURE', 'false').lower() == 'true'
    app.config['JWT_COOKIE_CSRF_PROTECT'] = True
    
    # Initialize JWT manager
    jwt = JWTManager(app)
    
    # Register token blacklist callback
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get('jti')
        return token_db.is_blacklisted(jti) if jti else False
    
    # Custom error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {
            'error': {
                'code': 'TOKEN_EXPIRED',
                'message': 'Token has expired'
            }
        }, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {
            'error': {
                'code': 'INVALID_TOKEN',
                'message': 'Invalid token'
            }
        }, 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {
            'error': {
                'code': 'MISSING_TOKEN',
                'message': 'Authorization token required'
            }
        }, 401
    
    logger.info("JWT authentication initialized")
    return True


def create_access_token(
    user_id: str,
    tenant_id: str = "default",
    additional_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token.
    
    Args:
        user_id: Unique user identifier
        tenant_id: Multi-tenant identifier
        additional_claims: Custom claims to add
        expires_delta: Custom expiration time
        
    Returns:
        JWT token string
    """
    if not JWT_AVAILABLE:
        raise RuntimeError("JWT not available")
    
    claims = {
        'tenant_id': tenant_id,
        'type': 'access',
    }
    
    if additional_claims:
        claims.update(additional_claims)
    
    return jwt_create_access_token(
        identity=user_id,
        additional_claims=claims,
        expires_delta=expires_delta
    )


def create_refresh_token(
    user_id: str,
    tenant_id: str = "default"
) -> str:
    """
    Create JWT refresh token.
    
    Args:
        user_id: Unique user identifier
        tenant_id: Multi-tenant identifier
        
    Returns:
        JWT refresh token string
    """
    if not JWT_AVAILABLE:
        raise RuntimeError("JWT not available")
    
    return jwt_create_refresh_token(
        identity=user_id,
        additional_claims={'tenant_id': tenant_id}
    )


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload or None if invalid
    """
    if not JWT_AVAILABLE:
        return None
    
    try:
        payload = jwt_decode_token(token)
        
        # Check blacklist
        jti = payload.get('jti')
        if jti and token_db.is_blacklisted(jti):
            logger.warning(f"Token {jti} is blacklisted")
            return None
        
        return payload
        
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        return None


def revoke_token(token: str) -> bool:
    """
    Revoke JWT token (add to blacklist).
    
    Args:
        token: JWT token string
        
    Returns:
        True if successfully revoked
    """
    if not JWT_AVAILABLE:
        return False
    
    try:
        payload = jwt_decode_token(token)
        jti = payload.get('jti')
        exp = payload.get('exp')
        
        if jti and exp:
            token_db.add_to_blacklist(jti, exp)
            logger.info(f"Token {jti} revoked")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to revoke token: {e}")
        return False


def get_current_user() -> Optional[Dict[str, str]]:
    """
    Get current authenticated user from request context.
    Must be called within a request context with @jwt_required.
    
    Returns:
        Dict with user_id and tenant_id, or None
    """
    if not JWT_AVAILABLE:
        return None
    
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()
        
        return {
            'user_id': user_id,
            'tenant_id': claims.get('tenant_id', 'default'),
            'type': claims.get('type', 'access'),
        }
    except Exception:
        return None


def hash_api_key(api_key: str) -> str:
    """Hash API key for storage."""
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()


def generate_api_key(tenant_id: str, key_name: str = "") -> str:
    """
    Generate a new API key for tenant.
    
    Returns plain text key once - store hash for verification.
    """
    import uuid
    plain = f"{uuid.uuid4()}:{tenant_id}:{time.time()}"
    return hashlib.sha256(plain.encode('utf-8')).hexdigest()
