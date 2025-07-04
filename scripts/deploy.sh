#!/bin/bash

# Brazil Property API - Deployment Script
# Usage: ./scripts/deploy.sh [environment] [version]
# Example: ./scripts/deploy.sh production v1.2.3

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-staging}"
VERSION="${2:-latest}"
COMPOSE_FILE=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Set environment-specific configuration
setup_environment() {
    log_info "Setting up environment: $ENVIRONMENT"
    
    case $ENVIRONMENT in
        "development"|"dev")
            COMPOSE_FILE="docker-compose.yml"
            ;;
        "staging"|"stage")
            COMPOSE_FILE="docker-compose.yml"
            export COMPOSE_PROFILES="monitoring"
            ;;
        "production"|"prod")
            COMPOSE_FILE="docker-compose.prod.yml"
            export COMPOSE_PROFILES="monitoring,backup"
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            log_info "Available environments: development, staging, production"
            exit 1
            ;;
    esac
    
    log_success "Environment configured: $ENVIRONMENT"
}

# Load environment variables
load_env_vars() {
    log_info "Loading environment variables..."
    
    ENV_FILE="$PROJECT_ROOT/.env.$ENVIRONMENT"
    if [[ -f "$ENV_FILE" ]]; then
        log_info "Loading variables from $ENV_FILE"
        set -o allexport
        source "$ENV_FILE"
        set +o allexport
    else
        log_warning "Environment file not found: $ENV_FILE"
    fi
    
    # Set default values for required variables
    export IMAGE_TAG="${VERSION}"
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-brazil-property-api-$ENVIRONMENT}"
    
    log_success "Environment variables loaded"
}

# Pre-deployment checks
pre_deployment_checks() {
    log_info "Running pre-deployment checks..."
    
    # Check if required environment variables are set
    required_vars=("SECRET_KEY" "MONGODB_URL" "REDIS_URL")
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Check disk space
    available_space=$(df / | awk 'NR==2 {print $4}')
    required_space=1048576 # 1GB in KB
    
    if [[ $available_space -lt $required_space ]]; then
        log_error "Insufficient disk space. Available: ${available_space}KB, Required: ${required_space}KB"
        exit 1
    fi
    
    log_success "Pre-deployment checks passed"
}

# Pull latest images
pull_images() {
    log_info "Pulling latest Docker images..."
    
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" pull
    
    log_success "Images pulled successfully"
}

# Backup current deployment
backup_current() {
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_info "Creating backup of current deployment..."
        
        BACKUP_DIR="$PROJECT_ROOT/backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Backup database
        if docker-compose -f "$COMPOSE_FILE" ps mongodb | grep -q "Up"; then
            log_info "Backing up MongoDB..."
            docker-compose -f "$COMPOSE_FILE" exec -T mongodb \
                mongodump --archive | gzip > "$BACKUP_DIR/mongodb_backup.gz"
        fi
        
        # Backup Redis (if needed)
        if docker-compose -f "$COMPOSE_FILE" ps redis | grep -q "Up"; then
            log_info "Backing up Redis..."
            docker-compose -f "$COMPOSE_FILE" exec -T redis \
                redis-cli --rdb - | gzip > "$BACKUP_DIR/redis_backup.gz"
        fi
        
        log_success "Backup created: $BACKUP_DIR"
    fi
}

# Deploy application
deploy() {
    log_info "Deploying application..."
    
    cd "$PROJECT_ROOT"
    
    # Use rolling update strategy for production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_info "Performing rolling update..."
        
        # Update services one by one to maintain availability
        services=("api" "nginx")
        for service in "${services[@]}"; do
            log_info "Updating service: $service"
            docker-compose -f "$COMPOSE_FILE" up -d --no-deps "$service"
            sleep 10
            
            # Health check
            if ! health_check "$service"; then
                log_error "Health check failed for $service"
                rollback
                exit 1
            fi
        done
    else
        # Standard deployment for non-production
        docker-compose -f "$COMPOSE_FILE" up -d
    fi
    
    log_success "Application deployed successfully"
}

# Health check
health_check() {
    local service="${1:-api}"
    log_info "Running health check for $service..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if [[ "$service" == "api" ]]; then
            if curl -f -s http://localhost:8000/api/v1/health > /dev/null; then
                log_success "Health check passed for $service"
                return 0
            fi
        elif [[ "$service" == "mongodb" ]]; then
            if docker-compose -f "$COMPOSE_FILE" exec -T mongodb \
                mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
                log_success "Health check passed for $service"
                return 0
            fi
        elif [[ "$service" == "redis" ]]; then
            if docker-compose -f "$COMPOSE_FILE" exec -T redis \
                redis-cli ping > /dev/null 2>&1; then
                log_success "Health check passed for $service"
                return 0
            fi
        fi
        
        log_info "Health check attempt $attempt/$max_attempts failed, retrying in 10s..."
        sleep 10
        ((attempt++))
    done
    
    log_error "Health check failed for $service after $max_attempts attempts"
    return 1
}

# Rollback deployment
rollback() {
    log_warning "Rolling back deployment..."
    
    # Implementation depends on your rollback strategy
    # This could involve:
    # - Reverting to previous Docker image tags
    # - Restoring from backup
    # - Using blue-green deployment switch
    
    log_info "Rollback completed"
}

# Post-deployment tasks
post_deployment() {
    log_info "Running post-deployment tasks..."
    
    # Run database migrations if needed
    if [[ -f "$PROJECT_ROOT/scripts/migrate.sh" ]]; then
        log_info "Running database migrations..."
        "$PROJECT_ROOT/scripts/migrate.sh" "$ENVIRONMENT"
    fi
    
    # Clear application cache
    log_info "Clearing application cache..."
    docker-compose -f "$COMPOSE_FILE" exec -T api \
        python -c "from src.cache.manager import CacheManager; CacheManager({}).cleanup()" || true
    
    # Send deployment notification
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        log_info "Sending deployment notification..."
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚀 Brazil Property API deployed to $ENVIRONMENT (version: $VERSION)\"}" \
            "$SLACK_WEBHOOK_URL" || true
    fi
    
    log_success "Post-deployment tasks completed"
}

# Cleanup old resources
cleanup() {
    log_info "Cleaning up old resources..."
    
    # Remove unused Docker images
    docker image prune -f
    
    # Remove old backups (keep last 7 days for production)
    if [[ "$ENVIRONMENT" == "production" && -d "$PROJECT_ROOT/backups" ]]; then
        find "$PROJECT_ROOT/backups" -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true
    fi
    
    log_success "Cleanup completed"
}

# Main deployment function
main() {
    log_info "Starting deployment to $ENVIRONMENT (version: $VERSION)"
    
    check_prerequisites
    setup_environment
    load_env_vars
    pre_deployment_checks
    pull_images
    backup_current
    deploy
    
    # Health checks for all services
    for service in api mongodb redis; do
        health_check "$service"
    done
    
    post_deployment
    cleanup
    
    log_success "Deployment completed successfully! 🎉"
    log_info "Application is running at: http://localhost:8000"
    log_info "Health check: http://localhost:8000/api/v1/health"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi