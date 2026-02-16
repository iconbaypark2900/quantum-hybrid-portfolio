"""
Backend API for Quantum Hybrid Portfolio Dashboard
Provides REST API endpoints for the React frontend
"""
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import numpy as np
import pandas as pd
import json
import os
import uuid
import time
import hashlib
import sqlite3
import threading
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import logging
from pythonjsonlogger.json import JsonFormatter as jsonlogger_JsonFormatter
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Import quantum hybrid portfolio modules
from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
from core.quantum_inspired.graph_builder import FinancialGraphBuilder
from config.qsw_config import QSWConfig
from services.portfolio_optimizer import run_optimization, get_config_for_preset
from services.constraints import PortfolioConstraints

# Import market data service
from services.market_data import fetch_market_data, validate_tickers

# Import backtesting service
from services.backtest import run_backtest as run_backtesting
from services.data_provider import load_market_payload

# ─── Structured JSON Logging ───
log_handler = logging.StreamHandler()
formatter = jsonlogger_JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s',
    rename_fields={'asctime': 'timestamp', 'levelname': 'level', 'name': 'logger'},
)
log_handler.setFormatter(formatter)

logging.root.handlers = []
logging.root.addHandler(log_handler)
logging.root.setLevel(getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO))
logger = logging.getLogger(__name__)

# ─── Prometheus Metrics ───
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
)
OPTIMIZATION_LATENCY = Histogram(
    'optimization_duration_seconds',
    'Portfolio optimization duration',
    ['objective'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)
MARKET_DATA_LATENCY = Histogram(
    'market_data_fetch_duration_seconds',
    'Market data fetch duration',
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

# ─── In-Memory Cache for Market Data ───
_market_data_cache = {}
CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))  # 1 hour default
API_DB_PATH = os.getenv('API_DB_PATH', os.path.join(os.path.dirname(__file__), 'data', 'api.sqlite3'))

# ─── Async Job Runtime ───
_executor = ThreadPoolExecutor(max_workers=int(os.getenv("JOB_WORKERS", "4")))
_jobs = {}
_jobs_lock = threading.Lock()

def _cache_key(tickers, start_date, end_date):
    raw = f"{','.join(sorted(tickers))}:{start_date}:{end_date}"
    return hashlib.md5(raw.encode()).hexdigest()

def cache_get(key):
    entry = _market_data_cache.get(key)
    if entry and time.time() - entry['ts'] < CACHE_TTL:
        return entry['data']
    if entry:
        del _market_data_cache[key]
    return None

def cache_set(key, data):
    # Evict old entries if cache grows too large (max 100 entries)
    if len(_market_data_cache) >= 100:
        oldest = min(_market_data_cache, key=lambda k: _market_data_cache[k]['ts'])
        del _market_data_cache[oldest]
    _market_data_cache[key] = {'data': data, 'ts': time.time()}


app = Flask(__name__)


def _ensure_runtime_tables() -> None:
    """Create local runtime tables for API keys, audit logs, and async jobs metadata."""
    os.makedirs(os.path.dirname(API_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(API_DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                key_hash TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                key_name TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_used_at TEXT,
                usage_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT,
                tenant_id TEXT,
                action TEXT,
                endpoint TEXT,
                method TEXT,
                payload_json TEXT,
                response_status INTEGER,
                duration_ms REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_request_id ON audit_log(request_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_tenant_id ON audit_log(tenant_id)")
        conn.commit()
    finally:
        conn.close()


def _db_conn():
    return sqlite3.connect(API_DB_PATH)


_ensure_runtime_tables()


def log_business_audit(action: str, payload: dict, result: dict, status: int = 200):
    """Persist business-level audit record including request payload and result summary."""
    try:
        conn = _db_conn()
        cur = conn.cursor()
        merged_payload = {
            "request": payload or {},
            "result_summary": result or {},
        }
        cur.execute(
            """
            INSERT INTO audit_log (
                request_id, tenant_id, action, endpoint, method,
                payload_json, response_status, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                getattr(g, "request_id", ""),
                getattr(g, "tenant_id", "anonymous"),
                action,
                request.path if request else action,
                request.method if request else "INTERNAL",
                json.dumps(merged_payload),
                int(status),
                0.0,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning(f"business_audit_write_failed: {exc}")


def log_async_audit(tenant_id: str, action: str, payload: dict, result: dict, status: int):
    """Audit logger for async workers where request context is unavailable."""
    try:
        conn = _db_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO audit_log (
                request_id, tenant_id, action, endpoint, method,
                payload_json, response_status, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "",
                tenant_id or "anonymous",
                action,
                action,
                "ASYNC",
                json.dumps({"request": payload or {}, "result_summary": result or {}}),
                int(status),
                0.0,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning(f"async_audit_write_failed: {exc}")

# ─── Security Configuration ───

# Request size limit (1 MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

# CORS: restrict to configured origins
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
CORS(app, origins=[o.strip() for o in cors_origins])

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per minute"],
    storage_uri=os.getenv('RATELIMIT_STORAGE_URL', 'memory://'),
)

# API key authentication
API_KEY = os.getenv('API_KEY', '')
API_KEY_REQUIRED = os.getenv('API_KEY_REQUIRED', 'false').lower() == 'true'


def _hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _lookup_tenant_by_key(key: str):
    """Lookup tenant by API key hash in local auth table."""
    if not key:
        return None
    key_hash = _hash_api_key(key)
    conn = _db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT tenant_id, key_name, usage_count
            FROM api_keys
            WHERE key_hash = ? AND is_active = 1
            """,
            (key_hash,),
        )
        row = cur.fetchone()
        if not row:
            return None
        tenant_id, key_name, usage_count = row
        cur.execute(
            """
            UPDATE api_keys
            SET last_used_at = CURRENT_TIMESTAMP,
                usage_count = ?
            WHERE key_hash = ?
            """,
            (int(usage_count or 0) + 1, key_hash),
        )
        conn.commit()
        return {"tenant_id": tenant_id, "key_name": key_name}
    finally:
        conn.close()


def _create_api_key(tenant_id: str, key_name: str = "") -> str:
    """Create and store a tenant API key, returning plaintext once."""
    plain = hashlib.sha256(f"{uuid.uuid4()}:{tenant_id}:{time.time()}".encode()).hexdigest()
    key_hash = _hash_api_key(plain)
    conn = _db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO api_keys (key_hash, tenant_id, key_name, is_active, created_at)
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
            """,
            (key_hash, tenant_id, key_name or ""),
        )
        conn.commit()
    finally:
        conn.close()
    return plain

def require_api_key(f):
    """
    Multi-tenant API key auth.
    Priority:
    1) If static API_KEY env is set, it must match.
    2) Else if key exists in api_keys table, use tenant mapping.
    3) Else allow only when API_KEY_REQUIRED is false.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key', '')
        if API_KEY:
            if key != API_KEY:
                return error_response('Unauthorized. Provide a valid X-API-Key header.', code='UNAUTHORIZED', status=401)
            g.tenant_id = "default"
            return f(*args, **kwargs)

        tenant = _lookup_tenant_by_key(key) if key else None
        if tenant:
            g.tenant_id = tenant["tenant_id"]
            g.api_key_name = tenant["key_name"]
            return f(*args, **kwargs)

        if API_KEY_REQUIRED:
            return error_response('Unauthorized. Provide a valid X-API-Key header.', code='UNAUTHORIZED', status=401)

        g.tenant_id = "anonymous"
        return f(*args, **kwargs)
    return decorated

# ─── Standardized Response Helpers ───

def success_response(data, status=200, extra_meta=None):
    """Wrap successful payload in standard envelope."""
    meta = {
        "request_id": getattr(g, "request_id", ""),
        "duration_ms": round((time.time() - getattr(g, "start_time", time.time())) * 1000, 2),
    }
    if extra_meta:
        meta.update(extra_meta)
    return jsonify({"data": data, "meta": meta}), status


def error_response(message, code="ERROR", status=400):
    """Wrap error in standard envelope."""
    return jsonify({
        "error": {"code": code, "message": str(message)},
        "meta": {"request_id": getattr(g, "request_id", "")},
    }), status


# ─── Request Lifecycle Hooks ───

@app.before_request
def before_request_hook():
    g.request_id = str(uuid.uuid4())
    g.start_time = time.time()

@app.after_request
def after_request_hook(response):
    # Metrics
    duration = time.time() - getattr(g, 'start_time', time.time())
    endpoint = request.endpoint or 'unknown'
    REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)

    # Structured log
    logger.info('request_completed', extra={
        'request_id': getattr(g, 'request_id', ''),
        'tenant_id': getattr(g, 'tenant_id', 'anonymous'),
        'method': request.method,
        'path': request.path,
        'status': response.status_code,
        'duration_ms': round(duration * 1000, 2),
        'remote_addr': request.remote_addr,
    })

    # Persist audit trail (best-effort)
    try:
        payload = None
        if request.method in ("POST", "PUT", "PATCH"):
            payload = request.get_json(silent=True)
        conn = _db_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO audit_log (
                request_id, tenant_id, action, endpoint, method,
                payload_json, response_status, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                getattr(g, "request_id", ""),
                getattr(g, "tenant_id", "anonymous"),
                request.endpoint or "unknown",
                request.path,
                request.method,
                json.dumps(payload) if payload is not None else None,
                int(response.status_code),
                float(round(duration * 1000, 2)),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as audit_exc:
        logger.warning(f"audit_log_write_failed: {audit_exc}")

    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-Request-Id'] = getattr(g, 'request_id', '')

    if os.getenv('HF_SPACES') == '1':
        response.headers['Content-Security-Policy'] = (
            "default-src 'self' https://*.hf.space; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "connect-src 'self' https://*.hf.space; "
            "frame-ancestors 'self' https://huggingface.co https://*.hf.space"
        )
    else:
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self'"
        )
    return response

