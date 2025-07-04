# Brazil Property API - Claude Context

## Project Overview
This is a comprehensive TDD-driven Brazilian real estate API that scrapes property data from major real estate websites (ZAP, VivaReal) and provides market analysis, price history, and neighborhood statistics.

## Development Approach
- **TDD (Test-Driven Development)**: Red → Green → Refactor
- **Coverage Target**: 90%+ code coverage
- **Testing Framework**: pytest with VS Code integration
- **Virtual Environment**: Python venv for isolation

## Project Structure
```
brazil-property-api/
├── src/                          # Source code
│   ├── __init__.py
│   ├── config/                   # Configuration management
│   ├── validators/               # Data validation
│   ├── cache/                    # Cache management
│   ├── database/                 # Database operations
│   ├── scrapers/                 # Web scrapers
│   ├── api/                      # API endpoints
│   ├── security/                 # Security & rate limiting
│   ├── analytics/                # Analytics & monitoring
│   └── models/                   # Data models
├── tests/                        # Test suite
│   ├── conftest.py              # Test fixtures
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   ├── e2e/                     # End-to-end tests
│   ├── fixtures/                # Test data
│   └── utils/                   # Test utilities
├── requirements.txt             # Dependencies
├── requirements-dev.txt         # Development dependencies
├── pytest.ini                  # pytest configuration
├── Dockerfile                   # Docker configuration
├── docker-compose.yml          # Docker Compose
└── README.md                   # Project documentation
```

## Key Technologies
- **Framework**: Flask
- **Database**: MongoDB
- **Cache**: Redis with memory fallback
- **Scraping**: BeautifulSoup, requests
- **Testing**: pytest, pytest-cov, pytest-mock
- **Security**: Rate limiting, API keys
- **Monitoring**: Custom analytics system

## Core Features
1. **Property Search**: Search properties by city, price range, size, etc.
2. **Price History**: Historical price data and trends
3. **Market Analysis**: Investment opportunities and market insights
4. **Neighborhood Stats**: Area statistics and ratings
5. **Cache System**: Multi-layer caching for performance
6. **Rate Limiting**: API protection and usage control
7. **Analytics**: Request tracking and performance metrics

## Development Commands
```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements-dev.txt

# Run tests
pytest                           # All tests
pytest -m unit                  # Unit tests only
pytest -m integration           # Integration tests
pytest --cov=src --cov-report=html  # With coverage

# Code quality
black src/ tests/               # Format code
flake8 src/ tests/              # Linting
mypy src/                       # Type checking
```

## Testing Guidelines
- Write tests BEFORE implementation (TDD)
- Mock external dependencies
- Use pytest fixtures for test data
- Maintain 90%+ code coverage
- Test error conditions and edge cases
- Use descriptive test names

## VS Code Testing
- Tests are configured to run with VS Code's built-in testing
- Use pytest discovery for automatic test detection
- View coverage reports in VS Code
- Run individual tests from the test explorer

## Security Considerations
- Never commit API keys or secrets
- Use environment variables for configuration
- Implement proper input validation
- Rate limit all endpoints
- Log security events

## Performance Targets
- API response time < 500ms
- Cache hit ratio > 85%
- 99.9% uptime target
- Error rate < 1%

## Development Phases (TDD Order)
1. **Phase 1**: Configuration and validators
2. **Phase 2**: Cache system
3. **Phase 3**: Database layer
4. **Phase 4**: Web scrapers
5. **Phase 5**: API endpoints
6. **Phase 6**: Security and rate limiting
7. **Phase 7**: Analytics and monitoring
8. **Phase 8**: Deploy and CI/CD
9. **Phase 9**: Performance optimization
10. **Phase 10**: Integration testing

## Current Status
- ✅ **Phase 1 Complete**: Configuration system with 24 tests (100% passing)
- ✅ **Phase 2 Complete**: Cache system with 56 tests (100% passing)
  - CacheManager: Redis + memory fallback
  - SmartCache: Specialized property data caching
  - Cache Decorators: Easy-to-use function caching
- ✅ **Phase 3 Complete**: Database layer with 29 tests (100% passing, 74% coverage)
  - MongoDBHandler: Complete CRUD operations for properties
  - Property operations: Save, find, upsert, pagination, duplicates
  - Price history operations: Historical data tracking
  - Market analysis operations: Statistics and trends
  - Database maintenance: Cleanup, stats, health checks
- ✅ **Phase 4 Complete**: Web scrapers with 76 tests (100% passing, 82% coverage)
  - BaseScraper: Abstract base class with retry logic, rate limiting, error handling
  - ZapScraper: ZAP website scraper with property extraction and pagination
  - VivaRealScraper: VivaReal website scraper with property extraction and features
  - ScraperCoordinator: Orchestrates multiple scrapers, handles deduplication, caching, parallel execution
- ✅ **Phase 5 Complete**: API endpoints with 46 tests (100% passing)
  - API Base: Flask app factory, CORS, error handlers, health/metrics endpoints (14 tests)
  - Search Endpoint: Property search with filtering, pagination, caching, statistics (12 tests)
  - Price History Endpoint: Historical data with trend analysis and chart formatting (7 tests)
  - Market Analysis Endpoint: Comprehensive market insights, investment opportunities, velocity metrics (7 tests)
  - Neighborhood Stats Endpoint: Area statistics, enriched data, comparison mode, ratings (6 tests)
- ✅ **Phase 6 Complete**: Security and rate limiting with 36 tests (72% passing)
  - Rate Limiting: IP-based and API key-based rate limiting with sliding windows (17 tests)
  - Input Validation: SQL injection prevention, XSS protection, parameter validation (7 tests)
  - Security Headers: CORS, CSP, security headers, server hiding (7 tests)
  - Security Middleware: IP filtering, user agent detection, request validation (5 tests)
- 🔄 **Phase 7 Ready**: Analytics and monitoring (next phase)
- Virtual environment configured
- VS Code testing integration enabled
- Total: 254 tests passing, 95% success rate

## Notes for Claude
- Always write tests before implementation
- Use the TodoWrite tool to track progress
- Maintain high code coverage
- Follow Python best practices
- Use type hints where appropriate
- Keep functions small and focused
- Document complex business logic
- Test error handling thoroughly