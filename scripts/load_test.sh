#!/bin/bash
# Load testing script for TerraFusion Platform
# This script runs load tests against the API endpoints

set -e

# Configuration
HOST=${1:-"localhost:5000"}  # Default to localhost:5000 if not provided
DURATION=${2:-"30s"}         # Default to 30 seconds duration if not provided
USERS=${3:-"50"}             # Default to 50 concurrent users if not provided
TARGET_ENDPOINT=${4:-"/"}    # Default to root endpoint if not provided

# Check if required tools are installed
if ! command -v ab &> /dev/null; then
    echo "Apache Benchmark (ab) not found"
    echo "Please install Apache Benchmark: sudo apt-get install apache2-utils"
    exit 1
fi

if ! command -v hey &> /dev/null; then
    echo "Hey load testing tool not found, will use Apache Benchmark only"
    echo "To install Hey: https://github.com/rakyll/hey"
    HEY_AVAILABLE=false
else
    HEY_AVAILABLE=true
fi

echo "Starting load tests for TerraFusion Platform"
echo "Host: $HOST"
echo "Duration: $DURATION"
echo "Concurrent users: $USERS"
echo "Target endpoint: $TARGET_ENDPOINT"

# Check if the server is up
echo "Checking if server is up..."
if ! curl -s "http://$HOST/health" | grep -q "healthy"; then
    echo "Server is not responding or not healthy"
    echo "Please ensure the server is running before running load tests"
    exit 1
fi

echo "Server is up and healthy, starting load tests..."

# Run tests with Apache Benchmark
echo "----------------------------------------"
echo "Running Apache Benchmark"
echo "----------------------------------------"
ab -n 1000 -c $USERS -t $DURATION http://$HOST$TARGET_ENDPOINT

# Run tests with Hey if available
if [ "$HEY_AVAILABLE" = true ]; then
    echo "----------------------------------------"
    echo "Running Hey load testing tool"
    echo "----------------------------------------"
    hey -z $DURATION -c $USERS http://$HOST$TARGET_ENDPOINT
fi

# Check server health after load test
echo "----------------------------------------"
echo "Checking server health after load test"
echo "----------------------------------------"
curl -s "http://$HOST/health"

echo "----------------------------------------"
echo "Load testing completed"
echo "----------------------------------------"

# Optional: Run more detailed analysis
echo "Would you like to run a more detailed analysis? (y/n)"
read -r ANSWER
if [[ $ANSWER =~ ^[Yy]$ ]]; then
    echo "----------------------------------------"
    echo "Running detailed analysis"
    echo "----------------------------------------"
    
    echo "Testing API response time under varying loads..."
    
    # Test with different concurrency levels
    for CONCURRENCY in 10 25 50 100; do
        echo "Testing with $CONCURRENCY concurrent users..."
        ab -n 500 -c $CONCURRENCY http://$HOST$TARGET_ENDPOINT
    done
    
    # Test different endpoints if Hey is available
    if [ "$HEY_AVAILABLE" = true ]; then
        echo "Testing different endpoints..."
        
        ENDPOINTS=("/health" "/api/v1/map" "/api/v1/audit" "/api/v1/flow" "/api/v1/insight")
        
        for ENDPOINT in "${ENDPOINTS[@]}"; do
            echo "Testing endpoint: $ENDPOINT"
            hey -n 200 -c 20 http://$HOST$ENDPOINT
        done
    fi
    
    echo "Detailed analysis completed"
fi

echo "Load testing script completed"