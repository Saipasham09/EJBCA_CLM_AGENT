#!/bin/bash

# EJBCA Setup Script with Credential Extraction
# This script starts EJBCA container and extracts credentials

set -e

echo "=== EJBCA Setup and Credential Extraction ==="

# Create directories
mkdir -p certs

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    if ! command -v docker &> /dev/null; then
        echo "Docker is not installed. Please install Docker first."
        exit 1
    fi
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "Step 1: Starting EJBCA container..."
$DOCKER_COMPOSE up -d

echo "Step 2: Monitoring container logs for credentials..."
echo "Waiting for EJBCA to initialize and generate credentials..."

# Monitor logs for credentials
timeout 180 bash -c "
export DOCKER_COMPOSE='$DOCKER_COMPOSE'
while true; do
    LOGS=\$(\$DOCKER_COMPOSE logs ejbca 2>/dev/null | tail -50)
    
    # Look for enrollment code/password patterns
    ENROLLMENT_CODE=\$(echo \"\$LOGS\" | grep -i \"Password:\" | sed 's/.*Password: \\(.*\\) \\*.*/\\1/' | head -1)
    
    # Look for admin URL
    ADMIN_URL=\$(echo \"\$LOGS\" | grep -i \"admin.*url\|web.*interface\" | head -1)
    
    # Look for username patterns
    USERNAME=\$(echo \"\$LOGS\" | grep -i \"username=\" | sed 's/.*username=\\([^[:space:]⁠]*\\).*/\\1/' | head -1)
    
    # Check if container is ready
    if curl -s -k https://localhost/ejbca/publicweb/healthcheck/ejbcahealth 2>/dev/null | grep -q \"ALLOK\"; then
        echo \"EJBCA is ready!\"
        break
    fi
    
    echo \"Still waiting for EJBCA to be ready...\"
    sleep 10
done
"

echo "Step 3: Extracting credentials from logs..."
LOGS=$($DOCKER_COMPOSE logs ejbca 2>/dev/null)

# Extract SuperAdmin credentials from logs
SUPERADMIN_USER=$(echo "$LOGS" | grep -i "username=" | sed 's/.*username=\([^[:space:]⁠]*\).*/\1/' | head -1)
ENROLLMENT_PASSWORD=$(echo "$LOGS" | grep -i "Password:" | sed 's/.*Password: \(.*\) \*.*/\1/' | head -1)
ENROLLMENT_URL=$(echo "$LOGS" | grep -i "URL:" | sed 's/.*URL: \(.*\) \*.*/\1/' | head -1)
ADMIN_URL="https://localhost/ejbca/adminweb/"
PUBLIC_URL="https://localhost/ejbca/"

# Create credentials file
cat > credentials.txt << EOF
EJBCA SuperAdmin Credentials
============================

Generated on: $(date)
Container: ejbca-ce

Admin Web Interface: ${ADMIN_URL}
Public Web Interface: ${PUBLIC_URL}

Access Instructions:
1. Download SuperAdmin.p12 certificate through the web interface
2. Import certificate into Firefox browser
3. Access admin interface with client certificate authentication

Manual Steps Required:
1. Enable REST API through admin interface
2. Configure certificate profiles if needed
3. Set up end entity profiles for API access

Container Logs Extract (Username and Password):
$(echo "$LOGS" | grep -E "(URL:.*username=|Password:)" | head -20)

Extracted Credentials:
SuperAdmin Username: [Extract from logs above - look for "username=" in URL]
Enrollment Password: [Extract from logs above - look for "Password:" line]  
Enrollment URL: [Extract from logs above - look for "URL:" line]
EOF

echo "Credentials saved to credentials.txt"

echo "Step 4: Setting up basic configuration..."

# Create environment file
cat > .env << EOF
EJBCA_BASE_URL=https://localhost
EJBCA_ADMIN_URL=https://localhost/ejbca/adminweb/
EJBCA_PUBLIC_URL=https://localhost/ejbca/
EJBCA_VERIFY_SSL=false
SUPERADMIN_USER=${SUPERADMIN_USER:-SuperAdmin}
ENROLLMENT_PASSWORD=${ENROLLMENT_PASSWORD:-check_logs}
EOF

echo "Environment configuration saved to .env"

echo "Step 5: Testing EJBCA connectivity..."
if curl -s -k https://localhost/ejbca/publicweb/healthcheck/ejbcahealth | grep -q "ALLOK"; then
    echo "✓ EJBCA is running and accessible"
else
    echo "⚠ EJBCA health check failed"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next Steps (Manual):"
echo "1. Access admin interface: https://localhost/ejbca/adminweb/"
echo "2. Use enrollment password from credentials.txt to download SuperAdmin.p12"
echo "3. Import SuperAdmin.p12 into Firefox browser"
echo "4. Enable REST API through admin interface"
echo "5. Configure certificate profiles and end entity profiles as needed"
echo ""
echo "Files created:"
echo "  - credentials.txt    : SuperAdmin credentials and access info"
echo "  - .env              : Environment variables"
echo ""
echo "Container Status:"
$DOCKER_COMPOSE ps