# Initialize the optimizer
global_optimizer = QuantumStochasticWalkOptimizer()

def generate_mock_data(n_assets, regime):
    """Generate mock market data for demonstration."""
    # Asset names
    names = ["AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","JPM","V","JNJ",
             "PG","UNH","HD","MA","BAC","DIS","NFLX","KO","PFE","CVX","WMT",
             "MRK","ABT","ADBE","NKE","PEP","T","VZ","PYPL","BRK"]

    sectors = ["Tech","Tech","Tech","Tech","Tech","Tech","Tech","Finance","Finance","Health",
               "Consumer","Health","Consumer","Finance","Finance","Consumer","Tech","Consumer",
               "Health","Energy","Consumer","Health","Health","Tech","Consumer","Consumer",
               "Telecom","Telecom","Tech","Finance"]

    # Adjust regime parameters
    regime_params = {
        'bull': {'drift': 0.0008, 'vol': 0.012, 'corr_base': 0.3},
        'bear': {'drift': -0.0003, 'vol': 0.022, 'corr_base': 0.6},
        'volatile': {'drift': 0.0002, 'vol': 0.028, 'corr_base': 0.45},
        'normal': {'drift': 0.0004, 'vol': 0.015, 'corr_base': 0.35},
    }

    params = regime_params.get(regime, regime_params['normal'])

    assets = []
    for i in range(n_assets):
        # Generate returns and volatility
        drift = params['drift'] + (np.random.random() - 0.4) * 0.001
        vol = params['vol'] * (0.7 + np.random.random() * 0.6)

        # Create artificial returns for the past year (252 trading days)
        returns = np.random.normal(drift, vol, 252)

        ann_return = np.mean(returns) * 252
        ann_vol = np.std(returns) * np.sqrt(252)
        sharpe = ann_return / ann_vol if ann_vol != 0 else 0

        assets.append({
            'name': names[i] if i < len(names) else f'ASSET_{i}',
            'sector': sectors[i] if i < len(sectors) else 'Other',
            'ann_return': ann_return,
            'ann_vol': ann_vol,
            'sharpe': sharpe
        })

    # Create correlation matrix
    corr = np.eye(n_assets)
    for i in range(n_assets):
        for j in range(i+1, n_assets):
            # Same sector gets slightly higher correlation
            same_sector_bonus = 0.1 if assets[i]['sector'] == assets[j]['sector'] else 0
            base_corr = params['corr_base']
            random_corr = np.random.uniform(-0.2, 0.4)
            corr_val = np.clip(base_corr + same_sector_bonus + random_corr, -0.3, 0.95)
            corr[i, j] = corr_val
            corr[j, i] = corr_val

    return assets, corr


# ─── Input Validation Helpers ───

import re

def sanitize_ticker(ticker):
    """Sanitize a ticker symbol to alphanumeric + dots/hyphens only."""
    cleaned = re.sub(r'[^A-Za-z0-9.\-]', '', str(ticker).strip().upper())
    return cleaned[:10]  # Max 10 chars

def validate_tickers_input(data, field='tickers'):
    """Validate and sanitize a list of tickers from request data. Returns (tickers, error)."""
    raw = data.get(field)
    if not raw:
        return None, f"'{field}' is required"
    if not isinstance(raw, list):
        return None, f"'{field}' must be a list"
    if len(raw) > 50:
        return None, f"Maximum 50 tickers allowed, got {len(raw)}"
    tickers = [sanitize_ticker(t) for t in raw if t]
    tickers = [t for t in tickers if t]  # Remove empty after sanitization
    if not tickers:
        return None, "No valid tickers provided after sanitization"
    return tickers, None

def validate_date(date_str, field_name='date'):
    """Validate a date string in YYYY-MM-DD format. Returns (date_str, error)."""
    if not date_str:
        return None, None  # Optional
    try:
        datetime.strptime(str(date_str), '%Y-%m-%d')
        return str(date_str), None
    except ValueError:
        return None, f"'{field_name}' must be in YYYY-MM-DD format, got '{date_str}'"

