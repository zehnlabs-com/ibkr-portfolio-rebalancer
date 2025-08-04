# User Notifications

The portfolio rebalancer sends real-time push system notifications to your desktop and/or mobile device via [ntfy.sh](https://ntfy.sh/). 

## Quick Setup

1. **Install the ntfy mobile app**:
   - [iOS App Store](https://apps.apple.com/us/app/ntfy/id1625396347)
   - [Google Play Store](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
   - [F-Droid](https://f-droid.org/en/packages/io.heckel.ntfy/)

2. **Subscribe to your account's channels**: Open the app and subscribe to any number of channels `{channel_prefix}-{account_id}` (e.g., `JOHN-1234-U12345678`)

## Environment Variables

Configure notifications in your `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `USER_NOTIFICATIONS_ENABLED` | `true` | Enable/disable all notifications |
| `USER_NOTIFICATIONS_SERVER_URL` | `https://ntfy.sh` | ntfy.sh server URL (public or private) |
| `USER_NOTIFICATIONS_BUFFER_SECONDS` | `60` | How long to batch events before sending |
| `USER_NOTIFICATIONS_CHANNEL_PREFIX` | `ZLF-2025` | Prefix for all notification channels (channel_prefix)|

### Important: Channel Prefix Security

**Set `USER_NOTIFICATIONS_CHANNEL_PREFIX` to something unique** Since by default `https://ntfy.sh` public server is used, a unique prefix will minimize the chance of someone else subscribing to the same channel.

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
## Mobile App Setup

1. **Download and install** the ntfy app from your app store
2. **Subscribe to channels**: 
   - Tap "+" to add subscription
   - Enter your channel name: `{channel_prefix}-{account_id}`

## What You'll Receive

### Normal Events (Grouped)
Only event state changes are sent to ntfy.sh. Events are batched for 60 seconds (default) to prevent too many rapid notifications. Number of seconds is configurable through `USER_NOTIFICATIONS_BUFFER_SECONDS` in .env. Normal events include:
- ▶ Rebalance started
- ✅ Rebalance completed  
- 🔄 Rebalance completed after retry
- ⏰ Rebalance delayed until market hours
- 🔄 Rebalance queued for retry

### Critical Events (Immediate)
These are sent immediately without any delay:
- 🌐 Connection errors with IBKR
- 🚨 Critical system errors


## Troubleshooting

**Not receiving notifications?**
1. Check `USER_NOTIFICATIONS_ENABLED=true`
2. Verify you're subscribed to the correct channel name including prefix
3. Check mobile app notification settings

**Too many notifications?**
- Increase `USER_NOTIFICATIONS_BUFFER_SECONDS` envirornment variable

