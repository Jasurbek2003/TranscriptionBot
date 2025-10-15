# TranscriptionBot Deployment Guide

Complete guide for deploying TranscriptionBot to Ubuntu server with domain **transcription.avlo.ai**.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Requirements](#server-requirements)
3. [Quick Deployment](#quick-deployment)
4. [Manual Deployment](#manual-deployment)
5. [Configuration](#configuration)
6. [Service Management](#service-management)
7. [Monitoring and Logs](#monitoring-and-logs)
8. [Troubleshooting](#troubleshooting)
9. [Backup and Maintenance](#backup-and-maintenance)

---

## Prerequisites

### Required Accounts & Credentials

- Ubuntu server (20.04 LTS or 22.04 LTS recommended)
- SSH access with root/sudo privileges
- Domain name: `transcription.avlo.ai` (DNS configured to point to your server IP)
- Telegram Bot Token (from @BotFather)
- Gemini API Key (from Google AI Studio)
- PostgreSQL database credentials
- Payment gateway credentials (PayMe, Click) - optional

### DNS Configuration

Before deployment, ensure your domain DNS records are configured:

```
A Record:     transcription.avlo.ai  →  YOUR_SERVER_IP
A Record:     www.transcription.avlo.ai  →  YOUR_SERVER_IP
```

Check DNS propagation:
```bash
dig transcription.avlo.ai
nslookup transcription.avlo.ai
```

---

## Server Requirements

### Minimum Specifications

- **OS**: Ubuntu 20.04/22.04 LTS
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 20 GB SSD
- **Network**: Public IP with ports 80, 443 open

### Recommended Specifications

- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Storage**: 50+ GB SSD
- **Network**: High bandwidth for media file uploads

### Open Firewall Ports

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH

# Enable firewall
sudo ufw enable
sudo ufw status
```

---

## Quick Deployment

### Automated Deployment Script

The easiest way to deploy is using the automated deployment script:

```bash
# 1. Connect to your server
ssh user@your-server-ip

# 2. Download the deployment script
wget https://raw.githubusercontent.com/Jasurbek2003/TranscriptionBot/master/deployment/deploy.sh

# 3. Make it executable
chmod +x deploy.sh

# 4. Run the deployment script
sudo ./deploy.sh
```

The script will:
- Install all dependencies (Python 3.13, PostgreSQL, Redis, Nginx, FFmpeg)
- Setup PostgreSQL database
- Clone the repository
- Configure virtual environment
- Setup systemd services
- Configure Nginx with SSL (Let's Encrypt)
- Start all services

### Post-Deployment Steps

After running the script:

1. **Edit environment variables:**
```bash
sudo nano /var/www/TranscriptionBot/.env
```

Fill in:
- `BOT_TOKEN` - Your Telegram bot token
- `GEMINI_API_KEY` - Your Gemini API key
- `DB_PASSWORD` - Database password
- Payment credentials (if using)

2. **Update database password:**
```bash
sudo -u postgres psql
\c transcription_bot
ALTER USER transcription_user WITH PASSWORD 'your_secure_password';
\q
```

3. **Restart services:**
```bash
sudo systemctl restart transcriptionbot-telegram
sudo systemctl restart transcriptionbot-django
```

4. **Verify deployment:**
```bash
# Check service status
sudo systemctl status transcriptionbot-telegram
sudo systemctl status transcriptionbot-django

# Visit your website
https://transcription.avlo.ai
```

---

## Manual Deployment

If you prefer manual installation:

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Python 3.13

```bash
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.13 python3.13-venv python3.13-dev -y
```

### 3. Install System Dependencies

```bash
sudo apt install -y \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    certbot python3-certbot-nginx \
    git curl wget \
    build-essential libpq-dev \
    ffmpeg
```

### 4. Setup PostgreSQL

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE transcription_bot;
CREATE USER transcription_user WITH PASSWORD 'your_password';
ALTER ROLE transcription_user SET client_encoding TO 'utf8';
ALTER ROLE transcription_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE transcription_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE transcription_bot TO transcription_user;
\c transcription_bot
GRANT ALL ON SCHEMA public TO transcription_user;
\q
```

### 5. Setup Redis

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 6. Clone Repository

```bash
sudo mkdir -p /var/www/TranscriptionBot
cd /var/www/TranscriptionBot
sudo git clone https://github.com/Jasurbek2003/TranscriptionBot.git .

# Create directories
sudo mkdir -p logs media/{audio,video,transcriptions}
sudo mkdir -p /var/run/transcriptionbot
sudo mkdir -p /var/log/transcriptionbot

# Set permissions
sudo chown -R www-data:www-data /var/www/TranscriptionBot
sudo chown -R www-data:www-data /var/run/transcriptionbot
sudo chown -R www-data:www-data /var/log/transcriptionbot
```

### 7. Setup Python Environment

```bash
cd /var/www/TranscriptionBot

# Create virtual environment
python3.13 -m venv .venv

# Activate and install dependencies
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
deactivate
```

### 8. Configure Environment

```bash
# Copy environment template
sudo cp deployment/.env.production.example .env

# Edit with your values
sudo nano .env
```

### 9. Run Django Migrations

```bash
cd /var/www/TranscriptionBot/django_admin
source ../.venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.production

python manage.py migrate
python manage.py collectstatic --noinput
deactivate
```

### 10. Setup Systemd Services

```bash
# Copy service files
sudo cp deployment/transcriptionbot-telegram.service /etc/systemd/system/
sudo cp deployment/transcriptionbot-django.service /etc/systemd/system/

# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable transcriptionbot-telegram
sudo systemctl enable transcriptionbot-django
```

### 11. Configure Nginx

```bash
# Copy nginx config
sudo cp deployment/nginx-transcriptionbot.conf /etc/nginx/sites-available/transcriptionbot

# Enable site
sudo ln -s /etc/nginx/sites-available/transcriptionbot /etc/nginx/sites-enabled/

# Remove default
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t
```

### 12. Setup SSL Certificate

```bash
# Restart nginx
sudo systemctl restart nginx

# Obtain certificate
sudo certbot --nginx -d transcription.avlo.ai -d www.transcription.avlo.ai
```

### 13. Start Services

```bash
sudo systemctl start transcriptionbot-telegram
sudo systemctl start transcriptionbot-django
sudo systemctl restart nginx
```

---

## Configuration

### Environment Variables

Key variables in `/var/www/TranscriptionBot/.env`:

```env
# Required
BOT_TOKEN=your_bot_token
GEMINI_API_KEY=your_gemini_key
DB_PASSWORD=your_db_password

# Domain
WEB_APP_URL=https://transcription.avlo.ai
ALLOWED_HOSTS=transcription.avlo.ai,www.transcription.avlo.ai

# Security
DEBUG=False
SECRET_KEY=generated_django_secret

# Admin IDs
ADMIN_IDS=1222173292,928883166
```

### Database Configuration

Edit `/var/www/TranscriptionBot/.env`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=transcription_bot
DB_USER=transcription_user
DB_PASSWORD=your_secure_password
```

### Redis Configuration

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

---

## Service Management

### Start/Stop/Restart Services

```bash
# Telegram Bot
sudo systemctl start transcriptionbot-telegram
sudo systemctl stop transcriptionbot-telegram
sudo systemctl restart transcriptionbot-telegram

# Django Web App
sudo systemctl start transcriptionbot-django
sudo systemctl stop transcriptionbot-django
sudo systemctl restart transcriptionbot-django

# Nginx
sudo systemctl restart nginx
```

### Check Service Status

```bash
sudo systemctl status transcriptionbot-telegram
sudo systemctl status transcriptionbot-django
sudo systemctl status nginx
```

### Enable/Disable Auto-Start

```bash
# Enable on boot
sudo systemctl enable transcriptionbot-telegram
sudo systemctl enable transcriptionbot-django

# Disable on boot
sudo systemctl disable transcriptionbot-telegram
sudo systemctl disable transcriptionbot-django
```

---

## Monitoring and Logs

### View Service Logs

```bash
# Telegram Bot logs (real-time)
sudo journalctl -u transcriptionbot-telegram -f

# Django logs (real-time)
sudo journalctl -u transcriptionbot-django -f

# Nginx access logs
sudo tail -f /var/log/nginx/transcriptionbot_access.log

# Nginx error logs
sudo tail -f /var/log/nginx/transcriptionbot_error.log

# Gunicorn logs
sudo tail -f /var/log/transcriptionbot/gunicorn_error.log
```

### View Last 100 Log Lines

```bash
sudo journalctl -u transcriptionbot-telegram -n 100 --no-pager
sudo journalctl -u transcriptionbot-django -n 100 --no-pager
```

### Check System Resources

```bash
# CPU and Memory usage
htop

# Disk usage
df -h

# Check specific process
ps aux | grep python
```

### Database Monitoring

```bash
# Connect to PostgreSQL
sudo -u postgres psql transcription_bot

# Check database size
SELECT pg_size_pretty(pg_database_size('transcription_bot'));

# Check active connections
SELECT count(*) FROM pg_stat_activity;
```

---

## Troubleshooting

### Bot Not Starting

1. **Check logs:**
```bash
sudo journalctl -u transcriptionbot-telegram -n 50
```

2. **Verify environment:**
```bash
cat /var/www/TranscriptionBot/.env | grep BOT_TOKEN
```

3. **Test bot token:**
```bash
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

### Django Not Accessible

1. **Check Gunicorn status:**
```bash
sudo systemctl status transcriptionbot-django
```

2. **Test Gunicorn directly:**
```bash
curl http://127.0.0.1:8000
```

3. **Check Nginx configuration:**
```bash
sudo nginx -t
```

### SSL Certificate Issues

```bash
# Renew certificate manually
sudo certbot renew

# Check certificate status
sudo certbot certificates
```

### Database Connection Errors

```bash
# Test database connection
sudo -u postgres psql -U transcription_user -d transcription_bot

# Check PostgreSQL is running
sudo systemctl status postgresql
```

### Permission Issues

```bash
# Fix ownership
sudo chown -R www-data:www-data /var/www/TranscriptionBot

# Fix media directory permissions
sudo chmod -R 755 /var/www/TranscriptionBot/media
```

---

## Backup and Maintenance

### Database Backup

```bash
# Create backup
sudo -u postgres pg_dump transcription_bot > backup_$(date +%Y%m%d).sql

# Restore from backup
sudo -u postgres psql transcription_bot < backup_20250101.sql
```

### Application Update

```bash
# Pull latest code
cd /var/www/TranscriptionBot
sudo git pull origin master

# Activate venv and update dependencies
source .venv/bin/activate
pip install --upgrade -e .

# Run migrations
cd django_admin
python manage.py migrate
python manage.py collectstatic --noinput
deactivate

# Restart services
sudo systemctl restart transcriptionbot-telegram
sudo systemctl restart transcriptionbot-django
```

### SSL Certificate Renewal

Certificates auto-renew, but to manually renew:

```bash
sudo certbot renew
sudo systemctl reload nginx
```

### Log Rotation

Logs are automatically rotated by systemd journal. To configure:

```bash
sudo nano /etc/systemd/journald.conf

# Set limits
SystemMaxUse=1G
SystemMaxFileSize=100M
```

### System Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Reboot if kernel updated
sudo reboot
```

---

## Security Checklist

- [ ] Firewall configured (UFW)
- [ ] SSL certificate installed
- [ ] Strong database password
- [ ] Django SECRET_KEY changed
- [ ] DEBUG=False in production
- [ ] Regular backups scheduled
- [ ] Monitoring setup
- [ ] SSH key authentication enabled
- [ ] Root login disabled
- [ ] Fail2ban installed (optional)

---

## Support

For issues and questions:
- GitHub: https://github.com/Jasurbek2003/TranscriptionBot
- Check logs first: `sudo journalctl -u transcriptionbot-telegram -f`

---

## License

See LICENSE file in the repository.