def validate_request(data, required_fields=None, numeric_ranges=None):
    """
    Validate request data with required fields and numeric range checks.
    Returns (cleaned_data, error_message).
    """
    if data is None:
        return None, "Request body is required (JSON)"

    errors = []

    if required_fields:
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"'{field}' is required")

    if numeric_ranges:
        for field, (lo, hi) in numeric_ranges.items():
            val = data.get(field)
            if val is not None:
                try:
                    val = float(val)
                    if val < lo or val > hi:
                        errors.append(f"'{field}' must be between {lo} and {hi}, got {val}")
                except (ValueError, TypeError):
                    errors.append(f"'{field}' must be a number")

    if errors:
        return None, '; '.join(errors)
    return data, None


@app.route('/api/market-data', methods=['GET', 'POST'])
@require_api_key
@limiter.limit("10 per minute")
def get_market_data():
    """Endpoint to fetch real market data using yfinance."""
    try:
        # Handle both GET and POST requests
        if request.method == 'GET':
            # Get parameters from query string
            tickers_param = request.args.get('tickers', '')
            start_date = request.args.get('start', None)
            end_date = request.args.get('end', None)
            
            if not tickers_param:
                return error_response('Tickers parameter is required', code='BAD_REQUEST', status=400)
                
            tickers = [t.strip().upper() for t in tickers_param.split(',')]
        else:  # POST
            # Get parameters from request body
            data = request.json
            if not data:
                return error_response('Request body is required for POST requests', code='BAD_REQUEST', status=400)
                
            tickers = data.get('tickers', [])
            start_date = data.get('start_date', None)
            end_date = data.get('end_date', None)
            
            if not tickers:
                return error_response('Tickers parameter is required', code='BAD_REQUEST', status=400)
        
        # Validate tickers
        if not isinstance(tickers, list) or len(tickers) == 0:
            return error_response('Tickers must be a non-empty list', code='BAD_REQUEST', status=400)
            
        # Limit number of tickers to prevent abuse
        if len(tickers) > 50:
            return error_response('Maximum of 50 tickers allowed', code='BAD_REQUEST', status=400)
            
        # Validate dates if provided
        if start_date:
            try:
                pd.to_datetime(start_date)
            except:
                return error_response('Invalid start date format. Use YYYY-MM-DD.', code='BAD_REQUEST', status=400)
                
        if end_date:
            try:
                pd.to_datetime(end_date)
            except:
                return error_response('Invalid end date format. Use YYYY-MM-DD.', code='BAD_REQUEST', status=400)
        
        # Check cache first
        ck = _cache_key(tickers, start_date or '', end_date or '')
        cached = cache_get(ck)
        if cached is not None:
            logger.info('market_data_cache_hit', extra={'cache_key': ck, 'tickers': tickers})
            return success_response(cached)

        # Fetch market data (with latency tracking)
        with MARKET_DATA_LATENCY.time():
            market_data = fetch_market_data(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date
            )

        # Store in cache
        cache_set(ck, market_data)
        
        return success_response(market_data)
        
    except ValueError as e:
        return error_response(str(e), code='BAD_REQUEST', status=400)
    except Exception as e:
        return error_response(f'Internal server error: {str(e)}', code='INTERNAL_ERROR', status=500)


@app.route('/api/portfolio/backtest', methods=['POST'])
@require_api_key
@limiter.limit("10 per minute")
def run_backtest():
    """Endpoint to run portfolio backtesting."""
    try:
        data = request.json
        backtest_results = _run_backtest_payload(data)
        log_business_audit(
            action="backtest_run",
            payload=data or {},
            result={
                "summary_metrics": backtest_results.get("summary_metrics", {}),
                "points": len(backtest_results.get("results", [])),
            },
            status=200,
        )
        return success_response(backtest_results)
        
    except ValueError as e:
        return error_response(str(e), code='BAD_REQUEST', status=400)
    except Exception as e:
        logger.error(f"Backtest endpoint error: {str(e)}", exc_info=True)
        return error_response(f'Internal server error: {str(e)}', code='INTERNAL_ERROR', status=500)


def _run_backtest_payload(data):
    """Shared backtest execution used by sync and async endpoints."""
    if not data:
        raise ValueError('Request body is required')

    tickers = data.get('tickers', [])
    start_date = data.get('start_date', None)
    end_date = data.get('end_date', None)
    rebalance_frequency = data.get('rebalance_frequency', 'monthly')
    objective = data.get('objective', 'max_sharpe')
    target_return = data.get('target_return', None)
    strategy_preset = data.get('strategy_preset', 'balanced')
    constraints = PortfolioConstraints.from_dict(data.get('constraints'))

    if not tickers:
        raise ValueError('Tickers parameter is required')
    if not start_date or not end_date:
        raise ValueError('Both start_date and end_date are required')

    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    if start_dt >= end_dt:
        raise ValueError('Start date must be before end date')

    valid_freqs = ['weekly', 'monthly', 'quarterly', 'yearly']
    if rebalance_frequency not in valid_freqs:
        raise ValueError(f'Invalid rebalance frequency. Valid options: {valid_freqs}')

    valid_objectives = ['max_sharpe', 'min_variance', 'target_return', 'risk_parity', 'hrp']
    if objective not in valid_objectives:
        raise ValueError(f'Invalid objective. Valid options: {valid_objectives}')

    return run_backtesting(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        rebalance_frequency=rebalance_frequency,
        objective=objective,
        target_return=target_return,
        strategy_preset=strategy_preset,
        constraints=constraints
    )

def calculate_portfolio_metrics(weights, returns, covariance_matrix):
    """Calculate portfolio metrics from weights, returns and covariance."""
    # Expected return
    portfolio_return = np.dot(weights, returns)
    
    # Volatility
    portfolio_variance = np.dot(weights, np.dot(covariance_matrix, weights))
    portfolio_volatility = np.sqrt(portfolio_variance)
    
    # Sharpe ratio (assuming 0 risk-free rate)
    sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility != 0 else 0
    
    # Effective number of assets
    n_assets_effective = 1 / np.sum(weights ** 2) if np.sum(weights ** 2) != 0 else 0
    
    # Number of active assets (with meaningful weight)
    n_active = np.sum(weights > 0.005)
    
    return {
        'expected_return': float(portfolio_return),
        'volatility': float(portfolio_volatility),
        'sharpe_ratio': float(sharpe_ratio),
        'n_active': int(n_active),
        'n_effective': float(n_assets_effective)
    }

