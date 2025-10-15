# Quick Reference - TranscriptionBot Deployment

## Initial Deployment

```bash
# Download and run deployment script
wget https://raw.githubusercontent.com/Jasurbek2003/TranscriptionBot/master/deployment/deploy.sh
chmod +x deploy.sh
sudo ./deploy.sh
```

## Essential Commands

### Service Control

```bash
# Restart all services
sudo systemctl restart transcriptionbot-telegram transcriptionbot-django nginx

# Stop all services
sudo systemctl stop transcriptionbot-telegram transcriptionbot-django

# Start all services
sudo systemctl start transcriptionbot-telegram transcriptionbot-django

# Check status
sudo systemctl status transcriptionbot-telegram
sudo systemctl status transcriptionbot-django
```

### View Logs

```bash
# Real-time bot logs
sudo journalctl -u transcriptionbot-telegram -f

# Real-time Django logs
sudo journalctl -u transcriptionbot-django -f

# Last 100 lines
sudo journalctl -u transcriptionbot-telegram -n 100 --no-pager

# Nginx logs
sudo tail -f /var/log/nginx/transcriptionbot_error.log
```

### Configuration

```bash
# Edit environment variables
sudo nano /var/www/TranscriptionBot/.env

# After editing, restart services
sudo systemctl restart transcriptionbot-telegram transcriptionbot-django
```

### Database

```bash
# Connect to database
sudo -u postgres psql transcription_bot

# Run Django migrations
cd /var/www/TranscriptionBot/django_admin
source ../.venv/bin/activate
python manage.py migrate
deactivate

# Create backup
sudo -u postgres pg_dump transcription_bot > backup_$(date +%Y%m%d).sql
```

### Updates

```bash
# Update application
cd /var/www/TranscriptionBot
sudo git pull origin master

# Update Python packages
source .venv/bin/activate
pip install --upgrade -e .
deactivate

# Run migrations and collect static
cd django_admin
source ../.venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
deactivate

# Restart services
sudo systemctl restart transcriptionbot-telegram transcriptionbot-django
```

### SSL Certificate

```bash
# Renew certificate
sudo certbot renew

# Check certificate status
sudo certbot certificates

# Reload nginx after renewal
sudo systemctl reload nginx
```

### Nginx

```bash
# Test configuration
sudo nginx -t

# Reload configuration
sudo systemctl reload nginx

# Restart nginx
sudo systemctl restart nginx
```

### System Monitoring

```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check CPU and processes
htop

# Check system uptime
uptime

# Check network connections
sudo netstat -tuln | grep LISTEN
```

### Troubleshooting

```bash
# Check if port 8000 is listening
sudo netstat -tuln | grep 8000

# Check Python processes
ps aux | grep python

# Check Nginx processes
ps aux | grep nginx

# Test bot token
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# Check DNS resolution
dig transcription.avlo.ai

# Check SSL certificate
openssl s_client -connect transcription.avlo.ai:443 -servername transcription.avlo.ai
```

### File Permissions

```bash
# Fix ownership
sudo chown -R www-data:www-data /var/www/TranscriptionBot

# Fix media permissions
sudo chmod -R 755 /var/www/TranscriptionBot/media

# Fix logs permissions
sudo chown -R www-data:www-data /var/log/transcriptionbot
```

## Important Paths

```
Project Directory:     /var/www/TranscriptionBot
Environment File:      /var/www/TranscriptionBot/.env
Virtual Environment:   /var/www/TranscriptionBot/.venv
Django Admin:          /var/www/TranscriptionBot/django_admin
Media Files:           /var/www/TranscriptionBot/media
Logs:                  /var/log/transcriptionbot/

Systemd Services:      /etc/systemd/system/transcriptionbot-*.service
Nginx Config:          /etc/nginx/sites-available/transcriptionbot
SSL Certificates:      /etc/letsencrypt/live/transcription.avlo.ai/
```

## Required Environment Variables

```env
# Critical - Must be set
BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
DB_PASSWORD=your_database_password
SECRET_KEY=your_django_secret_key

# Important - Should be verified
ALLOWED_HOSTS=transcription.avlo.ai,www.transcription.avlo.ai
WEB_APP_URL=https://transcription.avlo.ai
ENVIRONMENT=production
DEBUG=False
```

## Port Reference

| Port | Service | Access |
|------|---------|--------|
| 80 | Nginx HTTP | Public |
| 443 | Nginx HTTPS | Public |
| 8000 | Gunicorn (Django) | Local only |
| 5432 | PostgreSQL | Local only |
| 6379 | Redis | Local only |

## URLs

- **Main Website:** https://transcription.avlo.ai
- **Admin Panel:** https://transcription.avlo.ai/admin/
- **API Docs:** https://transcription.avlo.ai/api/docs/

## Emergency Recovery

```bash
# If everything breaks, restart everything
sudo systemctl restart postgresql
sudo systemctl restart redis-server
sudo systemctl restart transcriptionbot-telegram
sudo systemctl restart transcriptionbot-django
sudo systemctl restart nginx

# If still broken, check logs
sudo journalctl -xe
```

## Health Checks

```bash
# Test Django is responding
curl http://127.0.0.1:8000

# Test Nginx is serving
curl https://transcription.avlo.ai

# Test bot webhook (if using webhooks)
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo

# Test database connection
sudo -u postgres psql -U transcription_user -d transcription_bot -c "SELECT 1;"

# Test Redis
redis-cli ping
```

## Performance Tuning

```bash
# Check Gunicorn workers
ps aux | grep gunicorn | wc -l

# View system resources
htop

# Check database connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Clear Redis cache (if using)
redis-cli FLUSHALL
```

## Backup Commands

```bash
# Full database backup
sudo -u postgres pg_dump transcription_bot | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup media files
tar -czf media_backup_$(date +%Y%m%d).tar.gz /var/www/TranscriptionBot/media/

# Backup configuration
sudo tar -czf config_backup_$(date +%Y%m%d).tar.gz \
  /var/www/TranscriptionBot/.env \
  /etc/nginx/sites-available/transcriptionbot \
  /etc/systemd/system/transcriptionbot-*.service
```

## Quick Diagnostic

Run these commands if something is broken:

```bash
#!/bin/bash
echo "=== Service Status ==="
sudo systemctl status transcriptionbot-telegram --no-pager
sudo systemctl status transcriptionbot-django --no-pager

echo -e "\n=== Recent Logs ==="
sudo journalctl -u transcriptionbot-telegram -n 10 --no-pager
sudo journalctl -u transcriptionbot-django -n 10 --no-pager

echo -e "\n=== Port Check ==="
sudo netstat -tuln | grep -E '(8000|80|443)'

echo -e "\n=== Disk Space ==="
df -h /var/www/TranscriptionBot

echo -e "\n=== Process Check ==="
ps aux | grep -E '(python|gunicorn|nginx)' | grep -v grep
```

Save this as `diagnostic.sh`, make executable with `chmod +x diagnostic.sh`, and run with `sudo ./diagnostic.sh`
