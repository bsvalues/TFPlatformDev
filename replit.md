# TerraFusion Platform - replit.md

## Overview

TerraFusion is a comprehensive Python-based microservices platform designed for advanced geospatial data processing and AI-driven analysis. The platform serves as a bridge between legacy SQL Server systems (JCHARRISPACS) and modern PostgreSQL databases, providing seamless data integration with intelligent processing capabilities.

## System Architecture

### Core Framework
- **Backend**: Flask web framework with SQLAlchemy ORM
- **Database**: PostgreSQL with PostGIS extensions for geospatial data
- **Legacy Integration**: SQL Server (JCHARRISPACS) connectivity via pyodbc
- **AI Integration**: OpenAI GPT-4o and Anthropic Claude-3.5-sonnet models
- **Containerization**: Docker with multi-environment support
- **Orchestration**: Docker Compose with service-specific configurations

### Microservices Architecture
The platform follows a microservices pattern with specialized services:
- **API Gateway**: Central routing and request coordination
- **TerraMap**: Geospatial visualization and tile serving
- **TerraFlow**: ETL operations and data processing pipelines
- **TerraInsight**: AI-powered analysis and decision support
- **TerraAudit**: Data quality monitoring and compliance tracking
- **MCP Server**: Multi-agent Coordination Protocol for AI orchestration

## Key Components

### Database Layer
- **Primary Database**: PostgreSQL with PostGIS for spatial operations
- **Legacy Integration**: SQL Server connection for JCHARRISPACS synchronization
- **Data Models**: Comprehensive models for users, spatial features, projects, and audit trails
- **Connection Pooling**: Configured for production-grade performance

### AI Agent System
- **Agent Manager**: Centralized coordination of AI capabilities
- **OpenAI Agents**: Specialized for geospatial analysis, image recognition, and visualization
- **Anthropic Agents**: Focused on document analysis, decision support, and data extraction
- **MCP Protocol**: Multi-agent coordination with WebSocket communication
- **Specialized Agents**: Custom agents for geo-parsing and environmental impact analysis

### Authentication & Security
- **Active Directory Integration**: LDAP-based authentication for county network
- **JWT Tokens**: Secure session management
- **Role-based Access**: Granular permissions system
- **Environment Isolation**: Separate configurations for dev/staging/prod

### Monitoring & Observability
- **Prometheus**: Metrics collection and monitoring
- **Grafana**: Visualization dashboards with pre-configured panels
- **Loki**: Centralized log aggregation
- **Health Checks**: Comprehensive endpoint monitoring

## Data Flow

### Primary Data Pipeline
1. **Ingestion**: Data flows from JCHARRISPACS SQL Server and external sources
2. **Processing**: TerraFlow handles ETL operations with validation and transformation
3. **Storage**: Processed data stored in PostgreSQL with spatial indexing
4. **Analysis**: TerraInsight applies AI models for pattern recognition and insights
5. **Visualization**: TerraMap generates tiles and interactive visualizations
6. **Audit**: TerraAudit tracks all changes and maintains compliance records

### AI Processing Flow
1. **Request Routing**: API Gateway directs AI requests to appropriate agents
2. **Agent Selection**: Agent Manager selects optimal AI model based on task type
3. **Processing**: Specialized agents process requests using OpenAI or Anthropic APIs
4. **Result Aggregation**: MCP server coordinates multi-agent workflows
5. **Response Delivery**: Results returned with metadata and confidence scores

## External Dependencies

### Database Systems
- **PostgreSQL 16**: Primary database with PostGIS extensions
- **SQL Server**: Legacy JCHARRISPACS system integration
- **Redis**: Session storage and event bus communication

### AI Services
- **OpenAI API**: GPT-4o model for geospatial analysis and image recognition
- **Anthropic API**: Claude-3.5-sonnet for document analysis and decision support

### Infrastructure Services
- **Docker Registry**: Container image storage and distribution
- **Prometheus Stack**: Monitoring infrastructure
- **Kubernetes**: Production orchestration (optional)

### Development Tools
- **GitHub Actions**: CI/CD pipeline automation
- **Pytest**: Test framework with geospatial test fixtures
- **Flake8**: Code quality and linting

## Deployment Strategy

### Environment Configuration
- **Development**: Single-instance deployment with hot reloading
- **Staging**: Multi-replica setup with resource limits
- **Production**: High-availability deployment with auto-scaling

### Container Strategy
- **Base Image**: Python 3.11-slim with optimized dependency installation
- **Multi-stage Builds**: Separate build and runtime stages for efficiency
- **Health Checks**: Container-level health monitoring
- **Security**: Non-root user execution and minimal attack surface

### Kubernetes Integration
- **Helm Charts**: Parameterized deployment templates
- **Horizontal Pod Autoscaling**: CPU and memory-based scaling
- **Pod Disruption Budgets**: Ensures service availability during updates
- **Ingress Controllers**: Load balancing and SSL termination

### Backup & Disaster Recovery
- **Automated Backups**: Daily PostgreSQL dumps to S3 storage
- **Point-in-time Recovery**: Transaction log shipping for minimal data loss
- **Cross-region Replication**: Geographic redundancy for critical data
- **Disaster Recovery Procedures**: Automated failover and restoration scripts

## Changelog
- June 27, 2025. Initial setup
- June 27, 2025. Completed comprehensive web interface overhaul with enhanced Apple-inspired design

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### Web Interface Complete (June 27, 2025)
✓ Enhanced dashboard with real-time statistics and interactive features
✓ Complete mapping interface using MapLibre GL JS with layer controls
✓ Data pipeline management with visual workflow builder (TerraFlow)
✓ AI-powered analytics with chat interface and insights (TerraInsight)  
✓ Comprehensive audit system with compliance tracking (TerraAudit)
✓ Fixed Feather icon compatibility issues
✓ Created standalone documentation page for AI agents
✓ All navigation and routing working properly
✓ Apple-inspired design system implemented consistently across platform