def compute_var(assets, weights, confidence=0.95, n_simulations=2000):
    """Compute Value at Risk (VaR) and Conditional VaR."""
    n_assets = len(weights)
    
    # Simple VaR calculation using historical simulation
    # Generate scenario returns based on asset correlations
    np.random.seed(123)  # For consistency
    scenario_returns = []
    
    # Use the correlation structure from the assets
    # Create a basic correlation matrix and simulate returns
    corr_matrix = []
    for i, asset1 in enumerate(assets):
        row = []
        for j, asset2 in enumerate(assets):
            # Approximate correlation
            if i == j:
                row.append(1.0)
            elif i < j:
                row.append(0.3)  # Placeholder correlation
            else:
                row.append(corr_matrix[j][i])
        corr_matrix.append(row)
    corr_matrix = np.array(corr_matrix)
    
    # Generate correlated random returns
    for sim in range(n_simulations):
        # Generate correlated random shocks using Cholesky decomposition
        shocks = np.random.multivariate_normal(
            mean=[0] * n_assets,
            cov=corr_matrix * 0.01  # Adjusted for typical daily volatility
        )
        
        # Calculate portfolio return for this scenario
        portfolio_return = 0
        for i, weight in enumerate(weights):
            # Add random shock scaled by asset volatility
            asset_vol = assets[i]['ann_vol'] / np.sqrt(252)  # Daily volatility
            asset_return = shocks[i] * asset_vol
            portfolio_return += weight * asset_return
        
        scenario_returns.append(portfolio_return)
    
    scenario_returns.sort()
    
    # Calculate VaR
    var_idx = int(n_simulations * confidence)
    var_95 = abs(scenario_returns[var_idx]) if var_idx < len(scenario_returns) else 0
    
    # Calculate CVaR (Conditional VaR)
    tail_losses = scenario_returns[var_idx:]
    cvar = abs(sum(tail_losses) / len(tail_losses)) if tail_losses else 0
    
    return {
        'var_95': var_95 * 100,  # Convert to percentage
        'cvar': cvar * 100       # Convert to percentage
    }

def run_benchmark_comparison(assets_data):
    """Run benchmark algorithms for comparison."""
    n = len(assets_data)

    # Convert to numpy arrays
    returns = np.array([a['ann_return'] for a in assets_data])
    vols = np.array([a['ann_vol'] for a in assets_data])
    sharpes = np.array([a['sharpe'] for a in assets_data])

    def calc_metrics(w):
        r = np.dot(w, returns)
        # Simplified correlation matrix for benchmark calculations
        corr_matrix = np.full((n, n), 0.3)  # Average correlation
        np.fill_diagonal(corr_matrix, 1.0)
        # Calculate portfolio variance with correlation
        portfolio_variance = 0
        for i in range(n):
            for j in range(n):
                portfolio_variance += w[i] * w[j] * corr_matrix[i, j] * vols[i] * vols[j]
        vol = np.sqrt(portfolio_variance)
        sharpe = r / vol if vol != 0 else 0
        n_active = int(np.sum(w > 0.005))
        return {
            'weights': [float(x) for x in w],
            'expected_return': float(r),
            'volatility': float(vol),
            'sharpe_ratio': float(sharpe),
            'n_active': n_active
        }

    # Equal weight
    ew = np.ones(n) / n

    # Inverse volatility (min variance approximation)
    inv_vols = 1 / (vols + 1e-8)
    iv = inv_vols / np.sum(inv_vols)

    # Risk parity (equal risk contribution approximation)
    inv_risk = 1 / (vols**2 + 1e-8)
    rp = inv_risk / np.sum(inv_risk)

    # Max Sharpe
    pos_sharpes = np.maximum(sharpes, 0)
    ms = pos_sharpes / np.sum(pos_sharpes) if np.sum(pos_sharpes) > 0 else ew.copy()

    # Hierarchical Risk Parity
    from services.hrp import hrp_weights
    cov_approx = np.outer(vols, vols) * (np.full((n, n), 0.3))
    np.fill_diagonal(cov_approx, vols ** 2)
    hrp_w = hrp_weights(cov_approx)

    return {
        'equal_weight': {"name": "Equal Weight", **calc_metrics(ew)},
        'min_variance': {"name": "Min Variance", **calc_metrics(iv)},
        'risk_parity': {"name": "Risk Parity", **calc_metrics(rp)},
        'max_sharpe': {"name": "Max Sharpe", **calc_metrics(ms)},
        'hrp': {"name": "Hierarchical Risk Parity", **calc_metrics(hrp_w)}
    }

