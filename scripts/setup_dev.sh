#!/bin/bash
# Development environment setup script for TerraFusion Platform
# This script sets up a development environment for new team members

set -e

echo "Setting up development environment for TerraFusion Platform"

# Check for required tools
echo "Checking for required tools..."

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed"
    echo "Please install Python 3.11 or later"
    exit 1
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check for Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check for Git
if ! command -v git &> /dev/null; then
    echo "Git is not installed"
    echo "Please install Git: https://git-scm.com/downloads"
    exit 1
fi

echo "All required tools are installed"

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Set up environment variables
echo "Setting up environment variables..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from example template"
    echo "Please edit .env file with your credentials"
else
    echo ".env file already exists"
fi

# Create database if not exists
echo "Setting up database..."
if [ -z "$PGPASSWORD" ]; then
    # Source the .env file if PGPASSWORD is not set
    if [ -f .env ]; then
        source .env
    fi
fi

# Check if PostgreSQL is running in Docker
POSTGRES_RUNNING=$(docker ps -q -f name=postgres)
if [ -z "$POSTGRES_RUNNING" ]; then
    echo "Starting PostgreSQL container..."
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres
    echo "Waiting for PostgreSQL to start..."
    sleep 10
fi

# Check if database exists
if PGPASSWORD=$PGPASSWORD psql -h ${PGHOST:-localhost} -U ${PGUSER:-postgres} -c '\l' | grep -q ${PGDATABASE:-terrafusion}; then
    echo "Database already exists"
else
    echo "Creating database..."
    PGPASSWORD=$PGPASSWORD psql -h ${PGHOST:-localhost} -U ${PGUSER:-postgres} -c "CREATE DATABASE ${PGDATABASE:-terrafusion};"
    echo "Database created"
fi

# Set up Git hooks
echo "Setting up Git hooks..."
mkdir -p .git/hooks
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook for TerraFusion Platform

# Run flake8
echo "Running flake8..."
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
if [ $? -ne 0 ]; then
    echo "Flake8 failed, commit aborted"
    exit 1
fi

# Run security scan
echo "Running security scan..."
./scripts/security_scan.sh
if [ $? -ne 0 ]; then
    echo "Security scan failed, commit aborted"
    exit 1
fi

exit 0
EOF
chmod +x .git/hooks/pre-commit

echo "Development environment setup complete"
echo "To start the application in development mode, run:"
echo "docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d"