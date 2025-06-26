#!/usr/bin/env python3
"""
EJBCA MCP Server - Enhanced Implementation
Built from scratch based on EJBCA 9.1.1 REST API documentation and current MCP SDK
Updated with fixes for CRL APIs based on official Keyfactor EJBCA SDK patterns
"""

import asyncio
import json
import logging
import os
import subprocess
from typing import Any, Dict, List
import warnings
import requests
import urllib3

# Suppress SSL warnings
warnings.filterwarnings('ignore')
urllib3.disable_warnings()

# MCP imports with proper compatibility
try:
    from mcp.server.lowlevel import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError as e:
    print(f"MCP library not found: {e}")
    print("Install with: pip install mcp")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ejbca-mcp")

class EJBCARestClient:
    """
    EJBCA REST API client based on official EJBCA 9.1.1 documentation
    
    Implements the official REST API endpoints:
    - /ejbca/ejbca-rest-api/v1/ca/ (CA operations)
    - /ejbca/ejbca-rest-api/v1/certificate/ (Certificate operations) 
    - /ejbca/ejbca-rest-api/v1/endentity/ (End Entity operations - Enterprise)
    """
    
    def __init__(self, base_url: str, cert_path: str, key_path: str):
        self.base_url = base_url.rstrip('/')
        self.cert_path = cert_path
        self.key_path = key_path
        
        # Check certificate files
        self.has_certificates = (
            cert_path and key_path and 
            os.path.exists(cert_path) and os.path.exists(key_path)
        )
        
        if not self.has_certificates:
            logger.warning(f"Certificate files missing: {cert_path}, {key_path}")
        
        # Setup requests session for EJBCA
        self.session = requests.Session()
        self.session.verify = False  # Skip SSL verification for self-signed certs
        
        if self.has_certificates:
            self.session.cert = (cert_path, key_path)
        
        # Required headers for EJBCA REST API (from documentation)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Keyfactor-Requested-With': 'XMLHttpRequest'  # Required by EJBCA
        })
    
    def _curl_fallback(self, method: str, endpoint: str, data: dict = None) -> Dict[str, Any]:
        """
        Fallback to curl command when requests library fails
        Uses the same approach as official EJBCA documentation examples
        """
        if not self.has_certificates:
            return {"error": "No certificates available for authentication"}
        
        try:
            url = f"{self.base_url}/ejbca/ejbca-rest-api/v1/{endpoint}"
            
            # Build curl command as shown in EJBCA docs
            cmd = [
                'curl', '-s', '-k',
                '--cert', self.cert_path,
                '--key', self.key_path,
                '-H', 'X-Keyfactor-Requested-With: XMLHttpRequest',
                '-H', 'Content-Type: application/json',
                '-H', 'Accept: application/json'
            ]
            
            if method.upper() == 'POST' and data:
                cmd.extend(['-X', 'POST', '-d', json.dumps(data)])
            elif method.upper() == 'PUT' and data:
                cmd.extend(['-X', 'PUT', '-d', json.dumps(data)])
            
            cmd.append(url)
            
            # Execute curl with timeout
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout:
                try:
                    response = json.loads(result.stdout)
                    response["_method"] = "curl"
                    return response
                except json.JSONDecodeError:
                    return {
                        "response": result.stdout,
                        "success": True,
                        "_method": "curl"
                    }
            else:
                return {
                    "error": f"Curl failed (exit code: {result.returncode})",
                    "stderr": result.stderr,
                    "_method": "curl"
                }
                
        except subprocess.TimeoutExpired:
            return {"error": "Request timed out", "_method": "curl"}
        except Exception as e:
            return {"error": f"Curl command failed: {str(e)}", "_method": "curl"}
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to EJBCA REST API with automatic fallback
        Implements the URL structure from EJBCA documentation:
        https://[DOMAIN]:[PORT]/ejbca/ejbca-rest-api/[VERSION]/[RESOURCE]/[OPERATION]
        """
        
        # Debug logging
        logger.info(f"Making {method} request to endpoint: {endpoint}")
        
        # Try requests library first
        if self.has_certificates:
            try:
                url = f"{self.base_url}/ejbca/ejbca-rest-api/v1/{endpoint}"
                logger.info(f"Full URL: {url}")
                response = self.session.request(method, url, timeout=30, **kwargs)
                
                logger.info(f"Response status code: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        result["_method"] = "requests"
                        result["_status_code"] = response.status_code
                        return result
                    except json.JSONDecodeError:
                        # Handle binary responses (like CRL data)
                        if response.headers.get('content-type', '').startswith('application/pkix-crl'):
                            return {
                                "crl_data": response.content,
                                "content_type": response.headers.get('content-type'),
                                "content_length": len(response.content),
                                "success": True,
                                "_method": "requests",
                                "_status_code": response.status_code
                            }
                        else:
                            return {
                                "response": response.text,
                                "success": True,
                                "_method": "requests",
                                "_status_code": response.status_code
                            }
                else:
                    error_result = {
                        "error": f"HTTP {response.status_code}",
                        "message": response.text[:500] if response.text else "",
                        "_method": "requests",
                        "_status_code": response.status_code,
                        "_url": url
                    }
                    logger.warning(f"HTTP error response: {error_result}")
                    return error_result
                    
            except Exception as e:
                logger.warning(f"Requests failed: {e}, trying curl fallback")
        
        # Fallback to curl
        data = kwargs.get('json') if 'json' in kwargs else None
        return self._curl_fallback(method, endpoint, data)
    
    # EJBCA REST API Methods based on official documentation
    
    def get_certificate_api_status(self) -> Dict[str, Any]:
        """
        GET /certificate/status
        Returns the status of the Certificate Management REST API
        """
        return self._make_request("GET", "certificate/status")
    
    def get_ca_list(self) -> Dict[str, Any]:
        """
        GET /ca
        Get a list of authorized CAs 
        """
        return self._make_request("GET", "ca")
    
    def get_ca_version(self) -> Dict[str, Any]:
        """
        GET /ca/version  
        Get version information for the CA REST API
        """
        return self._make_request("GET", "ca/version")
    
    def search_certificates(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        GET /certificate/search
        Search for certificates using various criteria
        
        Supported criteria:
        - query: Search query
        - maxResults: Maximum number of results (default: 10)
        - criteria: List of search criteria objects
        """
        return self._make_request("GET", "certificate/search", params=criteria)
    
    def get_certificate_by_serial(self, serial_number: str, issuer_dn: str = None) -> Dict[str, Any]:
        """
        GET /certificate/{issuer_dn}/{certificate_serial_number_hex}
        Get certificate by serial number and optionally issuer DN
        """
        if issuer_dn:
            import urllib.parse
            encoded_dn = urllib.parse.quote(issuer_dn, safe='')
            endpoint = f"certificate/{encoded_dn}/{serial_number}"
        else:
            endpoint = f"certificate/serialnumber/{serial_number}"
        
        return self._make_request("GET", endpoint)
    
    def get_certificate_status(self, issuer_dn: str, serial_number: str) -> Dict[str, Any]:
        """
        GET /certificate/{issuer_dn}/{certificate_serial_number_hex}/revocationstatus
        Get the revocation status of a certificate
        """
        import urllib.parse
        encoded_dn = urllib.parse.quote(issuer_dn, safe='')
        endpoint = f"certificate/{encoded_dn}/{serial_number}/revocationstatus"
        return self._make_request("GET", endpoint)
    
    def revoke_certificate(self, issuer_dn: str, serial_number: str, reason: str = "UNSPECIFIED") -> Dict[str, Any]:
        """
        PUT /certificate/{issuer_dn}/{certificate_serial_number_hex}/revoke
        Revoke a certificate
        
        Revocation reasons: UNSPECIFIED, KEY_COMPROMISE, CA_COMPROMISE, etc.
        """
        import urllib.parse
        encoded_dn = urllib.parse.quote(issuer_dn, safe='')
        endpoint = f"certificate/{encoded_dn}/{serial_number}/revoke"
        data = {"reason": reason}
        return self._make_request("PUT", endpoint, json=data)
    
    # CRL methods based on official EJBCA OpenAPI specification
    def get_latest_crl(self, issuer_dn: str, delta_crl: bool = False, crl_partition_index: int = 0) -> Dict[str, Any]:
        """
        GET /ca/{issuer_dn}/getLatestCrl  
        Get the latest Certificate Revocation List for a specific CA
        
        Parameters:
        - issuer_dn: the CRL issuer's DN (CA's subject DN) - Required
        - delta_crl: true to get the latest deltaCRL, false to get the latest complete CRL - Default: false
        - crl_partition_index: the CRL partition index - Default: 0
        """
        import urllib.parse
        encoded_dn = urllib.parse.quote(issuer_dn, safe='')
        
        # Build query parameters - match SDK exactly
        params = {}
        if delta_crl:
            params['deltaCrl'] = 'true'
        if crl_partition_index != 0:
            params['crlPartitionIndex'] = str(crl_partition_index)
        
        # Use camelCase as per SDK: getLatestCrl
        endpoint = f"ca/{encoded_dn}/getLatestCrl"
        return self._make_request("GET", endpoint, params=params)
    
    def get_crl(self, issuer_dn: str = None, delta_crl: bool = False, crl_partition_index: int = 0) -> Dict[str, Any]:
        """
        GET /ca/{issuer_dn}/getcrl or GET /ca/crl
        Get Certificate Revocation List for a CA
        
        Parameters:
        - issuer_dn: the CRL issuer's DN (CA's subject DN) - Optional for default CA
        - delta_crl: true to get deltaCRL, false to get complete CRL - Default: false  
        - crl_partition_index: the CRL partition index - Default: 0
        """
        if issuer_dn:
            import urllib.parse
            encoded_dn = urllib.parse.quote(issuer_dn, safe='')
            
            # Build query parameters
            params = {}
            if delta_crl:
                params['deltaCrl'] = 'true'
            if crl_partition_index != 0:
                params['crlPartitionIndex'] = str(crl_partition_index)
            # Try lowercase 'getcrl' instead of 'getCrl'
            endpoint = f"ca/{encoded_dn}/getcrl"
            return self._make_request("GET", endpoint, params=params)
        else:
            # Get CRL for the default CA
            endpoint = "ca/crl"
            return self._make_request("GET", endpoint)
    
    def create_crl(self, issuer_dn: str, delta_crl: bool = False) -> Dict[str, Any]:
        """
        POST /ca/{issuer_dn}/createcrl
        Create/Generate a new CRL for a specific CA
        
        Parameters:
        - issuer_dn: the CRL issuer's DN (CA's subject DN) - Required
        - delta_crl: true to also create the deltaCRL, false to only create the base CRL - Default: false
        """
        import urllib.parse
        encoded_dn = urllib.parse.quote(issuer_dn, safe='')
        
        # Build query parameters
        params = {}
        if delta_crl:
            params['deltacrl'] = 'true'
        
        # Use lowercase 'createcrl' - this was working before!
        endpoint = f"ca/{encoded_dn}/createcrl"
        return self._make_request("POST", endpoint, params=params)
    
    def get_crl_info(self, issuer_dn: str) -> Dict[str, Any]:
        """
        GET /ca/{issuer_dn}/crlinfo
        Get CRL information for a specific CA
        """
        import urllib.parse
        encoded_dn = urllib.parse.quote(issuer_dn, safe='')
        endpoint = f"ca/{encoded_dn}/crlinfo"
        return self._make_request("GET", endpoint)
    
    def get_ca_certificate(self, ca_subject_dn: str) -> Dict[str, Any]:
        """
        GET /ca/{issuer_dn}/certificate/download
        Get CA certificate for a specific CA
        """
        import urllib.parse
        encoded_dn = urllib.parse.quote(ca_subject_dn, safe='')
        endpoint = f"ca/{encoded_dn}/certificate/download"
        return self._make_request("GET", endpoint)
    
    def get_ca_certificates(self, ca_subject_dn: str) -> Dict[str, Any]:
        """
        GET /ca/{issuer_dn}/certificate
        Get CA certificate chain for a specific CA
        """
        import urllib.parse
        encoded_dn = urllib.parse.quote(ca_subject_dn, safe='')
        endpoint = f"ca/{encoded_dn}/certificate"
        return self._make_request("GET", endpoint)
    
    def enroll_certificate(self, certificate_request: str, ca_name: str, 
                          certificate_profile: str = "ENDUSER",
                          end_entity_profile: str = "EMPTY",
                          username: str = None) -> Dict[str, Any]:
        """
        POST /certificate/enroll
        Enroll a new certificate using a CSR
        
        This is typically available in EJBCA Community for basic enrollment
        """
        if not username:
            from datetime import datetime
            username = f"mcp_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        data = {
            "certificateRequest": certificate_request,
            "certificateAuthorityName": ca_name,
            "certificateProfileName": certificate_profile,
            "endEntityProfileName": end_entity_profile,
            "username": username,
            "password": "mcp_temp_password"
        }
        
        return self._make_request("POST", "certificate/enroll", json=data)

