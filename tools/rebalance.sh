#!/bin/bash

# Script to trigger rebalance commands for accounts
# This is a convenience wrapper around enqueue.sh for rebalance operations
# Usage: 
#   ./rebalance.sh -all              # Process all accounts
#   ./rebalance.sh -account U123456  # Process specific account

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Forward all arguments to enqueue.sh with -command rebalance
exec "$SCRIPT_DIR/enqueue.sh" -command rebalance "$@"