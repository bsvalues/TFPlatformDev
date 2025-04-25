#!/bin/bash
# Security scanning script for TerraFusion Platform
# This script performs various security checks on the codebase and infrastructure

set -e

echo "Starting security scan for TerraFusion Platform"

# Check for dependencies
MISSING_DEPS=0

# Check for Bandit (Python security scanner)
if ! command -v bandit &> /dev/null; then
    echo "Bandit not found. Installing..."
    pip install bandit
fi

# Check for Trivy (Container scanner)
if ! command -v trivy &> /dev/null; then
    echo "Trivy not found, skipping container security scan"
    echo "Please install Trivy: https://github.com/aquasecurity/trivy"
    MISSING_DEPS=1
fi

# Check for trufflehog (Secret scanner)
if ! command -v trufflehog &> /dev/null; then
    echo "trufflehog not found, skipping secret scanning"
    echo "Please install trufflehog: https://github.com/trufflesecurity/trufflehog"
    MISSING_DEPS=1
fi

echo "----------------------------------------"
echo "Running Python code security scan (Bandit)"
echo "----------------------------------------"
bandit -r app services -f txt

# Run Trivy container scan if available
if command -v trivy &> /dev/null; then
    echo "----------------------------------------"
    echo "Running container security scan (Trivy)"
    echo "----------------------------------------"
    
    # Check if image exists
    if docker image inspect terrafusion:latest &> /dev/null; then
        trivy image terrafusion:latest
    else
        echo "Image terrafusion:latest not found, skipping container scan"
        echo "Please build the image first with: docker build -t terrafusion:latest ."
    fi
fi

# Run trufflehog secret scan if available
if command -v trufflehog &> /dev/null; then
    echo "----------------------------------------"
    echo "Running secret scanning (trufflehog)"
    echo "----------------------------------------"
    trufflehog filesystem --directory=.
fi

echo "----------------------------------------"
echo "Running dependency check"
echo "----------------------------------------"
# Check Python dependencies for known vulnerabilities
pip-audit || echo "pip-audit failed or not installed"

echo "----------------------------------------"
echo "Checking for hardcoded secrets in code"
echo "----------------------------------------"
grep -r --include="*.py" --include="*.yaml" --include="*.yml" --include="*.json" --include="*.sh" \
    -E "(password|secret|key|token|credential)[^:=]*[\":=][^,;}{]*(password|secret|key|token)" \
    --exclude-dir=venv --exclude-dir=.git . || echo "No potential hardcoded secrets found"

echo "----------------------------------------"
echo "Checking file permissions"
echo "----------------------------------------"
find . -type f -name "*.sh" ! -perm -u=x -exec echo "Warning: {} is not executable" \;
find . -type f -perm -o=w -not -path "*/\.*" -exec echo "Warning: {} is world-writable" \;

echo "----------------------------------------"
echo "Security scan completed"
echo "----------------------------------------"

if [ $MISSING_DEPS -eq 1 ]; then
    echo "Warning: Some security scans were skipped due to missing dependencies"
    echo "Please install the required tools for a complete security assessment"
fi