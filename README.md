# EJBCA PKI Management System

This project provides a containerized EJBCA (Enterprise Java Bean Certificate Authority) setup with MCP (Model Context Protocol) server integration for automated certificate management operations.

## Project Overview

EJBCA is an open-source Public Key Infrastructure (PKI) Certificate Authority software that provides a robust platform for managing digital certificates. This setup includes:

- **Containerized EJBCA CE (Community Edition)** using Keyfactor's official Docker image
- **MCP Server Integration** for automated certificate operations via API
- **Automated Setup Scripts** for quick deployment and credential extraction
- **REST API Configuration** for programmatic certificate management
- **Client Certificate Authentication** for secure API access

## Features

- 🔐 **Certificate Authority Management** - Issue, revoke, and manage digital certificates
- 🚀 **Automated Deployment** - One-click setup with Docker Compose
- 🔑 **Credential Extraction** - Automatic SuperAdmin credential capture from logs
- 🌐 **Web Interface** - Browser-based administration interface
- 🔌 **REST API** - Programmatic access to certificate operations
- 🐍 **Python Integration** - MCP server for certificate automation
- 📜 **Certificate Profiles** - Customizable certificate templates and policies

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   MCP Server     │    │   Client Apps   │
│  (Admin UI)     │    │  (Python)        │    │   (API Users)   │
└─────────┬───────┘    └────────┬─────────┘    └─────────┬───────┘
          │                     │                        │
          │ HTTPS/Cert Auth     │ REST API               │ REST API
          │                     │                        │
      ┌───▼─────────────────────▼────────────────────────▼───┐
      │              EJBCA Container                        │
      │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │
      │  │  Admin Web  │  │  Public Web  │  │  REST API   │ │
      │  │Interface    │  │  Interface   │  │  Endpoint   │ │
      │  └─────────────┘  └──────────────┘  └─────────────┘ │
      └─────────────────────────────────────────────────────┘
```

## Demo Video

[![EJBCA Agent Setup Demo](https://img.youtube.com/vi/ACwgBqdAwKI/0.jpg)](https://www.youtube.com/watch?v=ACwgBqdAwKI)

Watch the complete setup and configuration process in action.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- curl command available
- OpenSSL tools (for certificate operations)
- Firefox browser (recommended for certificate import)

### 1. Automated Setup

Run the automated setup script to deploy EJBCA and extract credentials:

```bash
chmod +x setup.sh
./setup.sh
```

This script will:
- Start the EJBCA container using Docker Compose
- Monitor container logs for SuperAdmin credentials
- Extract username and enrollment password
- Save credentials to `credentials.txt`
- Create environment configuration in `.env`
- Test basic connectivity

### 2. Manual Certificate Enrollment

After the automated setup completes:

1. **Access Admin Interface**
   ```
   URL: https://localhost/ejbca/adminweb/
   ```

2. **Download SuperAdmin Certificate**
   - Use the enrollment password from `credentials.txt`
   - Download `SuperAdmin.p12` certificate file

3. **Import Certificate to Browser**
   - Open Firefox browser
   - Go to Settings → Privacy & Security → Certificates → View Certificates
   - Import the `SuperAdmin.p12` file
   - Enter the enrollment password when prompted

4. **Extract Certificate Files for API Access**
   ```bash
   chmod +x cert.sh
   ./cert.sh
   ```
   This will extract the certificate and private key to the `certs/` directory:
   - `certs/client.pem` - Client certificate
   - `certs/client.key` - Private key

5. **Access Admin Interface with Certificate**
   - Navigate to `https://localhost/ejbca/adminweb/`
   - Select the SuperAdmin certificate when prompted
   - You should now have full administrative access

### 3. Enable REST API

The REST API is disabled by default and must be manually enabled:

1. **Access Admin Interface** (with SuperAdmin certificate)
2. **Navigate to System Configuration**
   - Go to `System Configuration` → `Protocol Configuration`
3. **Enable REST API**
   - Check "Enable REST API"
   - Configure allowed IP addresses (or use 0.0.0.0/0 for testing)
   - Save configuration
