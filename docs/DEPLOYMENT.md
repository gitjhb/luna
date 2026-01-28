# AI Companion Platform - Deployment Guide

This guide provides comprehensive instructions for deploying the AI Companion Platform using Docker.

## Prerequisites

Before deploying, ensure you have the following installed:

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Make**: (Optional) For using Makefile commands

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ai-companion-backend-final
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your actual values:

```bash
cp .env.example .env
```

Edit `.env` and provide the following required values:

- `POSTGRES_PASSWORD`: Strong password for PostgreSQL
- `REDIS_PASSWORD`: Strong password for Redis
- `FIREBASE_PROJECT_ID`: Your Firebase project ID
- `XAI_API_KEY`: Your xAI Grok API key
- `PINECONE_API_KEY`: Your Pinecone API key
- `OPENAI_API_KEY`: Your OpenAI API key (for embeddings)
- `JWT_SECRET_KEY`: A secure random string (minimum 32 characters)
- `STRIPE_API_KEY`: Your Stripe API key (if using payments)

### 3. Add Firebase Credentials

Place your Firebase service account credentials file in the project root:

```bash
cp /path/to/your/firebase-credentials.json ./firebase-credentials.json
```

### 4. Build and Start Services

Using Make (recommended):

```bash
make build
make up
```

Or using Docker Compose directly:

```bash
docker-compose build
docker-compose up -d
```

### 5. Verify Deployment

Check that all services are running:

```bash
docker-compose ps
```

Check the API health:

```bash
curl http://localhost:8000/health
```

You should see a response like:

```json
{
  "status": "healthy",
  "timestamp": "2026-01-28T12:00:00.000000",
  "version": "1.0.0"
}
```

## Service Architecture

The deployment includes the following services:

| Service | Port | Description |
|---------|------|-------------|
| **api** | 8000 | FastAPI application |
| **postgres** | 5432 | PostgreSQL database |
| **redis** | 6379 | Redis cache and rate limiting |
| **nginx** | 80, 443 | Reverse proxy (production profile) |

## Common Operations

### View Logs

View logs from all services:

```bash
make logs
```

View logs from a specific service:

```bash
docker-compose logs -f api
```

### Access Service Shells

**API Container:**

```bash
make shell
```

**PostgreSQL:**

```bash
make db-shell
```

**Redis:**

```bash
make redis-shell
```

### Restart Services

Restart all services:

```bash
make restart
```

Restart a specific service:

```bash
docker-compose restart api
```

### Stop Services

Stop all services:

```bash
make down
```

Stop and remove all data (including volumes):

```bash
make clean
```

## Production Deployment

For production deployment, follow these additional steps:

### 1. Enable HTTPS

1. Obtain SSL certificates (e.g., from Let's Encrypt)
2. Place certificates in `./nginx/ssl/`
3. Uncomment the HTTPS server block in `nginx/nginx.conf`
4. Update the `server_name` directive with your domain

### 2. Start with Production Profile

```bash
make up-prod
```

This starts all services including Nginx as a reverse proxy.

### 3. Configure Firewall

Ensure the following ports are open:

- **80**: HTTP (for Let's Encrypt challenges and redirect)
- **443**: HTTPS (for secure API access)

Block direct access to:

- **5432**: PostgreSQL (internal only)
- **6379**: Redis (internal only)
- **8000**: API (access through Nginx only)

### 4. Set Up Database Backups

Create a backup script:

```bash
#!/bin/bash
docker-compose exec -T postgres pg_dump -U postgres ai_companion > backup_$(date +%Y%m%d_%H%M%S).sql
```

Schedule it with cron:

```bash
0 2 * * * /path/to/backup-script.sh
```

### 5. Enable Monitoring

Consider adding monitoring services like:

- **Prometheus**: For metrics collection
- **Grafana**: For visualization
- **Sentry**: For error tracking

## Scaling

### Horizontal Scaling

To scale the API service:

```bash
docker-compose up -d --scale api=3
```

Update Nginx configuration to load balance across multiple API instances.

### Vertical Scaling

Adjust resource limits in `docker-compose.yml`:

```yaml
api:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

## Troubleshooting

### Service Won't Start

Check logs:

```bash
docker-compose logs api
```

Common issues:

1. **Port already in use**: Change the port in `.env`
2. **Missing environment variables**: Check `.env` file
3. **Database connection failed**: Ensure PostgreSQL is healthy

### Database Connection Issues

Check PostgreSQL status:

```bash
docker-compose exec postgres pg_isready -U postgres
```

Reset the database:

```bash
docker-compose down -v
docker-compose up -d
```

### Performance Issues

Check resource usage:

```bash
make stats
```

Increase worker count in `Dockerfile`:

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8"]
```

## Maintenance

### Update Application

1. Pull latest code:
   ```bash
   git pull origin main
   ```

2. Rebuild and restart:
   ```bash
   make build
   make restart
   ```

### Database Migrations

Run migrations:

```bash
make migrate
```

Or manually:

```bash
docker-compose exec api alembic upgrade head
```

### Clean Up Old Images

Remove unused Docker images:

```bash
docker image prune -a
```

## Security Checklist

- [ ] Change all default passwords in `.env`
- [ ] Use strong, unique passwords (minimum 32 characters)
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Restrict database and Redis access to internal network only
- [ ] Set up firewall rules
- [ ] Enable Docker security features (AppArmor, Seccomp)
- [ ] Regularly update Docker images
- [ ] Set up automated backups
- [ ] Enable logging and monitoring
- [ ] Review and limit CORS origins

## Support

For issues or questions, please refer to the main README or open an issue on GitHub.

---

**Last Updated**: January 28, 2026  
**Author**: Manus AI
