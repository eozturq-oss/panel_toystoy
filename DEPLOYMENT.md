# Production Deployment Guide

This guide deploys the toy marketplace to a clean Ubuntu/Debian VPS with Docker Compose.

## 1. Prepare the VPS

Connect as a sudo-enabled user, then update the server:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl git ufw
```

Allow SSH and HTTP. Add HTTPS after installing TLS at your reverse proxy:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

## 2. Install Docker Engine and Compose

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo ${VERSION_CODENAME}) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
newgrp docker
docker run --rm hello-world
docker compose version
```

For Debian, replace the Docker apt URL path with the official Debian instructions for the server release.

## 3. Create a private Git repository and push locally

Create an empty **private** repository on GitHub or GitLab. Do not initialize it with a README if this local project already has files.

On the local machine:

```bash
git init
git add .
git commit -m "Initial production-ready marketplace integration"
git branch -M main
git remote add origin git@github.com:YOUR_ORG/toy-marketplace.git
git push -u origin main
```

For GitLab, replace the remote with:

```bash
git remote add origin git@gitlab.com:YOUR_GROUP/toy-marketplace.git
```

Use an SSH deploy key or a short-lived access token. Never add `.env`, API keys, database passwords, or cloud credentials to Git. Check before pushing:

```bash
git status --short
git ls-files .env .env.production
```

The second command must print nothing.

## 4. Clone the project

```bash
sudo mkdir -p /opt/toy-marketplace
sudo chown -R "$USER":"$USER" /opt/toy-marketplace
git clone <YOUR_GIT_REPOSITORY_URL> /opt/toy-marketplace
cd /opt/toy-marketplace
```

For an existing checkout:

```bash
git pull --ff-only
```

## 5. Create production environment values

```bash
cp .env.production.example .env
chmod 600 .env
nano .env
```

Replace every `CHANGE_ME` value, especially:

- `POSTGRES_PASSWORD`
- `TRENDYOL_API_KEY` and `TRENDYOL_API_SECRET`
- `HEPSIBURADA_USERNAME` and `HEPSIBURADA_PASSWORD`
- AWS/S3 credentials and public image URL
- `DEFAULT_TENANT_ID`

Use a long random database password and make sure the `DATABASE_URL` password matches it. Never commit `.env`.

## 6. Build and start all services

```bash
docker compose up -d --build
```

The compose stack starts:

- `postgres`: persistent PostgreSQL database
- `redis`: persistent Redis queue/cache service
- `api`: FastAPI application
- `scheduler`: background order polling and inventory synchronization
- `frontend`: React production build served by Nginx

The public HTTP port is `80`; PostgreSQL and Redis remain private on the Docker network.

## 7. One-command deployment and sanity check

Make the helper scripts executable and run the checks:

```bash
chmod +x scripts/*.sh
./scripts/vps_sanity_check.sh
./scripts/deploy.sh
```

`deploy.sh` validates `.env`, runs `docker compose config`, builds and starts the stack, waits for API health, runs database/Redis sanity checks, and executes the zero-API-call dry-run.

## 8. Marketplace API preflight and dry-run

Run this on the VPS or in the backend image before enabling live submissions:

```bash
docker compose exec api python scripts/dry_run_marketplace.py --marketplace all
./scripts/health_check.sh
```

The script makes zero marketplace HTTP calls (`api_calls: 0`). It validates EAN/UPC barcode, CE, age group, minimum age, gender, material, and piece count, then prints Trendyol and Hepsiburada payloads.

Keep `MARKETPLACE_DRY_RUN=true` until the payload output is reviewed. Set it to `false` only after sandbox/live credentials and category IDs are confirmed.

## 9. Verify the deployment

```bash
docker compose ps
curl http://127.0.0.1/health
docker compose logs --tail=100 api
docker compose logs --tail=100 scheduler
```

Expected health response:

```json
{"status":"ok"}
```

## 10. Operations

```bash
docker compose logs -f scheduler
docker compose restart scheduler
docker compose pull
docker compose up -d --build
docker compose down
```

For live debugging:

```bash
./scripts/vps_debug.sh scheduler
docker compose logs -f --timestamps api scheduler
```

`postgres_data` and `redis_data` are named volumes. Back them up before destructive maintenance:

```bash
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

## Security checklist

- Keep `.env` at mode `600` and outside version control.
- Put the public service behind HTTPS using Caddy, Nginx Proxy Manager, or a cloud load balancer.
- Do not publish PostgreSQL or Redis ports to the host.
- Restrict SSH to keys and disable password login after confirming key access.
- Run `docker compose config` before deployment to inspect interpolated configuration without printing secrets in shared logs.
- Replace `Base.metadata.create_all()` with an Alembic migration command before the first production schema migration.
