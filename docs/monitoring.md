# Remote Monitoring Setup

This guide shows how to set up remote health monitoring for your portfolio rebalancer using free Cloudflare Zero Trust tunnel and UptimeRobot monitoring services. This will allow you to get realtime alerts if the service ever experiences difficulty in processing events for any reason.

## Cloudflare Zero Trust Tunnel (Free)

Cloudflare Zero Trust allows you to securely expose specific endpoints without opening firewall ports or exposing your entire system.

### Step 1: Install Cloudflare Tunnel

1. Create a free Cloudflare account at [dash.cloudflare.com](https://dash.cloudflare.com)
2. Go to **Zero Trust** → **Networks** → **Tunnels**
3. Click **Create a tunnel**
4. Choose **Cloudflared** and name your tunnel (e.g., "portfolio-rebalancer")
5. Follow the installation instructions for your platform:

### Step 2: Configure Tunnel

The tunnel should be configured only for the health endpoint. In the Cloudflare dashboard:

1. **Public Hostnames** → **Add a public hostname**
2. **Subdomain**: `ibkr-portfolio-rebalancer-health` (or your choice)
3. **Domain**: Select your domain or use a Cloudflare-provided domain
4. **Service**: 
   - Type: `HTTP`
   - URL: `localhost:8000`
5. **Additional application settings** → **HTTP Settings**:
   - **Path**: `/health` (this restricts access to only the health endpoint)

## Uptime Monitoring
It is recommended that you sign up for a paid account with 1-minute monitoring. There are several monitoring services available for you to choose from. Here we shall provide you with examples of two popular services.

### Option 1: UptimeRobot
1. Sign up at [uptimerobot.com](https://uptimerobot.com)
2. **Add New Monitor**:
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `IBKR Portfolio Rebalancer Health`
   - **URL**: Your Cloudflare tunnel URL (e.g., `https://ibkr-portfolio-health.yourdomain.com/health`)
   - **Monitoring Interval**: `1 minute`
   - **HTTP Method**: `GET`
3. **Advanced Settings**:
   - **Keyword Monitoring**: Enable
   - **Keyword Type**: `exists`
   - **Keyword**: `"healthy":true` (checks for successful health response)
4. **Alert Contacts**: Add your email/SMS for notifications

### Option 2: Pingdom
1. Sign up at [pingdom.com](https://www.pingdom.com)
2. **Create Check**:
   - **Name**: `Portfolio Rebalancer`
   - **URL**: Your Cloudflare tunnel URL (e.g., `https://ibkr-portfolio-health.yourdomain.com/health`)
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

**Healthy**: No events with retries or in retry queue  
**Unhealthy**: Events are being retried or in retry queue

## Security Considerations

- **Only expose `/health`**: Never expose all the queue management endpoints publicly

## Troubleshooting

**Tunnel not connecting:**
```bash
# Check tunnel status
cloudflared tunnel list
cloudflared tunnel info <tunnel-name>

# Restart tunnel service
sudo systemctl restart cloudflared
```
