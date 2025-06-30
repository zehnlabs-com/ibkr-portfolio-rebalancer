#!/bin/bash

# Test script for the Rebalancer API
echo "Testing Rebalancer API..."
echo "========================="

BASE_URL="http://localhost:8000"

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo
    echo "Testing: $description"
    echo "Endpoint: $method $endpoint"
    
    if [ -n "$data" ]; then
        response=$(curl -s -X $method "$BASE_URL$endpoint" -H 'Content-Type: application/json' -d "$data")
    else
        response=$(curl -s -X $method "$BASE_URL$endpoint")
    fi
    
    echo "Response: $response"
    echo "---"
}

# Test endpoints
test_endpoint "GET" "/" "" "Root endpoint"
test_endpoint "GET" "/health" "" "Health check"
test_endpoint "GET" "/accounts" "" "List accounts"
test_endpoint "GET" "/accounts/U20660659/positions" "" "Get account positions (should fail - no IBKR)"
test_endpoint "GET" "/accounts/U20660659/value" "" "Get account value (should fail - no IBKR)"
test_endpoint "POST" "/rebalance/U20660659/dry-run" "" "Dry run rebalance (should fail - no IBKR)"
test_endpoint "POST" "/rebalance/U20660659" '{"execution_mode": "dry_run"}' "Dry run via JSON (should fail - no IBKR)"
test_endpoint "GET" "/accounts/INVALID123/positions" "" "Invalid account (should return 404)"
test_endpoint "POST" "/rebalance/INVALID123/dry-run" "" "Invalid account dry run (should return 404)"

echo
echo "API Documentation available at: $BASE_URL/docs"
echo "OpenAPI schema available at: $BASE_URL/openapi.json"