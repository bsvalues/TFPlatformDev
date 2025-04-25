#!/bin/bash
# Load testing script for TerraFusion Platform
# This script performs load testing using Apache Bench

set -e

# Configuration
HOST=${1:-"localhost:5000"}  # Default to localhost:5000 if not provided
ENDPOINT=${2:-"/health"}     # Default to health endpoint if not provided
CONCURRENCY=${3:-10}         # Default concurrency level
REQUESTS=${4:-1000}          # Default number of requests
OUTPUT_DIR="load_test_results"

# Create output directory if it doesn't exist
mkdir -p $OUTPUT_DIR

# Generate timestamp for output files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/load_test_${TIMESTAMP}.txt"
GRAPH_FILE="$OUTPUT_DIR/load_test_${TIMESTAMP}.png"

echo "Starting load test for TerraFusion Platform"
echo "Host: $HOST"
echo "Endpoint: $ENDPOINT"
echo "Concurrency: $CONCURRENCY"
echo "Requests: $REQUESTS"
echo "Output file: $OUTPUT_FILE"

# Check if Apache Bench is installed
if ! command -v ab &> /dev/null; then
    echo "Apache Bench (ab) is not installed"
    echo "To install: apt-get install apache2-utils"
    exit 1
fi

# Run the load test
echo "Running load test..."
ab -c $CONCURRENCY -n $REQUESTS -g $OUTPUT_FILE.csv "http://$HOST$ENDPOINT" > $OUTPUT_FILE

# Display summary
echo "Load test completed"
echo "Results saved to $OUTPUT_FILE"

# Generate graph if gnuplot is available
if command -v gnuplot &> /dev/null; then
    echo "Generating performance graph..."
    gnuplot <<EOF
    set terminal png
    set output "$GRAPH_FILE"
    set title "TerraFusion Load Test Results ($REQUESTS Requests, $CONCURRENCY Concurrent)"
    set size 1,0.7
    set grid y
    set xlabel "Request"
    set ylabel "Response Time (ms)"
    plot "$OUTPUT_FILE.csv" using 9 smooth sbezier with lines title "Response Time"
EOF
    echo "Graph saved to $GRAPH_FILE"
else
    echo "gnuplot is not installed, skipping graph generation"
    echo "To install: apt-get install gnuplot"
fi

# Display basic statistics
echo "Basic Statistics:"
grep "Requests per second" $OUTPUT_FILE
grep "Time per request" $OUTPUT_FILE | head -1
grep "Transfer rate" $OUTPUT_FILE