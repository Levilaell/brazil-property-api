# Brazil Property API - Deployment Guide

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git
- Make (optional)

### Local Development
```bash
# Clone repository
git clone https://github.com/yourusername/brazil-property-api.git
cd brazil-property-api

# Copy environment file
cp .env.example .env.development

# Start development environment
docker-compose up -d

# Check health
curl http://localhost:8000/api/v1/health
```

### Production Deployment
```bash
# Set production environment variables
export SECRET_KEY="your-production-secret-key"
export MONGODB_URL="mongodb://user:pass@mongo-host:27017/brazil_property_prod"
export REDIS_URL="redis://redis-host:6379/0"

# Deploy to production
./scripts/deploy.sh production v1.0.0
```

## 📋 Deployment Environments

### Development
- **URL**: http://localhost:8000
- **Database**: Local MongoDB
- **Cache**: Local Redis
- **Monitoring**: Basic logs
- **Command**: `docker-compose up -d`

### Staging
- **URL**: https://staging.brazil-property-api.com
- **Database**: Staging MongoDB cluster
- **Cache**: Staging Redis cluster
- **Monitoring**: Full monitoring stack
- **Command**: `./scripts/deploy.sh staging`

### Production
- **URL**: https://brazil-property-api.com
- **Database**: Production MongoDB cluster
- **Cache**: Production Redis cluster
- **Monitoring**: Full monitoring + alerting
- **Command**: `./scripts/deploy.sh production v1.0.0`

## 🔧 Configuration

### Environment Variables
Copy `.env.example` to your environment-specific file:
- `.env.development` - Local development
- `.env.staging` - Staging environment  
- `.env.production` - Production environment

### Required Variables
```bash
SECRET_KEY=your-secret-key-here
MONGODB_URL=mongodb://user:pass@host:27017/database
REDIS_URL=redis://host:6379/0
```

### Optional Variables
```bash
SENTRY_DSN=https://your-sentry-dsn
SLACK_WEBHOOK_URL=https://hooks.slack.com/your-webhook
NEW_RELIC_LICENSE_KEY=your-new-relic-key
```

## 🐳 Docker Configuration

### Build Arguments
```bash
# Build development image
docker build --target development -t brazil-property-api:dev .

# Build production image
docker build --target production -t brazil-property-api:prod .
```

### Volume Mounts
- `./logs:/app/logs` - Application logs
- `./data:/app/data` - Application data
- `mongodb_data:/data/db` - MongoDB data
- `redis_data:/data` - Redis data

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow
1. **Test**: Run tests, linting, security scans
2. **Build**: Build and push Docker images
3. **Deploy Staging**: Auto-deploy to staging on `develop` branch
4. **Deploy Production**: Manual deploy on release tags

### Manual Deployment
```bash
# Deploy specific version
./scripts/deploy.sh production v1.2.3

# Deploy latest
./scripts/deploy.sh production latest

# Deploy with monitoring
COMPOSE_PROFILES=monitoring ./scripts/deploy.sh production
```

## 📊 Monitoring & Health Checks

### Health Endpoints
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health info
- `GET /api/v1/metrics` - Application metrics
- `GET /api/v1/analytics/overview` - Analytics overview

### Service Health
```bash
# Check all services
docker-compose ps

# Check specific service
docker-compose exec api python -c "
from src.database.mongodb_handler import MongoDBHandler
from src.cache.manager import CacheManager
print('Database:', MongoDBHandler({}).ping())
print('Cache:', CacheManager({}).health_check())
"
```

### Logs
```bash
# View application logs
docker-compose logs -f api

# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f mongodb redis nginx
```

## 🔒 Security

### SSL/TLS Configuration
```bash
# Generate self-signed certificates (development)
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes

# Production: Use Let's Encrypt or commercial certificates
```

### Secrets Management
- Use environment variables for secrets
- Never commit secrets to version control
- Use Docker secrets in production
- Consider external secret management (AWS Secrets Manager, etc.)

### Security Headers
- HTTPS enforced in production
- Security headers via Nginx
- Rate limiting configured
- CORS properly configured

## 🔧 Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check port usage
netstat -tulpn | grep :8000
netstat -tulpn | grep :27017
netstat -tulpn | grep :6379

# Kill processes using ports
sudo lsof -ti:8000 | xargs kill -9
```

#### Database Connection Issues
```bash
# Test MongoDB connection
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"

# Check MongoDB logs
docker-compose logs mongodb
```

#### Cache Issues
```bash
# Test Redis connection
docker-compose exec redis redis-cli ping

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL
```

#### Application Issues
```bash
# Check application logs
docker-compose logs api

# Restart application
docker-compose restart api

# Rebuild and restart
docker-compose up -d --build api
```

### Performance Issues
```bash
# Check resource usage
docker stats

# Check disk space
df -h

# Check memory usage
free -h

# Optimize database
docker-compose exec mongodb mongosh --eval "
db.adminCommand('planCacheClear')
db.properties.reIndex()
"
```

## 📈 Scaling

### Horizontal Scaling
```yaml
# docker-compose.prod.yml
services:
  api:
    deploy:
      replicas: 3
    
  nginx:
    # Load balancer configuration
```

### Database Scaling
- MongoDB replica sets for high availability
- Read replicas for read-heavy workloads
- Sharding for large datasets

### Cache Scaling
- Redis Cluster for high availability
- Redis Sentinel for automatic failover

## 🔄 Backup & Recovery

### Automated Backups
```bash
# Enable backup service
COMPOSE_PROFILES=backup docker-compose up -d

# Manual backup
./scripts/backup.sh
```

### Restore from Backup
```bash
# Restore MongoDB
docker-compose exec mongodb mongorestore --archive=/backup/mongodb_backup.gz --gzip

# Restore Redis
docker-compose exec redis redis-cli --rdb /backup/redis_backup.rdb
```

## 📞 Support

### Getting Help
- Check this documentation
- Review application logs
- Check GitHub Issues
- Contact: support@brazil-property-api.com

### Reporting Issues
1. Check existing issues
2. Provide reproduction steps
3. Include logs and environment info
4. Use issue templates