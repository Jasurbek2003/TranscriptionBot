# TranscriptionBot - Setup Guide

Quick setup guide for the new code quality and DevOps features.

---

## 🚀 Quick Start

### 1. Install Pre-commit Hooks (5 minutes)

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# Run on all files (optional, to see what would be checked)
pre-commit run --all-files
```

Now, every time you commit code, it will automatically:

- Format with Black
- Sort imports with isort
- Check linting with Flake8
- Check types with mypy
- Scan for security issues with Bandit

---

### 2. Setup Sentry Monitoring (10 minutes)

```bash
# 1. Go to https://sentry.io and create an account (free tier available)
# 2. Create a new Django project
# 3. Copy your DSN (looks like: https://xxx@sentry.io/123456)

# 4. Add to your .env file:
echo "SENTRY_DSN=your-dsn-here" >> .env
echo "SENTRY_ENABLED=true" >> .env
echo "SENTRY_ENVIRONMENT=production" >> .env

# 5. Restart your Django server
# That's it! Sentry is now tracking errors
```

**Test it:**

```python
# In Django shell
from config.sentry_config import capture_message
capture_message("Test message from TranscriptionBot")

# Check your Sentry dashboard - you should see the message!
```

---

### 3. Test Health Checks (2 minutes)

```bash
# Start your Django server
cd django_admin
python manage.py runserver

# In another terminal, test the endpoints:

# Basic health check
curl http://localhost:8000/health/
# Response: {"status": "healthy", ...}

# Readiness check (checks database + redis)
curl http://localhost:8000/ready/
# Response: {"status": "ready", "checks": {"database": true, "cache": true}, ...}

# Detailed status (admin only)
curl http://localhost:8000/status/
# Response: {"status": "operational", "application": {...}, "checks": {...}}
```

**Use in Production:**

- **Kubernetes:** Configure liveness/readiness probes
- **Docker:** Add healthcheck to docker-compose.yml
- **Load Balancer:** Point health checks to `/ready/`

---

### 4. Run Tests (5 minutes)

```bash
# Install test dependencies (if not already)
pip install pytest pytest-django pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=html

# View coverage report in browser
# Open htmlcov/index.html

# Run specific test file
pytest django_admin/apps/transactions/tests/test_click_webhook.py
```

**What's tested:**

- ✅ Click payment webhook (prepare, complete, errors)
- ✅ Payme payment webhook (all 6 RPC methods)
- ✅ Signature verification
- ✅ Transaction status updates
- ✅ Wallet balance updates

---

### 5. Setup GitHub Actions (Optional, 15 minutes)

```bash
# 1. Push your code to GitHub
git add .
git commit -m "Add code quality improvements"
git push origin main

# 2. Go to your GitHub repository
# 3. Click "Actions" tab
# 4. You'll see two workflows:
#    - CI/CD Pipeline
#    - Security Checks

# 5. (Optional) Add secrets for deployment:
# Go to Settings -> Secrets and variables -> Actions
# Add:
# - DOCKER_USERNAME (if using Docker Hub)
# - DOCKER_PASSWORD
# - SSH_HOST (for deployment)
# - SSH_USER
# - SSH_KEY
```

**What runs automatically:**

- ✅ Code linting and formatting checks
- ✅ Test suite with coverage
- ✅ Security scans (Bandit, Safety, Gitleaks, CodeQL)
- ✅ Docker image build
- ✅ Deployment (on main branch)

---

## 🔧 Configuration Files

All configuration is in:

```
TranscriptionBot/
├── .pre-commit-config.yaml      # Pre-commit hooks
├── .flake8                       # Linting rules
├── pyproject.toml                # Black, isort, mypy, pytest config
├── .github/workflows/
│   ├── ci.yml                    # Main CI/CD pipeline
│   └── security.yml              # Security scanning
├── django_admin/config/
│   ├── health_checks.py          # Health check endpoints
│   └── sentry_config.py          # Sentry configuration
```

---

## 📋 Daily Workflow

### Before Committing

```bash
# 1. Make your changes
vim bot/handlers/payment.py

# 2. Pre-commit will run automatically on commit
git add .
git commit -m "Add payment feature"

# If pre-commit fails:
# - It will auto-fix formatting issues
# - Review and commit the fixes
git add .
git commit -m "Add payment feature"

# 3. Push to GitHub
git push
```

### Monitoring in Production

```bash
# 1. Check Sentry dashboard for errors
#    https://sentry.io/organizations/your-org/issues/

# 2. Check health endpoints
curl https://your-domain.com/ready/

# 3. View GitHub Actions for build status
#    https://github.com/your-org/TranscriptionBot/actions
```

---

## 🐛 Troubleshooting

### Pre-commit Hook Fails

```bash
# Update hooks
pre-commit autoupdate

# Run manually to see errors
pre-commit run --all-files

# Skip hooks temporarily (not recommended)
git commit --no-verify
```

### Tests Failing

```bash
# Check test database
python django_admin/manage.py migrate

# Run with verbose output
pytest -v

# Run specific failing test
pytest django_admin/apps/transactions/tests/test_click_webhook.py::ClickWebhookTest::test_click_prepare_success -v
```

### Sentry Not Working

```bash
# Check configuration
python -c "from django_admin.config.sentry_config import init_sentry; init_sentry()"

# Check environment variables
echo $SENTRY_DSN
echo $SENTRY_ENABLED

# Test manually
python django_admin/manage.py shell
>>> from config.sentry_config import capture_message
>>> capture_message("Test")
```

### Health Check Returns 503

```bash
# Check database
python django_admin/manage.py dbshell

# Check Redis
redis-cli ping

# View detailed error
curl http://localhost:8000/ready/ | jq
```

---

## 📚 Additional Resources

- **Code Quality Improvements:** See `CODE_QUALITY_IMPROVEMENTS.md`
- **Pre-commit Docs:** https://pre-commit.com/
- **Sentry Docs:** https://docs.sentry.io/
- **GitHub Actions Docs:** https://docs.github.com/actions
- **Pytest Docs:** https://docs.pytest.org/

---

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] `pre-commit run --all-files` passes
- [ ] `pytest` all tests pass
- [ ] `curl http://localhost:8000/health/` returns 200
- [ ] `curl http://localhost:8000/ready/` returns 200
- [ ] Sentry dashboard shows test message
- [ ] GitHub Actions pipeline is green

---

**Need Help?** Check the troubleshooting section or open an issue on GitHub.
