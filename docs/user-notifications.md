# User Notifications

The portfolio rebalancer sends real-time push system notifications to your mobile device via [ntfy.sh](https://ntfy.sh/). This lets you monitor the system without constantly checking logs.

## Quick Setup

1. **Install the ntfy mobile app**:
   - [iOS App Store](https://apps.apple.com/us/app/ntfy/id1625396347)
   - [Google Play Store](https://play.google.com/store/apps/details?id=io.heckel.ntfy)

2. **Subscribe to your account's channel**: Open the app and subscribe to `{channel_prefix}-{account_id}` (e.g., `JOHN-1234-U12345678`)

## Environment Variables

Configure notifications in your `.env` file or docker-compose:

| Variable | Default | Description |
|----------|---------|-------------|
| `USER_NOTIFICATIONS_ENABLED` | `true` | Enable/disable all notifications |
| `USER_NOTIFICATIONS_SERVER_URL` | `https://ntfy.sh` | ntfy.sh server URL (public or private) |
| `USER_NOTIFICATIONS_AUTH_TOKEN` | `null` | Optional auth token for private servers |
| `USER_NOTIFICATIONS_BUFFER_SECONDS` | `60` | How long to batch events before sending |
| `USER_NOTIFICATIONS_CHANNEL_PREFIX` | `ZLF-2025` | Prefix for all notification channels |

### Important: Channel Prefix Security

**Set `USER_NOTIFICATIONS_CHANNEL_PREFIX` to something unique!** Since by default `https://ntfy.sh` public server is used, a unique prefix will minimize the chance of someone else subscribing to the same channel. This is a good precautionary measure; since channel names include accounts, they're already unique.

Use something personal like:
- `MARY-2025`
- `SMITH-1135` 
- `JOHN-IBKR-9876`

Your notifications will be posed to channels  `{prefix}-{account_id}` (e.g., `MARY-2025`).

## Server Options

### Public Server (Default)
Uses the free public ntfy.sh server at `https://ntfy.sh`. Anyone can subscribe to any channel if they know the name, so use a unique channel prefix.

### Private Server
For better security, run your own ntfy.sh server:

1. **Follow the ntfy.sh self-hosting guide**: https://docs.ntfy.sh/install/
2. **Set your server URL**:
   ```bash
   USER_NOTIFICATIONS_SERVER_URL=https://your-server.com
   USER_NOTIFICATIONS_AUTH_TOKEN=your_token_here
   ```
3. **Configure mobile app** to use your private server

## Mobile App Setup

1. **Download and install** the ntfy app from your app store
2. **Subscribe to channels**: 
   - Tap "+" to add subscription
   - Enter your channel name: `{prefix}-{account_id}`
   - For private servers: Configure server settings first

## What You'll Receive

### Normal Events (Grouped)
Events are batched for 60 seconds to prevent spam. Number of seconds is configurable through `USER_NOTIFICATIONS_BUFFER_SECONDS` environment variable.
- ▶ Rebalance started
- ✅ Rebalance completed  
- 🔄 Rebalance completed after retry
- ⏰ Rebalance delayed until market hours
- 🔄 Rebalance queued for retry

### Critical Events (Immediate)
Sent immediately without buffering:
- 🌐 Connection errors with IBKR
- 🚨 Critical system errors


## Troubleshooting

**Not receiving notifications?**
1. Check `USER_NOTIFICATIONS_ENABLED=true`
2. Verify you're subscribed to the correct channel name including prefix
3. Check mobile app notification settings
4. Review event processor logs: `docker-compose logs -f event-processor`

**Too many notifications?**
- Increase `USER_NOTIFICATIONS_BUFFER_SECONDS` envirornment variable

