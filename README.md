# EJBCA CLM Agent - AI-Powered Certificate Lifecycle Management

⚠️ **PROJECT STATUS: UNDER ACTIVE DEVELOPMENT - FEATURES AND DOCUMENTATION ARE BEING UPDATED**

This project builds an **intelligent CLM (Certificate Lifecycle Management) Agent** powered by Claude AI Desktop integration. The agent automates certificate operations through EJBCA PKI infrastructure using the Model Context Protocol (MCP), enabling natural language interactions for complex certificate management tasks.

## Project Overview

This CLM Agent transforms traditional certificate management by providing:

- **🤖 AI-Powered Certificate Operations** - Natural language commands for certificate issuance, renewal, and revocation
- **🔌 Claude AI Desktop Integration** - Direct connection via MCP (Model Context Protocol) for seamless AI interactions  
- **🏗️ Containerized EJBCA Infrastructure** - Full PKI environment using Keyfactor's EJBCA Community Edition
- **🚀 Automated CLM Workflows** - Intelligent certificate lifecycle management with minimal human intervention
- **🔐 Enterprise-Grade Security** - Client certificate authentication and secure API access
- **📊 Certificate Analytics** - AI-driven insights into certificate health and lifecycle patterns

### Why This Agent?

Traditional Certificate Lifecycle Management requires:
- Deep PKI knowledge and manual processes
- Complex API integrations and scripting
- Time-consuming certificate provisioning workflows
- Manual monitoring and renewal processes

**Our CLM Agent enables:**
- Natural language certificate requests: *"Issue a SSL certificate for app.example.com valid for 2 years"*
- Automated renewal workflows: *"Check and renew certificates expiring in 30 days"*
- Intelligent certificate analytics: *"Show me certificate usage patterns and security risks"*
- Conversational troubleshooting: *"Why did the certificate validation fail?"*

## CLM Agent Features

### 🤖 AI-Powered Operations
- **Natural Language Processing** - Interact with certificates using plain English commands
- **Intelligent Decision Making** - AI-driven certificate policy recommendations
- **Automated Workflows** - Self-executing certificate lifecycle processes
- **Contextual Assistance** - Smart troubleshooting and guidance

### 🏗️ Infrastructure & Integration  
- **Claude AI Desktop Integration** - Direct MCP connection for seamless AI interactions
- **Containerized EJBCA Setup** - Full PKI environment with one-click deployment
- **RESTful API Access** - Programmatic certificate operations
- **Automated Credential Management** - Secure handling of PKI authentication

### 📋 Certificate Management
- **Automated Issuance** - AI-guided certificate creation and provisioning
- **Lifecycle Monitoring** - Intelligent tracking of certificate status and expiration
- **Renewal Automation** - Proactive certificate renewal workflows
- **Revocation Management** - Secure certificate revocation and CRL updates

## CLM Agent Architecture

```
┌─────────────────────┐    ┌──────────────────────┐
│   Claude AI Desktop │    │     Human User       │
│                     │◄──►│  (Natural Language)  │
└──────────┬──────────┘    └──────────────────────┘
           │ MCP Protocol
           │
┌──────────▼──────────┐    ┌──────────────────────┐
│   CLM Agent (MCP)   │    │    Web Browser       │
│  ejbca-mcp-server   │    │   (Admin Interface)  │
└──────────┬──────────┘    └──────────┬───────────┘
           │ REST API Calls           │ HTTPS/Cert Auth
           │                          │
       ┌───▼──────────────────────────▼────────────────┐
       │            EJBCA Container                    │
       │  ┌─────────────┐  ┌──────────────┐          │
       │  │  Admin Web  │  │  REST API    │          │
       │  │ Interface   │  │  Endpoint    │          │
       │  └─────────────┘  └──────────────┘          │
       │           PKI Certificate Store              │
       └─────────────────────────────────────────────┘
```

### Connection Flow:
1. **User** communicates with **Claude AI Desktop** in natural language
2. **Claude AI Desktop** connects to **CLM Agent** via MCP protocol (`mcp.json`)
3. **CLM Agent** translates AI requests into EJBCA REST API calls
4. **EJBCA** processes certificate operations and returns results
5. **Claude AI Desktop** provides intelligent responses and insights

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

## CLM Agent Integration with Claude AI Desktop

### Setting up MCP Connection

1. **Configure Claude AI Desktop MCP Settings**
   - Add the `mcp.json` configuration to Claude AI Desktop
   - This enables direct communication between Claude and the CLM Agent

2. **Start CLM Agent Server**
   ```bash
   python ejbca-mcp-server.py
   ```

3. **Connect Claude AI Desktop**
   - Claude AI Desktop will automatically connect to the CLM Agent via MCP
   - You can now use natural language commands for certificate operations

### Example CLM Agent Commands

Once connected to Claude AI Desktop, you can use commands like:

```
"Issue a new SSL certificate for example.com with 2-year validity"
"Show me all certificates expiring in the next 30 days"
"Revoke the certificate with serial number 123456789"
"Create a new certificate profile for web servers"
"Check the health of our certificate authority"
```

### MCP Configuration (`mcp.json`)

The `mcp.json` file configures the connection between Claude AI Desktop and the CLM Agent:
- Server endpoint and authentication
- Available certificate operations
- Security context and permissions

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
