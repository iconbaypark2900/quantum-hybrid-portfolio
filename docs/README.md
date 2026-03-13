# Quantum Hybrid Portfolio — Documentation Index

Welcome to the Quantum Hybrid Portfolio documentation. This directory contains comprehensive guides for using, understanding, and extending the system.

## Quick Links

| Document | Purpose |
|----------|---------|
| [GETTING_STARTED.md](GETTING_STARTED.md) | Installation and first steps |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture and data flow |
| [API_REFERENCE.md](API_REFERENCE.md) | Complete API documentation |
| [API_PRODUCT_GUIDE.md](API_PRODUCT_GUIDE.md) | API usage patterns and best practices |
| [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) | Dashboard user guide |
| [TECHNICAL_PAPER.md](TECHNICAL_PAPER.md) | Technical background and research |
| [HUGGINGFACE_SPACES.md](HUGGINGFACE_SPACES.md) | Deploying to Hugging Face Spaces |
| [NEXT_STEPS.md](NEXT_STEPS.md) | Development roadmap and tasks |

## Getting Started

New to the project? Start here:

1. **[GETTING_STARTED.md](GETTING_STARTED.md)** — Installation, configuration, and running your first optimization
2. **[DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md)** — Learn to use the interactive dashboard
3. **[examples/](../examples/)** — Run code examples to understand the API

## API Documentation

### Reference

- **[API_REFERENCE.md](API_REFERENCE.md)** — Complete endpoint documentation with request/response examples
- **OpenAPI Spec** — Available at `http://localhost:5000/api/docs/openapi` when running the API

### Usage Guide

- **[API_PRODUCT_GUIDE.md](API_PRODUCT_GUIDE.md)** — Patterns for integrating the API into your applications
- Authentication, rate limiting, caching strategies
- Error handling and best practices

## Architecture

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — High-level system architecture
- Data flow diagrams
- Component descriptions
- Deployment options

## Technical Background

- **[TECHNICAL_PAPER.md](TECHNICAL_PAPER.md)** — Quantum algorithms explained
  - Quantum Stochastic Walks (QSW)
  - Quantum Annealing and QUBO
  - QAOA and VQE
  - Performance benchmarks

## Dashboard

- **[DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md)** — User guide for the React dashboard
- **[../DASHBOARD_README.md](../DASHBOARD_README.md)** — Dashboard features and customization
- **[../DASHBOARD_FEATURE_SUMMARY.md](../DASHBOARD_FEATURE_SUMMARY.md)** — Feature overview

## Deployment

- **[HUGGINGFACE_SPACES.md](HUGGINGFACE_SPACES.md)** — Deploy to Hugging Face Spaces
- **[../docker-compose.yml](../docker-compose.yml)** — Docker Compose configuration
- **[../deploy_production.sh](../deploy_production.sh)** — Production deployment script

## Development

### Roadmap

- **[NEXT_STEPS.md](NEXT_STEPS.md)** — Current development priorities and tasks

### Project Structure

```
docs/
├── README.md                 # This file
├── GETTING_STARTED.md        # Installation guide
├── ARCHITECTURE.md           # System architecture
├── API_REFERENCE.md          # API documentation
├── API_PRODUCT_GUIDE.md      # API usage guide
├── DASHBOARD_GUIDE.md        # Dashboard user guide
├── TECHNICAL_PAPER.md        # Technical background
├── HUGGINGFACE_SPACES.md     # HF Spaces deployment
└── NEXT_STEPS.md             # Development roadmap
```

### Related Documentation

- **[../DIRECTORY_GUIDE.md](../DIRECTORY_GUIDE.md)** — Project directory structure
- **[../DASHBOARD_CUSTOMIZATION_FEATURES.md](../DASHBOARD_CUSTOMIZATION_FEATURES.md)** — Dashboard customization
- **[../.env.example](../.env.example)** — Environment variable reference

## Examples

The `examples/` directory contains working code:

- **basic_qsw_example.py** — Basic QSW optimization
- **advanced_quantum_methods.py** — Advanced quantum techniques
- **quantum_integration_example.py** — Quantum integration patterns (to be restored)

## Testing

```bash
# Run all tests
pytest tests/

# Run integration tests
pytest tests/test_api_integration.py

# Run with coverage
pytest --cov=core --cov=services --cov=api tests/
```

## Support

- **GitHub Issues:** [Report bugs or request features](https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio/issues)
- **Documentation:** Browse this directory or the root `README.md`
- **API Health:** `GET /api/health` when running the API

## Contributing

We welcome contributions! See the root [README.md](../README.md) for contribution guidelines.

## License

MIT License — see [../LICENSE](../LICENSE) for details.
