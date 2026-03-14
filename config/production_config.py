"""
Production configuration for Quantum Portfolio Optimization System
"""
import os
from dataclasses import dataclass
from typing import Optional
import logging

# Configure logging for production (file only if dir exists; stream always)
def _logging_handlers():
    handlers = [logging.StreamHandler()]
    log_dir = '/var/log/quantum_portfolio'
    try:
        os.makedirs(log_dir, exist_ok=True)
        handlers.insert(0, logging.FileHandler(os.path.join(log_dir, 'production.log')))
    except (OSError, PermissionError):
        pass  # Use only StreamHandler (e.g. HF Spaces, containers)
    return handlers


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=_logging_handlers()
)


@dataclass
class ProductionConfig:
    """Production configuration settings"""
    
    # Application settings
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    TESTING: bool = False
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    WORKERS: int = 4
    THREADS: int = 2
    
    # Database configuration
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/prod')
    DATABASE_POOL_SIZE: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Redis configuration for caching
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = os.getenv('REDIS_PASSWORD')
    CACHE_TTL: int = 300  # 5 minutes
    
    # Security settings
    SECRET_KEY: str = os.getenv('SECRET_KEY', '')
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', '')
    JWT_ACCESS_TOKEN_EXPIRES: int = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES: int = 2592000  # 30 days
    
    # Rate limiting
    RATELIMIT_STORAGE_URL: str = os.getenv('RATELIMIT_STORAGE_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}/1')
    DEFAULT_RATE_LIMIT: str = "1000 per hour"
    OPTIMIZATION_RATE_LIMIT: str = "100 per hour"
    
    # Quantum computation limits
    MAX_ASSETS: int = int(os.getenv('MAX_ASSETS', 100))
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv('MAX_REQUESTS_PER_MINUTE', 100))
    QUANTUM_COMPUTE_TIMEOUT: int = int(os.getenv('QUANTUM_COMPUTE_TIMEOUT', 30))  # seconds
    MAX_EVOLUTION_TIME: int = int(os.getenv('MAX_EVOLUTION_TIME', 50))
    
    # External API limits
    YFINANCE_RATE_LIMIT: int = int(os.getenv('YFINANCE_RATE_LIMIT', 2000))  # requests per hour
    YFINANCE_TIMEOUT: int = int(os.getenv('YFINANCE_TIMEOUT', 30))  # seconds
    
    # Performance settings
    USE_OPTIMIZED_QUANTUM: bool = True
    ENABLE_CACHE: bool = True
    CACHE_COMPRESSION: bool = True
    
    # Monitoring and observability
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    SENTRY_DSN: Optional[str] = os.getenv('SENTRY_DSN')
    PROMETHEUS_ENABLED: bool = True
    METRICS_INTERVAL: int = 30  # seconds
    
    # Compliance and audit
    AUDIT_LOGGING: bool = True
    COMPLIANCE_LOG_PATH: str = '/var/log/quantum_portfolio/compliance.log'
    DATA_RETENTION_DAYS: int = 730  # 2 years
    
    # Backup and recovery
    BACKUP_ENABLED: bool = True
    BACKUP_SCHEDULE: str = "0 2 * * *"  # Daily at 2 AM
    BACKUP_RETENTION_DAYS: int = 90
    S3_BACKUP_BUCKET: Optional[str] = os.getenv('S3_BACKUP_BUCKET')
    
    # Circuit breaker settings
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 60  # seconds
    CIRCUIT_BREAKER_RESET_TIMEOUT: int = 300  # seconds
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        # Use placeholder secrets when not set (e.g. HF Spaces, demo) - not for real production
        if not self.SECRET_KEY:
            self.SECRET_KEY = os.getenv(
                "SECRET_KEY",
                "hf-demo-secret-change-in-production-" + str(os.getpid())
            )
        if not self.JWT_SECRET_KEY:
            self.JWT_SECRET_KEY = os.getenv(
                "JWT_SECRET_KEY",
                "hf-demo-jwt-secret-change-in-production-" + str(os.getpid())
            )
        if self.DEBUG:
            raise ValueError("DEBUG should be False in production")
        if self.TESTING:
            raise ValueError("TESTING should be False in production")


@dataclass
class StagingConfig(ProductionConfig):
    """Staging environment configuration"""
    ENVIRONMENT: str = "staging"
    DEBUG: bool = False
    DATABASE_URL: str = os.getenv('STAGING_DATABASE_URL', 'postgresql://user:pass@localhost/staging')
    DEFAULT_RATE_LIMIT: str = "5000 per hour"


@dataclass
class DevelopmentConfig:
    """Development environment configuration"""
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    TESTING: bool = False
    DATABASE_URL: str = os.getenv('DEV_DATABASE_URL', 'sqlite:///dev_portfolio.db')
    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379
    SECRET_KEY: str = 'dev-secret-key-change-in-production'
    JWT_SECRET_KEY: str = 'dev-jwt-secret-change-in-production'
    MAX_ASSETS: int = 50
    MAX_REQUESTS_PER_MINUTE: int = 1000
    QUANTUM_COMPUTE_TIMEOUT: int = 60
    AUDIT_LOGGING: bool = False


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'production')
    
    if env == 'development':
        return DevelopmentConfig()
    elif env == 'staging':
        return StagingConfig()
    else:
        return ProductionConfig()


# Global configuration instance
CONFIG = get_config()