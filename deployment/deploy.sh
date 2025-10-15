#!/bin/bash

# =============================================================================
# TranscriptionBot Deployment Script for Ubuntu Server
# Domain: transcription.avlo.ai
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="TranscriptionBot"
DOMAIN="transcription.avlo.ai"
DEPLOY_USER="www-data"
PROJECT_DIR="/var/www/$PROJECT_NAME"
VENV_DIR="$PROJECT_DIR/.venv"
GITHUB_REPO="https://github.com/Jasurbek2003/TranscriptionBot.git"

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run this script as root (use sudo)"
    exit 1
fi

# =============================================================================
# 1. System Update and Install Dependencies
# =============================================================================
install_dependencies() {
    print_info "Updating system packages..."
    apt update && apt upgrade -y

    print_info "Installing system dependencies..."
    apt install -y \
        python3.13 \
        python3.13-venv \
        python3.13-dev \
        python3-pip \
        postgresql \
        postgresql-contrib \
        redis-server \
        nginx \
        certbot \
        python3-certbot-nginx \
        git \
        curl \
        wget \
        build-essential \
        libpq-dev \
        ffmpeg \
        supervisor

    print_info "Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
}

# =============================================================================
# 2. Configure PostgreSQL
# =============================================================================
setup_database() {
    print_info "Setting up PostgreSQL database..."

    # Check if database exists
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw transcription_bot; then
        print_warning "Database 'transcription_bot' already exists. Skipping creation."
    else
        print_info "Creating database and user..."
        sudo -u postgres psql <<EOF
CREATE DATABASE transcription_bot;
CREATE USER transcription_user WITH PASSWORD 'change_this_password';
ALTER ROLE transcription_user SET client_encoding TO 'utf8';
ALTER ROLE transcription_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE transcription_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE transcription_bot TO transcription_user;
\c transcription_bot
GRANT ALL ON SCHEMA public TO transcription_user;
EOF
        print_info "Database created successfully!"
        print_warning "IMPORTANT: Change the database password in .env file and in PostgreSQL!"
    fi
}

# =============================================================================
# 3. Configure Redis
# =============================================================================
setup_redis() {
    print_info "Configuring Redis..."
    systemctl enable redis-server
    systemctl start redis-server
    print_info "Redis configured and started!"
}

# =============================================================================
# 4. Clone and Setup Project
# =============================================================================
setup_project() {
    print_info "Setting up project directory..."

    # Create project directory
    mkdir -p $PROJECT_DIR
    cd $PROJECT_DIR

    # Clone repository if not exists
    if [ ! -d "$PROJECT_DIR/.git" ]; then
        print_info "Cloning repository..."
        git clone $GITHUB_REPO .
    else
        print_info "Repository already exists. Pulling latest changes..."
        git pull origin master
    fi

    # Create necessary directories
    mkdir -p logs media media/audio media/video media/transcriptions
    mkdir -p /var/run/transcriptionbot
    mkdir -p /var/log/transcriptionbot

    # Set permissions
    chown -R $DEPLOY_USER:$DEPLOY_USER $PROJECT_DIR
    chown -R $DEPLOY_USER:$DEPLOY_USER /var/run/transcriptionbot
    chown -R $DEPLOY_USER:$DEPLOY_USER /var/log/transcriptionbot

    print_info "Project directory setup complete!"
}

# =============================================================================
# 5. Setup Python Virtual Environment
# =============================================================================
setup_venv() {
    print_info "Setting up Python virtual environment..."

    cd $PROJECT_DIR

    # Create virtual environment
    if [ ! -d "$VENV_DIR" ]; then
        python3.13 -m venv $VENV_DIR
    fi

    # Activate virtual environment
    source $VENV_DIR/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Install dependencies using uv (faster) or pip
    if command -v uv &> /dev/null; then
        print_info "Installing dependencies with uv..."
        uv pip install -e .
    else
        print_info "Installing dependencies with pip..."
        pip install -e .
    fi

    deactivate
    print_info "Virtual environment setup complete!"
}

# =============================================================================
# 6. Configure Environment Variables
# =============================================================================
setup_env() {
    print_info "Setting up environment variables..."

    if [ ! -f "$PROJECT_DIR/.env" ]; then
        print_info "Creating .env file from template..."
        cp $PROJECT_DIR/deployment/.env.production.example $PROJECT_DIR/.env

        print_warning "IMPORTANT: Edit $PROJECT_DIR/.env and fill in your configuration!"
        print_warning "You need to set:"
        print_warning "  - BOT_TOKEN"
        print_warning "  - GEMINI_API_KEY"
        print_warning "  - DB_PASSWORD"
        print_warning "  - SECRET_KEY (Django)"
        print_warning "  - Payment gateway credentials (if using)"

        # Generate Django secret key
        DJANGO_SECRET=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
        sed -i "s/change_this_to_a_long_random_django_secret_key/$DJANGO_SECRET/" $PROJECT_DIR/.env

        print_info "Generated Django secret key automatically."
    else
        print_warning ".env file already exists. Skipping..."
    fi
}