4. **Restart Container** (if required)
   ```bash
   docker-compose restart ejbca
   ```

## Configuration Files

### Docker Compose Configuration

The `docker-compose.yaml` file contains:
- EJBCA container configuration using `keyfactor/ejbca-ce:latest`
- Port mappings (80→8080, 443→8443)
- Volume mounts for persistence
- TLS setup enabled for automatic certificate generation

### Environment Variables

The `.env` file contains:
```bash
EJBCA_BASE_URL=https://localhost
EJBCA_ADMIN_URL=https://localhost/ejbca/adminweb/
EJBCA_PUBLIC_URL=https://localhost/ejbca/
EJBCA_VERIFY_SSL=false
SUPERADMIN_USER=SuperAdmin
ENROLLMENT_PASSWORD=<extracted_from_logs>
```

### Credentials File

The `credentials.txt` file contains:
- SuperAdmin username and enrollment password
- Admin and public web interface URLs
- Access instructions and manual steps
- Container log extracts with credential information

## API Usage

Once REST API is enabled and client certificates are configured:

### Test API Connectivity
```bash
curl -k --cert ./certs/client.pem --key ./certs/client.key \
     https://localhost/ejbca/ejbca-rest-api/v1/ca
```

### List Certificate Authorities
```bash
curl -k --cert ./certs/client.pem --key ./certs/client.key \
     https://localhost/ejbca/ejbca-rest-api/v1/ca | jq .
```

### Health Check
```bash
curl -k https://localhost/ejbca/publicweb/healthcheck/ejbcahealth
```

## MCP Server Integration

The `ejbca-mcp-server.py` provides Model Context Protocol integration for:
- Automated certificate issuance
- Certificate revocation operations
- CA management tasks
- End entity profile management

### Running MCP Server
```bash
python ejbca-mcp-server.py
```

## Directory Structure

```
ejbca/
├── README.md                 # This documentation
├── docker-compose.yaml       # Container orchestration
├── setup.sh                 # Automated setup script
├── credentials.txt          # Generated credentials (after setup)
├── .env                     # Environment variables (after setup)
├── ejbca-mcp-server.py      # MCP server implementation
├── mcp.json                 # MCP configuration
├── requirements.txt         # Python dependencies
├── certs/                   # Certificate storage directory
│   ├── ca.pem              # CA certificate (if extracted)
│   ├── client.pem          # Client certificate (if configured)
│   └── client.key          # Client private key (if configured)
└── venv/                    # Python virtual environment
```

## Troubleshooting

### Container Issues
```bash
# Check container status
docker-compose ps

# View container logs
docker-compose logs ejbca

# Restart container
docker-compose restart ejbca
```

### Certificate Issues
```bash
# Test EJBCA health
curl -k https://localhost/ejbca/publicweb/healthcheck/ejbcahealth

# Check certificate validity
openssl x509 -in ./certs/client.pem -text -noout
```

### API Access Issues
1. Verify REST API is enabled in admin interface
2. Check client certificate is properly imported
3. Ensure correct API endpoints are being used
4. Review EJBCA logs for authentication errors

## Security Considerations

⚠️ **Important Security Notes:**

- This setup is configured for **development/testing purposes**
- SSL verification is disabled (`EJBCA_VERIFY_SSL=false`)
- Default ports (80/443) are exposed
- No database persistence beyond Docker volumes
- SuperAdmin credentials are stored in plain text files

For production use:
- Enable SSL certificate verification
- Use proper SSL certificates
- Implement database backup strategies
- Secure credential storage
- Configure firewall rules
- Regular security updates

## Support

For EJBCA-specific issues, refer to:
- [EJBCA Community Edition Documentation](https://docs.keyfactor.com/ejbca/)
- [Keyfactor EJBCA Docker Hub](https://hub.docker.com/r/keyfactor/ejbca-ce)
- [EJBCA Community Forum](https://community.ejbca.org/)

## License

This project configuration is provided as-is for educational and development purposes. EJBCA Community Edition has its own licensing terms - please refer to the official EJBCA documentation for licensing information.
