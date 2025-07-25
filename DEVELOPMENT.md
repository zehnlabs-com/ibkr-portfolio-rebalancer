# Development Guide

## Live Code Reloading Setup

This project uses a hybrid approach for development that eliminates the need to rebuild Docker images when making code changes:

### How It Works

- **Management Service**: Full auto-reload using uvicorn with `--reload` flag
- **Event Processor & Event Broker**: Manual reload using the `reload.sh` script
- All services mount source code as volumes for instant code updates

### Development Workflow

#### 1. Management Service (Automatic)
The management service automatically detects file changes and reloads:
```bash
# Just make your changes - no restart needed!
# The service will automatically reload when you save files
```

#### 2. Other Services (Manual Reload)
For event-processor and event-broker, use the reload script:

```bash
# After making changes to event-processor:
./reload.sh processor

# After making changes to event-broker:
./reload.sh broker

# Reload all services that need manual restart:
./reload.sh all

# Show usage help:
./reload.sh
```

### Available Reload Commands

| Command | Service | Description |
|---------|---------|-------------|
| `./reload.sh processor` | event-processor | Reload event processor service |
| `./reload.sh broker` | event-broker | Reload event broker service |
| `./reload.sh management` | management-service | Shows info (auto-reload enabled) |
| `./reload.sh all` | All manual services | Reload all services that need manual restart |

### Performance Benefits

- ✅ **Fast**: 3-5 seconds vs 30+ second rebuilds
- ✅ **No image rebuilds**: Code changes via mounted volumes
- ✅ **Consistent**: Same workflow every time
- ✅ **Production-safe**: No dev dependencies in production images

### File Structure

```
docker-compose.yaml          # Production service definitions
docker-compose.override.yml  # Development overrides (volume mounts, reload commands)
reload.sh                   # Development reload script
```

### Technical Details

The development setup uses:
- **Volume mounts**: Source code is mounted into containers at runtime
- **uvicorn --reload**: Automatic file watching for management service
- **Container recreation**: Fast restart for other services without rebuilding images
- **docker-compose.override.yml**: Development-specific configuration

### Troubleshooting

**Issue**: Changes not appearing after reload
**Solution**: Ensure you're using `./reload.sh service-name` not `docker-compose restart service-name`

**Issue**: Script shows line ending errors on Windows
**Solution**: The script automatically handles line endings, but if issues persist:
```bash
sed -i 's/\r$//' reload.sh
```

**Issue**: Permission denied when running reload.sh
**Solution**: Make the script executable:
```bash
chmod +x reload.sh
```

### Alternative Manual Commands

If you prefer not to use the script:
```bash
# Reload event-processor
docker-compose stop event-processor && docker-compose up -d event-processor

# Reload event-broker  
docker-compose stop event-broker && docker-compose up -d event-broker
```

### Key Points

1. **Never use `docker-compose restart`** for development - it doesn't apply volume mount changes
2. **Use `docker-compose stop && docker-compose up -d`** or the reload script
3. **Management service changes are automatic** - no manual action needed
4. **Code changes are instant** - no Docker image rebuilding required