#!/bin/bash
# convert-cert.sh

echo "Convert P12 certificate to PEM format"
echo "Place your downloaded P12 file in this directory and name it 'downloaded.p12'"

if [ ! -f "RESTTEST1.p12" ]; then
    echo "Error: downloaded.p12 not found"
    echo "Please download the certificate from EJBCA and rename it to 'downloaded.p12'"
    exit 1
fi

# Create certs directory if it doesn't exist
mkdir -p certs

# Convert P12 to PEM
echo "Enter the P12 password when prompted:"
openssl pkcs12 -in RESTTEST1.p12 -nokeys -out certs/client.pem
openssl pkcs12 -in RESTTEST1.p12 -nocerts -nodes -out certs/client.key

echo "Certificate converted successfully!"
echo "Files created:"
echo "- certs/client.pem (certificate)"
echo "- certs/client.key (private key)"

# Show certificate details
echo ""
echo "Certificate details:"
openssl x509 -in certs/client.pem -noout -subject -issuer -dates
