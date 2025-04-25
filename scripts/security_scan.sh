#!/bin/bash
# Security scanning script for TerraFusion Platform
# This script performs security scanning of the application code and dependencies

set -e

echo "Starting security scan for TerraFusion Platform"

# Check for Python dependencies with known vulnerabilities
echo "Checking Python dependencies for vulnerabilities..."
pip install safety
safety check -r requirements.txt

# Run static code analysis
echo "Running static code analysis..."
pip install bandit
bandit -r . -x venv,env,tests

# Check Docker image for vulnerabilities (requires Trivy)
if command -v trivy &> /dev/null; then
    echo "Scanning Docker image for vulnerabilities..."
    docker build -t terrafusion-scan:latest .
    trivy image terrafusion-scan:latest
else
    echo "Trivy is not installed, skipping Docker image scan"
    echo "To install Trivy: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
fi

# Check secrets (requires git-secrets)
if command -v git-secrets &> /dev/null; then
    echo "Checking for secrets in code..."
    git secrets --scan
else
    echo "git-secrets is not installed, skipping secrets scan"
    echo "To install git-secrets: https://github.com/awslabs/git-secrets"
fi

echo "Security scan completed"