def serialize_numpy(obj):
    """Convert numpy objects to JSON serializable types."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


@app.route('/api/portfolio/optimize', methods=['POST'])
@require_api_key
@limiter.limit("10 per minute")
def optimize_portfolio():
    """Endpoint to run quantum portfolio optimization."""
    try:
        data = request.json
        if not data:
            return error_response('Request body is required', code='BAD_REQUEST', status=400)

        # Prefer production matrix input (returns + covariance), fallback to ticker provider.
        market_payload = load_market_payload(data)
        assets = market_payload.assets
        returns = market_payload.returns
        covariance = market_payload.covariance
        tickers = market_payload.tickers

        # Get optimization parameters
        regime = data.get('regime', 'normal')
        omega = data.get('omega', 0.3)
        evolution_time = data.get('evolutionTime', 10)
        max_weight = data.get('maxWeight', 0.10)
        turnover_limit = data.get('turnoverLimit', 0.20)
        objective = data.get('objective', 'max_sharpe')
        target_return = data.get('targetReturn', None)
        strategy_preset = data.get('strategyPreset', 'balanced')
        constraints = PortfolioConstraints.from_dict(data.get('constraints'))

        # Build config: use preset as base, override with explicit params if provided
        config = get_config_for_preset(strategy_preset)
        if omega is not None:
            config.default_omega = omega
        if evolution_time is not None:
            config.evolution_time = evolution_time
        if max_weight is not None:
            config.max_weight = max_weight
        if turnover_limit is not None:
            config.max_turnover = turnover_limit

        # Run unified optimization (supports max_sharpe, min_variance, target_return, risk_parity)
        asset_names = [a['name'] for a in assets]
        sectors_list = [a['sector'] for a in assets]
        with OPTIMIZATION_LATENCY.labels(objective=objective).time():
            result = run_optimization(
                returns=returns,
                covariance=covariance,
                objective=objective,
                target_return=target_return,
                market_regime=regime,
                strategy_preset=strategy_preset,
                config=config,
                constraints=constraints,
                asset_names=asset_names,
                sectors=sectors_list,
            )

        # Calculate risk metrics
        risk_metrics = compute_var(assets, result.weights)

        # Run benchmarks for comparison
        benchmarks = run_benchmark_comparison(assets)

        # Calculate improvement over best benchmark
        benchmark_sharpes = [
            benchmarks['equal_weight']['sharpe_ratio'],
            benchmarks['min_variance']['sharpe_ratio'],
            benchmarks['risk_parity']['sharpe_ratio'],
            benchmarks['max_sharpe']['sharpe_ratio'],
            benchmarks['hrp']['sharpe_ratio']
        ]
        best_benchmark_sharpe = max(benchmark_sharpes) if benchmark_sharpes else 0
        improvement = float(((result.sharpe_ratio / best_benchmark_sharpe) - 1) * 100 if best_benchmark_sharpe != 0 else 0)

        # Prepare holdings data
        holdings = []
        for i, asset in enumerate(assets):
            weight = float(result.weights[i])
            if weight > 0.005:  # Only include meaningful positions
                holdings.append({
                    'name': asset['name'],
                    'sector': asset['sector'],
                    'weight': weight,
                    'annReturn': float(asset['ann_return']),
                    'annVol': float(asset['ann_vol']),
                    'sharpe': float(asset['sharpe'])
                })

        # Sort holdings by weight
        holdings.sort(key=lambda x: x['weight'], reverse=True)

        # Calculate sector allocation
        sector_allocation = {}
        for holding in holdings:
            sector = holding['sector']
            if sector not in sector_allocation:
                sector_allocation[sector] = 0
            sector_allocation[sector] += holding['weight']

        sector_data = [{'name': k, 'value': round(float(v) * 100, 2)} for k, v in sector_allocation.items()]
        sector_data.sort(key=lambda x: x['value'], reverse=True)

        # Prepare response with explicit conversion of numpy types
        response = {
            'qsw_result': {
                'weights': [float(w) for w in result.weights],
                'sharpe_ratio': float(result.sharpe_ratio),
                'expected_return': float(result.expected_return),
                'volatility': float(result.volatility),
                'n_active': int(np.sum(result.weights > 0.005)),
                'turnover': float(result.turnover)
            },
            'holdings': holdings,
            'sector_allocation': sector_data,
            'risk_metrics': {
                'var_95': float(risk_metrics['var_95']),
                'cvar': float(risk_metrics['cvar'])
            },
            'benchmarks': {
                'equal_weight': {
                    'name': benchmarks['equal_weight']['name'],
                    'weights': [float(w) for w in benchmarks['equal_weight']['weights']],
                    'expected_return': float(benchmarks['equal_weight']['expected_return']),
                    'volatility': float(benchmarks['equal_weight']['volatility']),
                    'sharpe_ratio': float(benchmarks['equal_weight']['sharpe_ratio']),
                    'n_active': int(benchmarks['equal_weight']['n_active'])
                },
                'min_variance': {
                    'name': benchmarks['min_variance']['name'],
                    'weights': [float(w) for w in benchmarks['min_variance']['weights']],
                    'expected_return': float(benchmarks['min_variance']['expected_return']),
                    'volatility': float(benchmarks['min_variance']['volatility']),
                    'sharpe_ratio': float(benchmarks['min_variance']['sharpe_ratio']),
                    'n_active': int(benchmarks['min_variance']['n_active'])
                },
                'risk_parity': {
                    'name': benchmarks['risk_parity']['name'],
                    'weights': [float(w) for w in benchmarks['risk_parity']['weights']],
                    'expected_return': float(benchmarks['risk_parity']['expected_return']),
                    'volatility': float(benchmarks['risk_parity']['volatility']),
                    'sharpe_ratio': float(benchmarks['risk_parity']['sharpe_ratio']),
                    'n_active': int(benchmarks['risk_parity']['n_active'])
                },
                'max_sharpe': {
                    'name': benchmarks['max_sharpe']['name'],
                    'weights': [float(w) for w in benchmarks['max_sharpe']['weights']],
                    'expected_return': float(benchmarks['max_sharpe']['expected_return']),
                    'volatility': float(benchmarks['max_sharpe']['volatility']),
                    'sharpe_ratio': float(benchmarks['max_sharpe']['sharpe_ratio']),
                    'n_active': int(benchmarks['max_sharpe']['n_active'])
                },
                'hrp': {
                    'name': benchmarks['hrp']['name'],
                    'weights': [float(w) for w in benchmarks['hrp']['weights']],
                    'expected_return': float(benchmarks['hrp']['expected_return']),
                    'volatility': float(benchmarks['hrp']['volatility']),
                    'sharpe_ratio': float(benchmarks['hrp']['sharpe_ratio']),
                    'n_active': int(benchmarks['hrp']['n_active'])
                }
            },
            'improvement_over_best': improvement,
            'assets': [{'name': a['name'], 'sector': a['sector'], 'ann_return': float(a['ann_return']), 'ann_vol': float(a['ann_vol']), 'sharpe': float(a['sharpe'])} for a in assets],
            'objective': objective,
            'target_return': target_return,
            'strategy_preset': strategy_preset
        }

        # Include correlation matrix if available
        if tickers:
            # Calculate correlation from covariance
            vols = np.sqrt(np.diag(covariance))
            correlation = covariance / np.outer(vols, vols)
            response['correlation_matrix'] = [[float(c) for c in row] for row in correlation.tolist()]

        log_business_audit(
            action="optimize_run",
            payload=data or {},
            result={
                "sharpe_ratio": response["qsw_result"]["sharpe_ratio"],
                "n_active": response["qsw_result"]["n_active"],
                "source": market_payload.source,
            },
            status=200,
        )

        return success_response(response)

    except ValueError as e:
        return error_response(str(e), code='BAD_REQUEST', status=400)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


def _post_webhook(url: str, body: dict):
    """Best-effort webhook callback."""
    try:
        payload = json.dumps(body).encode("utf-8")
        req = Request(
            url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req, timeout=10):
            pass
    except Exception as exc:
        logger.warning(f"webhook_delivery_failed: {exc}")


def _run_job_endpoint(path: str, payload: dict):
    """Execute existing endpoint logic in-process using Flask test client."""
    with app.test_client() as client:
        headers = {}
        inherited_key = payload.pop("__api_key", None)
        if inherited_key:
            headers["X-API-Key"] = inherited_key
        resp = client.post(path, json=payload, headers=headers)
        data = resp.get_json(silent=True) or {}
        if resp.status_code >= 400:
            err = data.get("error")
            msg = err.get("message", str(err)) if isinstance(err, dict) else (err or f"{path} failed with {resp.status_code}")
            raise ValueError(msg)
        return data.get("data", data)


def _submit_async_job(job_type: str, payload: dict, webhook_url: str = ""):
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _jobs_lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "job_type": job_type,
            "status": "queued",
            "created_at": now,
            "started_at": None,
            "finished_at": None,
            "error": None,
            "result": None,
            "webhook_url": webhook_url or None,
            "tenant_id": getattr(g, "tenant_id", "anonymous"),
        }

    def _runner():
        with _jobs_lock:
            _jobs[job_id]["status"] = "running"
            _jobs[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()
        try:
            if job_type == "optimize":
                result = _run_job_endpoint("/api/portfolio/optimize", dict(payload))
            elif job_type == "backtest":
                result = _run_job_endpoint("/api/portfolio/backtest", dict(payload))
            else:
                raise ValueError(f"Unsupported job type: {job_type}")

            with _jobs_lock:
                _jobs[job_id]["status"] = "completed"
                _jobs[job_id]["result"] = result
                _jobs[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
            log_async_audit(
                tenant_id=_jobs[job_id].get("tenant_id", "anonymous"),
                action=f"{job_type}_job_completed",
                payload=payload,
                result={"job_id": job_id, "status": "completed"},
                status=200,
            )

            if webhook_url:
                _post_webhook(
                    webhook_url,
                    {
                        "job_id": job_id,
                        "status": "completed",
                        "result": result,
                    },
                )
        except Exception as exc:
            with _jobs_lock:
                _jobs[job_id]["status"] = "failed"
                _jobs[job_id]["error"] = str(exc)
                _jobs[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
            log_async_audit(
                tenant_id=_jobs[job_id].get("tenant_id", "anonymous"),
                action=f"{job_type}_job_failed",
                payload=payload,
                result={"job_id": job_id, "status": "failed", "error": str(exc)},
                status=500,
            )
            if webhook_url:
                _post_webhook(
                    webhook_url,
                    {
                        "job_id": job_id,
                        "status": "failed",
                        "error": str(exc),
                    },
                )

    _executor.submit(_runner)
    return _jobs[job_id]


@app.route('/api/portfolio/optimize/batch', methods=['POST'])
@require_api_key
@limiter.limit("3 per minute")
def optimize_portfolio_batch():
    """
    Batch optimization endpoint.
    Body: {"requests":[{...},{...}], "stop_on_error": false}
    """
    data = request.get_json(silent=True) or {}
    reqs = data.get("requests", [])
    stop_on_error = bool(data.get("stop_on_error", False))
    if not isinstance(reqs, list) or len(reqs) == 0:
        return error_response("requests must be a non-empty list", code='BAD_REQUEST', status=400)
    if len(reqs) > 100:
        return error_response("maximum 100 optimization requests per batch", code='BAD_REQUEST', status=400)

    api_key = request.headers.get("X-API-Key", "")
    results = []
    for idx, payload in enumerate(reqs):
        try:
            if not isinstance(payload, dict):
                raise ValueError("each request payload must be an object")
            local_payload = dict(payload)
            if api_key:
                local_payload["__api_key"] = api_key
            result = _run_job_endpoint("/api/portfolio/optimize", local_payload)
            results.append({"index": idx, "status": "ok", "result": result})
        except Exception as exc:
            results.append({"index": idx, "status": "error", "error": str(exc)})
            if stop_on_error:
                break

    return success_response({"count": len(results), "results": results})


@app.route('/api/portfolio/backtest/batch', methods=['POST'])
@require_api_key
@limiter.limit("3 per minute")
def backtest_portfolio_batch():
    """
    Batch backtest endpoint.
    Body: {"requests":[{tickers, start_date, end_date, ...}, ...], "stop_on_error": false}
    Returns: {"count": N, "results": [{"index": 0, "status": "ok"|"error", "result"|"error": ...}, ...]}
    """
    data = request.get_json(silent=True) or {}
    reqs = data.get("requests", [])
    stop_on_error = bool(data.get("stop_on_error", False))
    if not isinstance(reqs, list) or len(reqs) == 0:
        return error_response("requests must be a non-empty list", code='BAD_REQUEST', status=400)
    if len(reqs) > 50:
        return error_response("maximum 50 backtest requests per batch", code='BAD_REQUEST', status=400)

    results = []
    for idx, payload in enumerate(reqs):
        try:
            if not isinstance(payload, dict):
                raise ValueError("each request payload must be an object")
            result = _run_backtest_payload(payload)
            results.append({"index": idx, "status": "ok", "result": result})
        except Exception as exc:
            results.append({"index": idx, "status": "error", "error": str(exc)})
            if stop_on_error:
                break

    return success_response({"count": len(results), "results": results})


@app.route('/api/jobs/optimize', methods=['POST'])
@require_api_key
@limiter.limit("10 per minute")
def submit_optimize_job():
    """Submit optimization job for async execution."""
    data = request.get_json(silent=True) or {}
    payload = data.get("payload", data)
    webhook_url = data.get("webhook_url", "")
    if not isinstance(payload, dict):
        return error_response("payload must be an object", code='BAD_REQUEST', status=400)
    payload["__api_key"] = request.headers.get("X-API-Key", "")
    job = _submit_async_job("optimize", payload, webhook_url)
    return success_response({"job_id": job["job_id"], "status": job["status"]}, status=202)


@app.route('/api/jobs/backtest', methods=['POST'])
@require_api_key
@limiter.limit("10 per minute")
def submit_backtest_job():
    """Submit backtest job for async execution."""
    data = request.get_json(silent=True) or {}
    payload = data.get("payload", data)
    webhook_url = data.get("webhook_url", "")
    if not isinstance(payload, dict):
        return error_response("payload must be an object", code='BAD_REQUEST', status=400)
    payload["__api_key"] = request.headers.get("X-API-Key", "")
    job = _submit_async_job("backtest", payload, webhook_url)
    return success_response({"job_id": job["job_id"], "status": job["status"]}, status=202)


@app.route('/api/jobs/<job_id>', methods=['GET'])
@require_api_key
def get_job_status(job_id):
    """Get async job status and result."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return error_response("job not found", code='NOT_FOUND', status=404)
    if job.get("tenant_id") != getattr(g, "tenant_id", "anonymous"):
        return error_response("forbidden", code='FORBIDDEN', status=403)
    return success_response(job)


def _admin_authorized() -> bool:
    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key:
        return False
    return request.headers.get("X-Admin-Key", "") == admin_key


@app.route('/api/admin/api-keys', methods=['POST'])
@limiter.limit("30 per minute")
def admin_create_api_key():
    """Admin endpoint to create tenant API keys."""
    if not _admin_authorized():
        return error_response("unauthorized", code='UNAUTHORIZED', status=401)
    data = request.get_json(silent=True) or {}
    tenant_id = str(data.get("tenant_id", "")).strip()
    key_name = str(data.get("key_name", "")).strip()
    if not tenant_id:
        return error_response("tenant_id is required", code='BAD_REQUEST', status=400)
    plain_key = _create_api_key(tenant_id=tenant_id, key_name=key_name)
    return success_response({"tenant_id": tenant_id, "key_name": key_name, "api_key": plain_key}, status=201)


@app.route('/api/admin/api-keys', methods=['GET'])
@limiter.limit("60 per minute")
def admin_list_api_keys():
    """Admin endpoint to list tenants and key usage."""
    if not _admin_authorized():
        return error_response("unauthorized", code='UNAUTHORIZED', status=401)
    conn = _db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT tenant_id, key_name, is_active, created_at, last_used_at, usage_count
            FROM api_keys
            ORDER BY created_at DESC
            """
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    return success_response(
        {
            "keys": [
                {
                    "tenant_id": r[0],
                    "key_name": r[1],
                    "is_active": bool(r[2]),
                    "created_at": r[3],
                    "last_used_at": r[4],
                    "usage_count": int(r[5] or 0),
                }
                for r in rows
            ]
        }
    )

@app.route('/api/config/objectives', methods=['GET'])
@require_api_key
def get_objectives():
    """Return available optimization objectives."""
    return success_response({
        'objectives': [
            {'id': 'max_sharpe', 'name': 'Max Sharpe Ratio', 'description': 'Quantum-inspired max risk-adjusted return'},
            {'id': 'min_variance', 'name': 'Min Variance', 'description': 'Minimum volatility portfolio'},
            {'id': 'target_return', 'name': 'Target Return', 'description': 'Minimize variance at target return'},
            {'id': 'risk_parity', 'name': 'Risk Parity', 'description': 'Equal risk contribution per asset'},
            {'id': 'hrp', 'name': 'Hierarchical Risk Parity', 'description': 'López de Prado HRP; robust out-of-sample, no matrix inversion'},
        ]
    })


@app.route('/api/config/constraints', methods=['GET'])
@require_api_key
def get_constraints_schema():
    """Return schema for Phase 2 portfolio constraints."""
    return success_response({
        'sector_limits': {
            'type': 'object',
            'description': 'Max weight per sector, e.g. {"Technology": 0.30, "Finance": 0.25}',
            'example': {'Technology': 0.30}
        },
        'sector_min': {
            'type': 'object',
            'description': 'Min weight per sector',
            'example': {'Healthcare': 0.05}
        },
        'max_sector_weight': {
            'type': 'number',
            'description': 'Global cap for any sector (e.g. 0.40 = 40%)'
        },
        'cardinality': {
            'type': 'integer',
            'description': 'Exact number of positions (top-k heuristic)'
        },
        'min_cardinality': {'type': 'integer', 'description': 'Minimum number of positions'},
        'max_cardinality': {'type': 'integer', 'description': 'Maximum number of positions'},
        'blacklist': {
            'type': 'array',
            'items': {'type': 'string'},
            'description': 'Tickers to exclude'
        },
        'whitelist': {
            'type': 'array',
            'items': {'type': 'string'},
            'description': 'If non-empty, only these tickers allowed'
        },
        'turnover_budget': {'type': 'number', 'description': 'Max turnover per rebalance (e.g. 0.20)'}
    })


@app.route('/api/config/presets', methods=['GET'])
@require_api_key
def get_presets():
    """Return available strategy presets."""
    return success_response({
        'presets': [
            {'id': 'growth', 'name': 'Growth', 'description': 'Higher risk/return, more turnover'},
            {'id': 'income', 'name': 'Income', 'description': 'Lower risk, stability focused'},
            {'id': 'balanced', 'name': 'Balanced', 'description': 'Default middle ground'},
            {'id': 'aggressive', 'name': 'Aggressive', 'description': 'Maximum responsiveness'},
            {'id': 'defensive', 'name': 'Defensive', 'description': 'Minimum variance, low turnover'},
        ]
    })


# ─── Ticker catalog & search ───
_TICKER_CATALOG = [
    {"symbol":"SPY","name":"SPDR S&P 500 ETF","sector":"Broad Market","type":"etf"},
    {"symbol":"QQQ","name":"Invesco Nasdaq 100 ETF","sector":"Broad Market","type":"etf"},
    {"symbol":"DIA","name":"SPDR Dow Jones Industrial ETF","sector":"Broad Market","type":"etf"},
    {"symbol":"IWM","name":"iShares Russell 2000 ETF","sector":"Broad Market","type":"etf"},
    {"symbol":"VTI","name":"Vanguard Total Stock Market ETF","sector":"Broad Market","type":"etf"},
    {"symbol":"VOO","name":"Vanguard S&P 500 ETF","sector":"Broad Market","type":"etf"},
    {"symbol":"VEA","name":"Vanguard FTSE Developed Markets","sector":"International","type":"etf"},
    {"symbol":"VWO","name":"Vanguard FTSE Emerging Markets","sector":"International","type":"etf"},
    {"symbol":"BND","name":"Vanguard Total Bond Market ETF","sector":"Fixed Income","type":"etf"},
    {"symbol":"AGG","name":"iShares Core US Aggregate Bond","sector":"Fixed Income","type":"etf"},
    {"symbol":"TLT","name":"iShares 20+ Year Treasury Bond","sector":"Fixed Income","type":"etf"},
    {"symbol":"GLD","name":"SPDR Gold Shares","sector":"Commodities","type":"etf"},
    {"symbol":"XLK","name":"Technology Select Sector SPDR","sector":"Technology","type":"etf"},
    {"symbol":"XLF","name":"Financial Select Sector SPDR","sector":"Financials","type":"etf"},
    {"symbol":"XLE","name":"Energy Select Sector SPDR","sector":"Energy","type":"etf"},
    {"symbol":"XLV","name":"Health Care Select Sector SPDR","sector":"Healthcare","type":"etf"},
    {"symbol":"AAPL","name":"Apple Inc.","sector":"Technology","type":"stock"},
    {"symbol":"MSFT","name":"Microsoft Corporation","sector":"Technology","type":"stock"},
    {"symbol":"GOOGL","name":"Alphabet Inc.","sector":"Technology","type":"stock"},
    {"symbol":"AMZN","name":"Amazon.com Inc.","sector":"Consumer Disc","type":"stock"},
    {"symbol":"NVDA","name":"NVIDIA Corporation","sector":"Technology","type":"stock"},
    {"symbol":"META","name":"Meta Platforms Inc.","sector":"Communication","type":"stock"},
    {"symbol":"TSLA","name":"Tesla Inc.","sector":"Consumer Disc","type":"stock"},
    {"symbol":"JPM","name":"JPMorgan Chase & Co.","sector":"Financials","type":"stock"},
    {"symbol":"V","name":"Visa Inc.","sector":"Financials","type":"stock"},
    {"symbol":"JNJ","name":"Johnson & Johnson","sector":"Healthcare","type":"stock"},
    {"symbol":"UNH","name":"UnitedHealth Group Inc.","sector":"Healthcare","type":"stock"},
    {"symbol":"HD","name":"Home Depot Inc.","sector":"Consumer Disc","type":"stock"},
    {"symbol":"PG","name":"Procter & Gamble Co.","sector":"Consumer Stpl","type":"stock"},
    {"symbol":"MA","name":"Mastercard Inc.","sector":"Financials","type":"stock"},
    {"symbol":"BAC","name":"Bank of America Corp.","sector":"Financials","type":"stock"},
    {"symbol":"XOM","name":"Exxon Mobil Corporation","sector":"Energy","type":"stock"},
    {"symbol":"CVX","name":"Chevron Corporation","sector":"Energy","type":"stock"},
    {"symbol":"WMT","name":"Walmart Inc.","sector":"Consumer Stpl","type":"stock"},
    {"symbol":"KO","name":"Coca-Cola Company","sector":"Consumer Stpl","type":"stock"},
    {"symbol":"PFE","name":"Pfizer Inc.","sector":"Healthcare","type":"stock"},
    {"symbol":"ABBV","name":"AbbVie Inc.","sector":"Healthcare","type":"stock"},
    {"symbol":"MRK","name":"Merck & Co. Inc.","sector":"Healthcare","type":"stock"},
    {"symbol":"NFLX","name":"Netflix Inc.","sector":"Communication","type":"stock"},
    {"symbol":"DIS","name":"Walt Disney Company","sector":"Communication","type":"stock"},
    {"symbol":"ADBE","name":"Adobe Inc.","sector":"Technology","type":"stock"},
    {"symbol":"CRM","name":"Salesforce Inc.","sector":"Technology","type":"stock"},
    {"symbol":"AMD","name":"Advanced Micro Devices Inc.","sector":"Technology","type":"stock"},
    {"symbol":"INTC","name":"Intel Corporation","sector":"Technology","type":"stock"},
    {"symbol":"CSCO","name":"Cisco Systems Inc.","sector":"Technology","type":"stock"},
    {"symbol":"NKE","name":"Nike Inc.","sector":"Consumer Disc","type":"stock"},
    {"symbol":"PEP","name":"PepsiCo Inc.","sector":"Consumer Stpl","type":"stock"},
    {"symbol":"T","name":"AT&T Inc.","sector":"Communication","type":"stock"},
    {"symbol":"VZ","name":"Verizon Communications Inc.","sector":"Communication","type":"stock"},
    {"symbol":"PYPL","name":"PayPal Holdings Inc.","sector":"Financials","type":"stock"},
]


@app.route('/api/tickers/search', methods=['GET'])
@require_api_key
@limiter.limit("30 per minute")
def search_tickers():
    """
    Search the ticker catalog by query string.
    Query params: q (search query), limit (max results, default 15).
    Returns matches sorted: exact symbol > symbol prefix > name/sector match.
    """
    q = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 15)), 50)
    if not q:
        return success_response({"results": _TICKER_CATALOG[:limit]})

    q_upper = q.upper()
    q_lower = q.lower()
    exact, prefix, name_match = [], [], []
    for entry in _TICKER_CATALOG:
        if entry["symbol"] == q_upper:
            exact.append(entry)
        elif entry["symbol"].startswith(q_upper):
            prefix.append(entry)
        elif q_lower in entry["name"].lower() or q_lower in entry["sector"].lower():
            name_match.append(entry)
    results = (exact + prefix + name_match)[:limit]

    if not results and len(q_upper) <= 10 and q_upper.isalpha():
        results = [{"symbol": q_upper, "name": q_upper, "sector": "Unknown", "type": "custom"}]

    return success_response({"results": results})


@app.route('/api/portfolio/efficient-frontier', methods=['POST'])
@require_api_key
@limiter.limit("10 per minute")
def get_efficient_frontier():
    """Endpoint to compute the efficient frontier."""
    try:
        data = request.json
        if not data:
            return error_response('Request body is required', code='BAD_REQUEST', status=400)

        # Extract parameters
        tickers = data.get('tickers', [])
        start_date = data.get('start_date', None)
        end_date = data.get('end_date', None)
        n_points = data.get('n_points', 15)  # Number of points on the frontier

        # Prefer direct matrix input for production; support ticker fallback.
        if data.get("returns") is not None and data.get("covariance") is not None:
            payload = load_market_payload(data)
            returns = payload.returns
            covariance = payload.covariance
            tickers = payload.tickers
        else:
            if not tickers:
                return error_response('Tickers parameter is required (or provide returns/covariance)', code='BAD_REQUEST', status=400)
            if not start_date or not end_date:
                return error_response('Both start_date and end_date are required', code='BAD_REQUEST', status=400)
            # Validate dates
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return error_response('Invalid date format. Use YYYY-MM-DD.', code='BAD_REQUEST', status=400)
            if start_dt >= end_dt:
                return error_response('Start date must be before end date', code='BAD_REQUEST', status=400)

            # Fetch market data
            market_data = fetch_market_data(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date
            )
            returns = np.array(market_data['returns'])
            covariance = np.array(market_data['covariance'])

        # Calculate efficient frontier using the portfolio optimizer function
        from services.portfolio_optimizer import compute_efficient_frontier
        frontier_points = compute_efficient_frontier(returns, covariance, n_points)
        
        # Calculate min and max possible returns for the range
        min_return = np.min([point['target_return'] for point in frontier_points]) if frontier_points else 0
        max_return = np.max([point['target_return'] for point in frontier_points]) if frontier_points else 0

        return success_response({
            'frontier_points': frontier_points,
            'min_return': float(min_return),
            'max_return': float(max_return),
            'tickers': tickers
        })

    except Exception as e:
        logger.error(f"Efficient frontier endpoint error: {str(e)}", exc_info=True)
        return error_response(f'Internal server error: {str(e)}', code='INTERNAL_ERROR', status=500)


@app.route('/api/health', methods=['GET'])
@limiter.exempt
def health_check():
    """Enhanced health check -- reports status of API and optional dependencies."""
    checks = {'api': 'ok'}
    overall = 'healthy'

    # Check Redis if configured
    redis_host = os.getenv('REDIS_HOST')
    if redis_host:
        try:
            import redis
            r = redis.Redis(host=redis_host, port=int(os.getenv('REDIS_PORT', 6379)), socket_timeout=2)
            r.ping()
            checks['redis'] = 'ok'
        except Exception:
            checks['redis'] = 'unavailable'
            overall = 'degraded'

    # Check DB if configured
    db_url = os.getenv('DATABASE_URL')
    if db_url and 'postgresql' in db_url:
        try:
            import psycopg2
            conn = psycopg2.connect(db_url, connect_timeout=2)
            conn.close()
            checks['database'] = 'ok'
        except Exception:
            checks['database'] = 'unavailable'
            overall = 'degraded'

    return success_response({
        'status': overall,
        'checks': checks,
        'cache_entries': len(_market_data_cache),
        'message': 'Quantum Portfolio Backend is running',
    })


@app.route('/metrics', methods=['GET'])
@limiter.exempt
def prometheus_metrics():
    """Expose Prometheus metrics."""
    from flask import Response
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route('/api/docs/openapi', methods=['GET'])
@limiter.exempt
def openapi_spec():
    """Serve OpenAPI specification document."""
    spec_path = os.path.join(os.path.dirname(__file__), "docs", "openapi.yaml")
    if not os.path.exists(spec_path):
        return error_response("OpenAPI spec not found", code='NOT_FOUND', status=404)
    with open(spec_path, "r", encoding="utf-8") as f:
        content = f.read()
    from flask import Response
    return Response(content, mimetype="application/yaml")


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)