# Initialize EJBCA client
ejbca_client = EJBCARestClient(
    base_url=os.getenv("EJBCA_BASE_URL", "https://localhost:443"),
    cert_path=os.getenv("EJBCA_CLIENT_CERT", "/Users/saipasham/ejbca/certs/client.pem"),
    key_path=os.getenv("EJBCA_CLIENT_KEY", "/Users/saipasham/ejbca/certs/client.key")
)

# Create MCP server
server = Server("ejbca-mcp")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available EJBCA tools based on official REST API"""
    return [
        Tool(
            name="test_ejbca_connection",
            description="Test connection to EJBCA REST API and check authentication status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="troubleshoot_connection",
            description="Comprehensive troubleshooting tool for EJBCA connection issues",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_certificate_api_status", 
            description="Get the status and version of the EJBCA Certificate Management REST API",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_ca_list",
            description="Get list of authorized Certificate Authorities",
            inputSchema={
                "type": "object", 
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_ca_version",
            description="Get version information for the CA REST API",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="search_certificates",
            description="Search for certificates using various criteria",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string"
                    },
                    "max_results": {
                        "type": "integer", 
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    },
                    "subject_dn": {
                        "type": "string",
                        "description": "Subject Distinguished Name to search for"
                    },
                    "issuer_dn": {
                        "type": "string", 
                        "description": "Issuer Distinguished Name to search for"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_certificate_by_serial",
            description="Get certificate details by serial number",
            inputSchema={
                "type": "object",
                "properties": {
                    "serial_number": {
                        "type": "string",
                        "description": "Certificate serial number in hexadecimal format"
                    },
                    "issuer_dn": {
                        "type": "string",
                        "description": "Issuer Distinguished Name (optional)"
                    }
                },
                "required": ["serial_number"]
            }
        ),
        Tool(
            name="get_certificate_status",
            description="Get the revocation status of a certificate",
            inputSchema={
                "type": "object",
                "properties": {
                    "issuer_dn": {
                        "type": "string",
                        "description": "Issuer Distinguished Name"
                    },
                    "serial_number": {
                        "type": "string", 
                        "description": "Certificate serial number in hexadecimal format"
                    }
                },
                "required": ["issuer_dn", "serial_number"]
            }
        ),
        Tool(
            name="revoke_certificate",
            description="Revoke a certificate with specified reason",
            inputSchema={
                "type": "object",
                "properties": {
                    "issuer_dn": {
                        "type": "string",
                        "description": "Issuer Distinguished Name"
                    },
                    "serial_number": {
                        "type": "string",
                        "description": "Certificate serial number in hexadecimal format"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Revocation reason: UNSPECIFIED, KEY_COMPROMISE, CA_COMPROMISE, AFFILIATION_CHANGED, SUPERSEDED, CESSATION_OF_OPERATION, CERTIFICATE_HOLD, REMOVE_FROM_CRL, PRIVILEGE_WITHDRAWN, AA_COMPROMISE",
                        "default": "UNSPECIFIED"
                    }
                },
                "required": ["issuer_dn", "serial_number"]
            }
        ),
        Tool(
            name="get_crl",
            description="Get Certificate Revocation List (CRL) for a CA with optional delta CRL and partition support",
            inputSchema={
                "type": "object",
                "properties": {
                    "issuer_dn": {
                        "type": "string",
                        "description": "CRL issuer's DN (CA's subject DN) - optional for default CA"
                    },
                    "delta_crl": {
                        "type": "boolean",
                        "description": "true to get deltaCRL, false to get complete CRL (default: false)",
                        "default": False
                    },
                    "crl_partition_index": {
                        "type": "integer",
                        "description": "CRL partition index (default: 0)",
                        "default": 0
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_latest_crl",
            description="Get the latest Certificate Revocation List for a specific CA",
            inputSchema={
                "type": "object",
                "properties": {
                    "issuer_dn": {
                        "type": "string",
                        "description": "CRL issuer's DN (CA's subject DN)"
                    },
                    "delta_crl": {
                        "type": "boolean",
                        "description": "true to get the latest deltaCRL, false to get the latest complete CRL (default: false)",
                        "default": False
                    },
                    "crl_partition_index": {
                        "type": "integer",
                        "description": "CRL partition index (default: 0)",
                        "default": 0
                    }
                },
                "required": ["issuer_dn"]
            }
        ),
        Tool(
            name="create_crl",
            description="Create/Generate a new CRL for a specific CA",
            inputSchema={
                "type": "object",
                "properties": {
                    "issuer_dn": {
                        "type": "string",
                        "description": "CRL issuer's DN (CA's subject DN)"
                    },
                    "delta_crl": {
                        "type": "boolean",
                        "description": "true to also create the deltaCRL, false to only create the base CRL (default: false)",
                        "default": False
                    }
                },
                "required": ["issuer_dn"]
            }
        ),
        Tool(
            name="get_crl_info",
            description="Get CRL information for a specific CA",
            inputSchema={
                "type": "object",
                "properties": {
                    "issuer_dn": {
                        "type": "string",
                        "description": "CRL issuer's DN (CA's subject DN)"
                    }
                },
                "required": ["issuer_dn"]
            }
        ),
        Tool(
            name="get_ca_certificate",
            description="Get CA certificate for a specific CA",
            inputSchema={
                "type": "object",
                "properties": {
                    "ca_subject_dn": {
                        "type": "string",
                        "description": "CA Subject Distinguished Name"
                    }
                },
                "required": ["ca_subject_dn"]
            }
        ),
        Tool(
            name="get_ca_certificates",
            description="Get CA certificate chain for a specific CA",
            inputSchema={
                "type": "object",
                "properties": {
                    "ca_subject_dn": {
                        "type": "string",
                        "description": "CA Subject Distinguished Name"
                    }
                },
                "required": ["ca_subject_dn"]
            }
        ),
        Tool(
            name="enroll_certificate",
            description="Enroll a new certificate using a Certificate Signing Request (CSR)",
            inputSchema={
                "type": "object",
                "properties": {
                    "certificate_request": {
                        "type": "string",
                        "description": "Certificate Signing Request in PEM format"
                    },
                    "ca_name": {
                        "type": "string",
                        "description": "Certificate Authority name"
                    },
                    "certificate_profile": {
                        "type": "string", 
                        "description": "Certificate profile name (default: ENDUSER)",
                        "default": "ENDUSER"
                    },
                    "end_entity_profile": {
                        "type": "string",
                        "description": "End entity profile name (default: EMPTY)",
                        "default": "EMPTY"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username for the certificate (auto-generated if not provided)"
                    }
                },
                "required": ["certificate_request", "ca_name"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    
    try:
        result = None
        
        if name == "test_ejbca_connection":
            # Test connection with multiple checks
            health_result = ejbca_client.get_certificate_api_status()
            ca_result = ejbca_client.get_ca_version()
            
            result = {
                "connection_test": "completed",
                "certificate_api_status": health_result,
                "ca_version": ca_result,
                "certificates_available": ejbca_client.has_certificates,
                "base_url": ejbca_client.base_url
            }
            
        elif name == "troubleshoot_connection":
            # Comprehensive diagnostics
            import os
            
            # Check certificate files
            cert_exists = os.path.exists(ejbca_client.cert_path) if ejbca_client.cert_path else False
            key_exists = os.path.exists(ejbca_client.key_path) if ejbca_client.key_path else False
            
            # Test basic connectivity
            health_result = ejbca_client.get_certificate_api_status()
            ca_result = ejbca_client.get_ca_version()
            ca_list_result = ejbca_client.get_ca_list()
            
            result = {
                "diagnostics": {
                    "base_url": ejbca_client.base_url,
                    "cert_path": ejbca_client.cert_path,
                    "key_path": ejbca_client.key_path,
                    "cert_exists": cert_exists,
                    "key_exists": key_exists,
                    "certificates_available": ejbca_client.has_certificates
                },
                "api_tests": {
                    "certificate_status": health_result,
                    "ca_version": ca_result,
                    "ca_list": ca_list_result
                },
                "recommendations": []
            }
            
            # Add recommendations based on results
            if not ejbca_client.has_certificates:
                result["recommendations"].append("Configure client certificates using EJBCA_CLIENT_CERT and EJBCA_CLIENT_KEY environment variables")
            if not cert_exists and ejbca_client.cert_path:
                result["recommendations"].append(f"Certificate file not found: {ejbca_client.cert_path}")
            if not key_exists and ejbca_client.key_path:
                result["recommendations"].append(f"Private key file not found: {ejbca_client.key_path}")
            if health_result.get("error"):
                result["recommendations"].append("Certificate API not accessible - check EJBCA_BASE_URL and certificate authentication")
            if ca_result.get("error"):
                result["recommendations"].append("CA API not accessible - verify EJBCA REST API is enabled")
            
        elif name == "get_certificate_api_status":
            result = ejbca_client.get_certificate_api_status()
            
        elif name == "get_ca_list":
            result = ejbca_client.get_ca_list()
            
        elif name == "get_ca_version":
            result = ejbca_client.get_ca_version()
            
        elif name == "search_certificates":
            criteria = {}
            if "query" in arguments:
                criteria["query"] = arguments["query"]
            if "max_results" in arguments:
                criteria["maxResults"] = arguments["max_results"]
            if "subject_dn" in arguments:
                criteria["subjectDN"] = arguments["subject_dn"]
            if "issuer_dn" in arguments:
                criteria["issuerDN"] = arguments["issuer_dn"]
                
            result = ejbca_client.search_certificates(criteria)
            
        elif name == "get_certificate_by_serial":
            result = ejbca_client.get_certificate_by_serial(
                arguments["serial_number"],
                arguments.get("issuer_dn")
            )
            
        elif name == "get_certificate_status":
            result = ejbca_client.get_certificate_status(
                arguments["issuer_dn"],
                arguments["serial_number"]
            )
            
        elif name == "revoke_certificate":
            result = ejbca_client.revoke_certificate(
                arguments["issuer_dn"],
                arguments["serial_number"],
                arguments.get("reason", "UNSPECIFIED")
            )
            
        elif name == "get_crl":
            result = ejbca_client.get_crl(
                arguments.get("issuer_dn"),
                arguments.get("delta_crl", False),
                arguments.get("crl_partition_index", 0)
            )
            
        elif name == "get_latest_crl":
            result = ejbca_client.get_latest_crl(
                arguments["issuer_dn"],
                arguments.get("delta_crl", False),
                arguments.get("crl_partition_index", 0)
            )
            
        elif name == "create_crl":
            result = ejbca_client.create_crl(
                arguments["issuer_dn"],
                arguments.get("delta_crl", False)
            )
            
        elif name == "get_crl_info":
            result = ejbca_client.get_crl_info(arguments["issuer_dn"])
            
        elif name == "get_ca_certificate":
            result = ejbca_client.get_ca_certificate(arguments["ca_subject_dn"])
            
        elif name == "get_ca_certificates":
            result = ejbca_client.get_ca_certificates(arguments["ca_subject_dn"])
            
        elif name == "enroll_certificate":
            result = ejbca_client.enroll_certificate(
                arguments["certificate_request"],
                arguments["ca_name"],
                arguments.get("certificate_profile", "ENDUSER"),
                arguments.get("end_entity_profile", "EMPTY"),
                arguments.get("username")
            )
            
        else:
            return [TextContent(
                type="text", 
                text=f"❌ Unknown tool: {name}"
            )]
        
        # Format result
        if isinstance(result, dict):
            method = result.get("_method", "unknown")
            status_code = result.get("_status_code", "N/A")
            
            if "error" in result:
                status_icon = "❌"
                status_text = "ERROR"
            elif result.get("success") or status_code == 200:
                status_icon = "✅"
                status_text = "SUCCESS" 
            else:
                status_icon = "⚠️"
                status_text = "WARNING"
        else:
            method = "unknown"
            status_code = "N/A"
            status_icon = "✅"
            status_text = "SUCCESS"
        
        # Clean up internal fields for display
        display_result = dict(result) if isinstance(result, dict) else result
        if isinstance(display_result, dict):
            display_result.pop("_method", None)
            display_result.pop("_status_code", None)
            display_result.pop("_url", None)
            
            # Handle binary CRL data specially
            if "crl_data" in display_result:
                crl_data = display_result.pop("crl_data")
                display_result["crl_size_bytes"] = len(crl_data)
                display_result["crl_data_preview"] = f"{crl_data[:50]}..." if len(crl_data) > 50 else str(crl_data)
        
        formatted_result = json.dumps(display_result, indent=2, default=str)
        
        return [TextContent(
            type="text",
            text=f"{status_icon} **{status_text}**: EJBCA {name}\n\n"
                 f"**Method**: {method} | **Status**: {status_code}\n\n"
                 f"```json\n{formatted_result}\n```"
        )]
        
    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return [TextContent(
            type="text", 
            text=f"❌ **ERROR**: Failed to execute {name}\n\n"
                 f"**Error**: {str(e)}\n\n"
                 f"**Tip**: Try `troubleshoot_connection` first to verify setup."
        )]

async def main():
    """Main entry point"""
    logger.info("Starting EJBCA MCP Server...")
    logger.info(f"EJBCA URL: {ejbca_client.base_url}")
    logger.info(f"Certificates available: {ejbca_client.has_certificates}")
    
    # Test connection on startup
    try:
        test_result = ejbca_client.get_certificate_api_status()
        logger.info(f"Startup test: {test_result.get('status', 'unknown')}")
    except Exception as e:
        logger.warning(f"Startup test failed: {e}")
    
    # Initialize with proper MCP server setup
    init_options = InitializationOptions(
        server_name="ejbca-mcp",
        server_version="2.1.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={}
        )
    )
    
    # Run the MCP server
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], init_options)

if __name__ == "__main__":
    asyncio.run(main())