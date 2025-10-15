# Deployment Files

This directory contains all necessary configuration files for deploying TranscriptionBot to production.

## Quick Start

### Option 1: Automated Deployment (Recommended)

```bash
# On your Ubuntu server
wget https://raw.githubusercontent.com/Jasurbek2003/TranscriptionBot/master/deployment/deploy.sh
chmod +x deploy.sh
sudo ./deploy.sh
```

### Option 2: Manual Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed manual deployment instructions.

## Files Overview

| File | Description |
|------|-------------|
| `deploy.sh` | Automated deployment script for Ubuntu |
| `DEPLOYMENT.md` | Complete deployment guide with troubleshooting |
| `.env.production.example` | Template for production environment variables |
| `gunicorn_config.py` | Gunicorn WSGI server configuration |
| `nginx-transcriptionbot.conf` | Nginx reverse proxy configuration with SSL |
| `transcriptionbot-telegram.service` | Systemd service for Telegram bot |
| `transcriptionbot-django.service` | Systemd service for Django web app |

## Configuration Required

Before deployment, you'll need:

1. **Telegram Bot Token** - Get from @BotFather
2. **Gemini API Key** - Get from Google AI Studio
3. **Domain Name** - `transcription.avlo.ai` pointed to your server
4. **Server Access** - Ubuntu 20.04/22.04 with root/sudo access

## Post-Deployment

After running `deploy.sh`, remember to:

1. Edit `/var/www/TranscriptionBot/.env` with your credentials
2. Update database password
3. Restart services: `sudo systemctl restart transcriptionbot-*`
4. Check logs: `sudo journalctl -u transcriptionbot-telegram -f`

## Architecture

```
┌─────────────────────────────────────────┐
│         Internet (HTTPS)                │
└────────────────┬────────────────────────┘
                 │
         ┌───────▼────────┐
         │  Nginx (443)   │
         │  SSL/TLS       │
         └────────┬───────┘
                  │
         ┌────────▼─────────┐
         │  Gunicorn (8000) │
         │  Django App      │
         └────────┬─────────┘
                  │
         ┌────────▼──────────┐
         │  PostgreSQL DB    │
         └───────────────────┘

┌─────────────────────────────────────────┐
│  Telegram Bot API                       │
└────────────────┬────────────────────────┘
                 │
         ┌───────▼──────────┐
         │  Telegram Bot    │
         │  (Python/Aiogram)│
         └────────┬─────────┘
                  │
         ┌────────▼──────────┐
         │  PostgreSQL DB    │
         └───────────────────┘
```

## Service Management

```bash
# Start services
sudo systemctl start transcriptionbot-telegram
sudo systemctl start transcriptionbot-django

# Stop services
sudo systemctl stop transcriptionbot-telegram
sudo systemctl stop transcriptionbot-django

# Restart services
sudo systemctl restart transcriptionbot-telegram
sudo systemctl restart transcriptionbot-django

# View logs
sudo journalctl -u transcriptionbot-telegram -f
sudo journalctl -u transcriptionbot-django -f
```

## Troubleshooting

If something goes wrong, check:

1. **Service status:**
   ```bash
   sudo systemctl status transcriptionbot-telegram
   sudo systemctl status transcriptionbot-django
   ```

2. **Logs:**
   ```bash
   sudo journalctl -u transcriptionbot-telegram -n 100
   sudo journalctl -u transcriptionbot-django -n 100
   ```

3. **Nginx:**
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   ```

4. **Database:**
   ```bash
   sudo -u postgres psql transcription_bot
   ```

## Security Notes

- All services run as `www-data` user (non-root)
- SSL/TLS encryption enabled by default
- Firewall should only allow ports 80, 443, 22
- Database passwords should be strong and unique
- Django SECRET_KEY is auto-generated during deployment

## Support

For detailed help, see [DEPLOYMENT.md](DEPLOYMENT.md).
