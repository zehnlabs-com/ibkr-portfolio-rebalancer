# Remote Monitoring Setup

This guide shows how to set up remote health monitoring for your portfolio rebalancer using Cloudflare Zero Trust tunnel and UptimeRobot monitoring services.

## Cloudflare Zero Trust Tunnel (Free)

Cloudflare Zero Trust allows you to securely expose specific endpoints without opening firewall ports or exposing your entire system.

### Step 1: Install Cloudflare Tunnel

1. Create a free Cloudflare account at [dash.cloudflare.com](https://dash.cloudflare.com)
2. Go to **Zero Trust** → **Networks** → **Tunnels**
3. Click **Create a tunnel**
4. Choose **Cloudflared** and name your tunnel (e.g., "portfolio-rebalancer")
5. Follow the installation instructions for your platform:

**Windows (WSL/Ubuntu):**
```bash
# Download cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Authenticate (use the command provided by Cloudflare)
cloudflared service install <your-token-here>
```

### Step 2: Configure Tunnel for Health Endpoint Only

In the Cloudflare dashboard:

1. **Public Hostnames** → **Add a public hostname**
2. **Subdomain**: `ibkr-portfolio-rebalancer-health` (or your choice)
3. **Domain**: Select your domain or use a Cloudflare-provided domain
4. **Service**: 
   - Type: `HTTP`
   - URL: `localhost:8000`
5. **Additional application settings** → **HTTP Settings**:
   - **Path**: `/health` (this restricts access to only the health endpoint)

## Uptime Monitoring

### Option 1: Uptime Robot (Free)

1. Sign up at [uptimerobot.com](https://uptimerobot.com)
2. **Add New Monitor**:
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `IBKR Portfolio Rebalancer Health`
   - **URL**: Your Cloudflare tunnel URL (e.g., `https://ibkr-portfolio-health.yourdomain.com/health`)
   - **Monitoring Interval**: `5 minutes` (free tier)
   - **HTTP Method**: `GET`
3. **Advanced Settings**:
   - **Keyword Monitoring**: Enable
   - **Keyword Type**: `exists`
   - **Keyword**: `"healthy":true` (checks for successful health response)
4. **Alert Contacts**: Add your email/SMS for notifications

### Option 2: Uptime Kuma (Self-hosted)

If you prefer self-hosted monitoring:

```bash
# Add to your docker-compose.yaml
uptime-kuma:
  image: louislam/uptime-kuma:1
  container_name: uptime-kuma
  volumes:
    - uptime-kuma-data:/app/data
  ports:
    - "3001:3001"
  restart: unless-stopped

volumes:
  uptime-kuma-data:
```

### Option 3: Pingdom (Paid)

For more advanced monitoring:

1. Sign up at [pingdom.com](https://www.pingdom.com)
2. **Create Check**:
   - **Name**: `Portfolio Rebalancer`
   - **URL**: Your tunnel URL
   - **Check interval**: `1 minute`
3. **Advanced Settings**:
   - **Response should contain**: `"healthy":true`
   - **Alert policy**: Configure email/SMS alerts

## Health Response Format

The health endpoint returns JSON in this format:

```json
{
  "healthy": true,
  "message": "System is healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Healthy**: No events with retries or in delayed queue  
**Unhealthy**: Events are being retried or delayed

## Alert Setup Examples

### Uptime Robot Alert Message

Configure custom alert messages:

**Down Alert**: "🚨 Portfolio Rebalancer is DOWN - Check system immediately"  
**Up Alert**: "✅ Portfolio Rebalancer is back UP"

### Monitoring Best Practices

1. **Check Interval**: 5-10 minutes (balance between responsiveness and costs)
2. **Keyword Monitoring**: Always check for `"healthy":true` in response
3. **Multiple Contacts**: Set up both email and SMS alerts
4. **Escalation**: Configure escalation rules for persistent failures
5. **Maintenance Windows**: Use maintenance windows during planned updates

## Security Considerations

- **Only expose `/health`**: Never expose queue management endpoints publicly
- **Use Cloudflare Access**: Add authentication for additional security
- **Monitor tunnel logs**: Regularly check Cloudflare tunnel logs for unusual access
- **Rotate tokens**: Periodically rotate Cloudflare tunnel tokens

## Troubleshooting

**Tunnel not connecting:**
```bash
# Check tunnel status
cloudflared tunnel list
cloudflared tunnel info <tunnel-name>

# Restart tunnel service
sudo systemctl restart cloudflared
```

**Health check failing:**
- Verify management service is running: `docker-compose ps management-service`
- Test locally first: `curl http://localhost:8000/health`
- Check tunnel configuration points to correct port (8000)

**Uptime monitoring false positives:**
- Ensure keyword monitoring looks for exact string: `"healthy":true`
- Check if Cloudflare Access is blocking the monitoring service
- Verify tunnel is stable with `cloudflared tunnel info`