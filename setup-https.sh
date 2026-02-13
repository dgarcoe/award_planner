#!/bin/bash

# QuendAward HTTPS Setup Script
# This script sets up Let's Encrypt SSL certificates for the application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  QuendAward HTTPS Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run this script with sudo or as root${NC}"
    exit 1
fi

# Check if docker and docker-compose are installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Determine docker-compose command
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Get domain from user
echo -e "${YELLOW}Enter your domain name (e.g., quendaward.example.com):${NC}"
read -r DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Domain cannot be empty${NC}"
    exit 1
fi

# Get email for Let's Encrypt
echo -e "${YELLOW}Enter your email for Let's Encrypt notifications:${NC}"
read -r EMAIL

if [ -z "$EMAIL" ]; then
    echo -e "${RED}Email cannot be empty${NC}"
    exit 1
fi

# Get admin credentials
echo -e "${YELLOW}Enter admin callsign (default: EA1RFI):${NC}"
read -r ADMIN_CALLSIGN
ADMIN_CALLSIGN=${ADMIN_CALLSIGN:-EA1RFI}

echo -e "${YELLOW}Enter admin password:${NC}"
read -rs ADMIN_PASSWORD

if [ -z "$ADMIN_PASSWORD" ]; then
    echo -e "${RED}Password cannot be empty${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Domain: $DOMAIN"
echo "  Email: $EMAIL"
echo "  Admin Callsign: $ADMIN_CALLSIGN"
echo ""

# Create .env file
echo -e "${GREEN}Creating .env file...${NC}"
cat > .env << EOF
DOMAIN=$DOMAIN
EMAIL=$EMAIL
ADMIN_CALLSIGN=$ADMIN_CALLSIGN
ADMIN_PASSWORD=$ADMIN_PASSWORD
EOF

# Create directories
echo -e "${GREEN}Creating directories...${NC}"
mkdir -p certbot/www certbot/conf data

# Update nginx.conf with domain
echo -e "${GREEN}Configuring nginx for domain: $DOMAIN${NC}"
sed "s/\${DOMAIN}/$DOMAIN/g" nginx/nginx.conf > nginx/nginx.conf.tmp
mv nginx/nginx.conf.tmp nginx/nginx.conf

# Step 1: Start with HTTP-only config to get initial certificate
echo -e "${GREEN}Step 1: Starting nginx with HTTP-only config...${NC}"
cp nginx/nginx-init.conf nginx/nginx-active.conf

# Temporarily use init config
$DOCKER_COMPOSE -f docker-compose-standalone.yml up -d nginx

# Wait for nginx to start
echo -e "${YELLOW}Waiting for nginx to start...${NC}"
sleep 5

# Step 2: Get the certificate
echo -e "${GREEN}Step 2: Requesting Let's Encrypt certificate...${NC}"
docker run --rm \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

# Check if certificate was created
if [ ! -f "certbot/conf/live/$DOMAIN/fullchain.pem" ]; then
    echo -e "${RED}Certificate generation failed!${NC}"
    echo -e "${RED}Make sure your domain points to this server and port 80 is accessible.${NC}"
    $DOCKER_COMPOSE -f docker-compose-standalone.yml down
    exit 1
fi

echo -e "${GREEN}Certificate obtained successfully!${NC}"

# Step 3: Restart with full HTTPS config
echo -e "${GREEN}Step 3: Restarting with HTTPS configuration...${NC}"
$DOCKER_COMPOSE -f docker-compose-standalone.yml down
$DOCKER_COMPOSE -f docker-compose-standalone.yml up -d

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Your QuendAward application is now available at:"
echo -e "  ${GREEN}https://$DOMAIN/quendaward${NC}"
echo ""
echo -e "Admin credentials:"
echo -e "  Callsign: ${GREEN}$ADMIN_CALLSIGN${NC}"
echo -e "  Password: ${GREEN}(as configured)${NC}"
echo ""
echo -e "${YELLOW}Note: Certificates will auto-renew via the certbot container.${NC}"
echo ""
