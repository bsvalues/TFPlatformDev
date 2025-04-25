# TerraFusion Platform

A cutting-edge Python-based microservices platform for advanced geospatial data processing and intelligent AI-driven analysis.

## Core Technologies

- Flask web framework
- PostgreSQL database with SQLAlchemy ORM
- Multi-agent AI architecture
- OpenAI and Anthropic AI integrations
- Advanced geospatial data processing and visualization
- Docker containerization and orchestration
- Prometheus and Grafana monitoring

## Services Architecture

TerraFusion is built as a set of specialized microservices:

- **API Gateway**: Central routing point for all services
- **TerraMap**: Geospatial visualization service
- **TerraFlow**: ETL and data processing service
- **TerraInsight**: AI-driven analysis service
- **TerraAudit**: Data quality and auditing service
- **MCP (Multi-agent Coordination Protocol)**: AI agent orchestration

## DevOps Components

### Containerization

- `Dockerfile`: Application containerization
- `docker-compose.yml`: Service orchestration
- Environment-specific configurations: `docker-compose.dev.yml`, `docker-compose.staging.yml`, `docker-compose.prod.yml`

### Continuous Integration/Deployment

- GitHub Actions workflow: `.github/workflows/main.yml`
- Test, build, and deployment pipeline
- Automated testing with pytest and flake8

### Monitoring and Observability

- Prometheus metrics integration
- Grafana dashboards
- Loki for log aggregation
- Health check endpoints

### Database Management

- Database backup script: `scripts/backup.sh`
- Database restore script: `scripts/restore.sh`
- PostgreSQL connection pooling and health monitoring

### Deployment Automation

- Deployment script: `scripts/deploy.sh`
- Environment-specific deployments
- Zero-downtime deployment for production

## Getting Started

### Prerequisites

- Docker and Docker Compose
- PostgreSQL database
- OpenAI and Anthropic API keys

### Environment Variables

The following environment variables are required:

- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: API key for OpenAI services
- `ANTHROPIC_API_KEY`: API key for Anthropic services
- `SESSION_SECRET`: Secret key for Flask sessions

### Running the Application

1. Clone the repository
2. Set up environment variables
3. Run with Docker Compose:

```bash
docker-compose up -d
```

For development:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Monitoring

Access the monitoring dashboard at:

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## License

Copyright (c) 2025 TerraFusion Team - All Rights Reserved