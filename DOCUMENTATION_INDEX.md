# Quantum Hybrid Portfolio — Documentation Index

This is the master index for all Quantum Hybrid Portfolio documentation.

## 📖 Getting Started

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Project overview, quick start, and features |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Installation and setup guide |
| [docs/DASHBOARD_GUIDE.md](docs/DASHBOARD_GUIDE.md) | Dashboard user guide |
| [.env.example](.env.example) | Environment variable reference |

## 🏗️ Architecture & Design

| Document | Description |
|----------|-------------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture and data flow |
| [docs/TECHNICAL_PAPER.md](docs/TECHNICAL_PAPER.md) | Technical background and research |
| [DIRECTORY_GUIDE.md](DIRECTORY_GUIDE.md) | Project directory structure |

## 📡 API Documentation

| Document | Description |
|----------|-------------|
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | Complete API endpoint reference |
| [docs/API_PRODUCT_GUIDE.md](docs/API_PRODUCT_GUIDE.md) | API usage patterns and best practices |
| `/api/docs/openapi` | OpenAPI/Swagger spec (when API is running) |

## 📊 Dashboard Documentation

| Document | Description |
|----------|-------------|
| [DASHBOARD_README.md](DASHBOARD_README.md) | Dashboard features overview |
| [DASHBOARD_FEATURE_SUMMARY.md](DASHBOARD_FEATURE_SUMMARY.md) | Feature summary |
| [DASHBOARD_FEATURE_GUIDE.md](DASHBOARD_FEATURE_GUIDE.md) | Feature guide |
| [DASHBOARD_CUSTOMIZATION_FEATURES.md](DASHBOARD_CUSTOMIZATION_FEATURES.md) | Customization options |
| [DASHBOARD_FULL_README.md](DASHBOARD_FULL_README.md) | Complete dashboard documentation |
| [DASHBOARD_VISUAL_GUIDE.md](DASHBOARD_VISUAL_GUIDE.md) | Visual guide |
| [DASHBOARD_WALKTHROUGH_REPORT.md](DASHBOARD_WALKTHROUGH_REPORT.md) | Walkthrough report |
| [DASHBOARD_TEST_SUMMARY.md](DASHBOARD_TEST_SUMMARY.md) | Test summary |

## 🧪 Examples & Tutorials

| File | Description |
|------|-------------|
| [examples/basic_qsw_example.py](examples/basic_qsw_example.py) | Basic QSW optimization |
| [examples/advanced_quantum_methods.py](examples/advanced_quantum_methods.py) | Advanced quantum techniques |
| [examples/quantum_integration_example.py](examples/quantum_integration_example.py) | Full integration example |

## 🚀 Deployment

| Document | Description |
|----------|-------------|
| [docs/HUGGINGFACE_SPACES.md](docs/HUGGINGFACE_SPACES.md) | Deploy to Hugging Face Spaces |
| [deploy_production.sh](deploy_production.sh) | Production deployment script |
| [deploy_hf_spaces.sh](deploy_hf_spaces.sh) | HF Spaces deployment script |
| [docker-compose.yml](docker-compose.yml) | Docker Compose configuration |

## 🧭 Development

| Document | Description |
|----------|-------------|
| [docs/NEXT_STEPS.md](docs/NEXT_STEPS.md) | Development roadmap and tasks |
| [demo_dashboard_features.sh](demo_dashboard_features.sh) | Dashboard feature demo script |

## 🧪 Testing

| File | Description |
|------|-------------|
| [tests/test_api_integration.py](tests/test_api_integration.py) | API integration tests |
| [tests/test_api.py](tests/test_api.py) | API unit tests |
| [tests/test_api_productization.py](tests/test_api_productization.py) | API productization tests |
| [tests/test_braket_backend.py](tests/test_braket_backend.py) | Braket backend tests |

## 📋 Configuration Reference

### Environment Variables

See [`.env.example`](.env.example) for all available variables:

| Category | Variables |
|----------|-----------|
| **Application** | `FLASK_ENV`, `LOG_LEVEL`, `PORT` |
| **Security** | `SECRET_KEY`, `JWT_SECRET_KEY`, `API_KEY`, `ADMIN_API_KEY` |
| **Database** | `DATABASE_URL`, `DB_PASSWORD` |
| **Redis** | `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` |
| **Rate Limiting** | `RATELIMIT_ENABLED`, `MAX_REQUESTS_PER_MINUTE` |
| **Portfolio** | `MAX_ASSETS`, `MAX_EVOLUTION_TIME`, `QUANTUM_COMPUTE_TIMEOUT` |
| **Market Data** | `YFINANCE_RATE_LIMIT`, `YFINANCE_TIMEOUT` |
| **AWS Braket** | `AWS_REGION`, `BRAKET_DEVICE_ARN` |
| **Caching** | `CACHE_TTL` |
| **CORS** | `CORS_ORIGINS` |
| **Monitoring** | `SENTRY_DSN` |
| **Jobs** | `JOB_WORKERS` |

### QSW Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `default_omega` | 0.3 | Coupling strength |
| `evolution_time` | 10 | Evolution duration |
| `max_turnover` | 0.15 | Maximum portfolio turnover |
| `stability_blend_factor` | 0.7 | Stability vs optimization blend |
| `max_weight` | 0.10 | Maximum weight per asset |
| `min_weight` | 0.01 | Minimum weight per asset |

## 📚 Research & Citations

### Key Papers

- **Chang et al. (2025)** — Quantum Stochastic Walks for portfolio optimization
- **López de Prado (2016)** — Hierarchical Risk Parity (SSRN 2708678)
- **Farhi et al. (2014)** — Quantum Approximate Optimization Algorithm (QAOA)
- **Peruzzo et al. (2014)** — Variational Quantum Eigensolver (VQE)

### Citing This Project

```bibtex
@software{quantum_hybrid_portfolio,
  author = {Quantum Global Group},
  title = {Quantum Hybrid Portfolio: Quantum-Inspired Optimization},
  year = {2026},
  url = {https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio}
}
```

## 🔗 External Resources

- [AWS Braket Documentation](https://docs.aws.amazon.com/braket/)
- [yfinance Documentation](https://pypi.org/project/yfinance/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [React Documentation](https://react.dev/)

## 📞 Support

- **GitHub Issues:** [Report bugs or request features](https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio/issues)
- **API Health:** `GET /api/health` when running the API
- **Metrics:** `GET /metrics` for Prometheus metrics

---

*Last updated: March 2026*
