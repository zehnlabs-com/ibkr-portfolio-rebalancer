# 🔗 Port Forwarding Setup for Tabby SSH

This guide shows you how to set up port forwarding in Tabby Terminal to access your cloud-deployed services locally.

## Port Forwarding Configuration

When setting up your SSH connection in Tabby, you need to configure port forwarding to access the web services running on your cloud server.

### Required Port Forwards

You'll need to forward these two ports:

#### Port Forward #1: Management API
- **Local port:** `8000`
- **Remote host:** `127.0.0.1`
- **Remote port:** `8000`

#### Port Forward #2: Container Management
- **Local port:** `8080`
- **Remote host:** `127.0.0.1`
- **Remote port:** `8080`

### How to Configure in Tabby

1. **Open your SSH profile settings** in Tabby
2. **Click the "Ports" tab**
3. **Add the first port forward:**
   - Local port: `8000`
   - Remote host: `127.0.0.1`
   - Remote port: `8000`
4. **Add the second port forward:**
   - Local port: `8080`
   - Remote host: `127.0.0.1`
   - Remote port: `8080`
5. **Save your profile**

### What These Ports Do

- **Port 8000**: Management API for health checks, queue status, and system monitoring
- **Port 8080**: Container management interface with real-time logs and container controls

### Important Notes

- 🔗 **Keep your SSH connection open** - Port forwarding only works while connected
- 🌐 **Access via localhost** - After connecting, visit `http://localhost:8000` and `http://localhost:8000`

