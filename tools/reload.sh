#!/bin/bash
# Development reload script for event-broker service
# Usage: ./tools/reload.sh

echo "🔄 Reloading event-broker..."
docker compose stop event-broker && docker compose up -d event-broker