# =============================================================================
# 7. Run Django Migrations and Collect Static
# =============================================================================
setup_django() {
    print_info "Setting up Django..."

    cd $PROJECT_DIR/django_admin
    source $VENV_DIR/bin/activate

    # Set Django settings
    export DJANGO_SETTINGS_MODULE=config.settings.production

    # Run migrations
    print_info "Running database migrations..."
    python manage.py migrate --noinput

    # Collect static files
    print_info "Collecting static files..."
    python manage.py collectstatic --noinput

    # Create superuser (optional - uncomment if needed)
    # print_info "Creating Django superuser..."
    # python manage.py createsuperuser

    deactivate
    print_info "Django setup complete!"
}

# =============================================================================
# 8. Setup Systemd Services
# =============================================================================
setup_services() {
    print_info "Setting up systemd services..."

    # Copy service files
    cp $PROJECT_DIR/deployment/transcriptionbot-telegram.service /etc/systemd/system/
    cp $PROJECT_DIR/deployment/transcriptionbot-django.service /etc/systemd/system/

    # Reload systemd
    systemctl daemon-reload

    # Enable services
    systemctl enable transcriptionbot-telegram.service
    systemctl enable transcriptionbot-django.service

    print_info "Systemd services configured!"
}

# =============================================================================
# 9. Setup Nginx
# =============================================================================
setup_nginx() {
    print_info "Setting up Nginx..."

    # Create certbot directory
    mkdir -p /var/www/certbot

    # Copy nginx configuration
    cp $PROJECT_DIR/deployment/nginx-transcriptionbot.conf /etc/nginx/sites-available/transcriptionbot

    # Create symbolic link
    ln -sf /etc/nginx/sites-available/transcriptionbot /etc/nginx/sites-enabled/

    # Remove default site if exists
    rm -f /etc/nginx/sites-enabled/default

    # Test nginx configuration
    nginx -t

    print_info "Nginx configured!"
}

# =============================================================================
# 10. Setup SSL with Let's Encrypt
# =============================================================================
setup_ssl() {
    print_info "Setting up SSL certificate..."

    # Restart nginx
    systemctl restart nginx

    print_info "Obtaining SSL certificate..."
    certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

    # Setup auto-renewal
    systemctl enable certbot.timer

    print_info "SSL certificate configured!"
}

# =============================================================================
# 11. Start Services
# =============================================================================
start_services() {
    print_info "Starting services..."

    # Start Django
    systemctl start transcriptionbot-django.service
    systemctl status transcriptionbot-django.service --no-pager

    # Start Telegram Bot
    systemctl start transcriptionbot-telegram.service
    systemctl status transcriptionbot-telegram.service --no-pager

    # Restart Nginx
    systemctl restart nginx

    print_info "All services started!"
}

# =============================================================================
# Main Deployment Flow
# =============================================================================
main() {
    print_info "Starting TranscriptionBot deployment..."
    print_info "Domain: $DOMAIN"
    print_info "Project directory: $PROJECT_DIR"
    echo ""

    read -p "Continue with deployment? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Deployment cancelled."
        exit 1
    fi

    install_dependencies
    setup_database
    setup_redis
    setup_project
    setup_venv
    setup_env
    setup_django
    setup_services
    setup_nginx

    # Ask for SSL setup
    read -p "Setup SSL certificate with Let's Encrypt? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_ssl
    else
        print_warning "Skipping SSL setup. You can run it later with: certbot --nginx -d $DOMAIN"
    fi

    start_services

    echo ""
    print_info "============================================="
    print_info "Deployment completed successfully!"
    print_info "============================================="
    print_info "Website: https://$DOMAIN"
    print_info ""
    print_warning "Next steps:"
    print_warning "1. Edit /var/www/TranscriptionBot/.env with your configuration"
    print_warning "2. Update database password: sudo -u postgres psql"
    print_warning "3. Restart services: sudo systemctl restart transcriptionbot-*"
    print_warning "4. Check logs: sudo journalctl -u transcriptionbot-telegram -f"
    print_warning "              sudo journalctl -u transcriptionbot-django -f"
    print_info "============================================="
}

# Run main function
main
