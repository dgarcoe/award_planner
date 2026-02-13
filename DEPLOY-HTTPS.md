# QuendAward HTTPS Deployment Guide

This guide explains how to deploy QuendAward with HTTPS using Let's Encrypt certificates.

## Prerequisites

- A server with Docker and Docker Compose installed
- A domain name pointing to your server's IP address
- Ports 80 and 443 open in your firewall

## Quick Setup (Automated)

Run the setup script:

```bash
sudo ./setup-https.sh
```

The script will prompt you for:
- Your domain name (e.g., `quendaward.example.com`)
- Your email (for Let's Encrypt notifications)
- Admin callsign and password

## Manual Setup

If you prefer to set things up manually:

### Step 1: Configure Environment

Create a `.env` file:

```bash
cat > .env << EOF
DOMAIN=your-domain.com
ADMIN_CALLSIGN=YOUR_CALLSIGN
ADMIN_PASSWORD=your_secure_password
EOF
```

### Step 2: Update nginx.conf with your domain

Replace `${DOMAIN}` in `nginx/nginx.conf` with your actual domain:

```bash
sed -i "s/\${DOMAIN}/your-domain.com/g" nginx/nginx.conf
```

### Step 3: Create required directories

```bash
mkdir -p certbot/www certbot/conf data
```

### Step 4: Get initial certificate

First, start nginx with HTTP-only config:

```bash
# Use the init config temporarily
cp nginx/nginx-init.conf nginx/nginx.conf.bak

# Start only nginx
docker-compose -f docker-compose-standalone.yml up -d nginx
```

Request the certificate:

```bash
docker run --rm \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email your-email@example.com \
    --agree-tos \
    --no-eff-email \
    -d your-domain.com
```

### Step 5: Start the full stack

Restore the HTTPS nginx config and start everything:

```bash
# Restore HTTPS config (if you backed it up)
mv nginx/nginx.conf.bak nginx/nginx.conf

# Stop and restart
docker-compose -f docker-compose-standalone.yml down
docker-compose -f docker-compose-standalone.yml up -d
```

## Accessing the Application

Once deployed, access the application at:

```
https://your-domain.com/quendaward
```

## Certificate Renewal

Certificates are automatically renewed by the certbot container. It checks for renewal every 12 hours.

To manually renew:

```bash
docker-compose -f docker-compose-standalone.yml exec certbot certbot renew
docker-compose -f docker-compose-standalone.yml exec nginx nginx -s reload
```

## Troubleshooting

### Certificate generation fails

1. Ensure your domain DNS points to your server
2. Check that port 80 is accessible from the internet
3. Verify no other service is using port 80

```bash
# Check if port 80 is in use
sudo lsof -i :80
```

### Check nginx logs

```bash
docker-compose -f docker-compose-standalone.yml logs nginx
```

### Check application logs

```bash
docker-compose -f docker-compose-standalone.yml logs ham-coordinator
```

## Useful Commands

```bash
# Start the stack
docker-compose -f docker-compose-standalone.yml up -d

# Stop the stack
docker-compose -f docker-compose-standalone.yml down

# View logs
docker-compose -f docker-compose-standalone.yml logs -f

# Restart nginx after config changes
docker-compose -f docker-compose-standalone.yml restart nginx

# Rebuild after code changes
docker-compose -f docker-compose-standalone.yml up -d --build
```
