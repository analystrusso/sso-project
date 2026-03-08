#!/bin/bash
set -e

CERTS_DIR="$(dirname "$0")"

echo "Generating CA..."
openssl genrsa -out "$CERTS_DIR/ca.key" 2048
openssl req -new -x509 -days 365 -key "$CERTS_DIR/ca.key" \
	-out "$CERTS_DIR/ca.crt" -subj "/CN=example-ca"

echo "Generating LDAP cert..."
openssl genrsa -out "$CERTS_DIR/ldap.key" 2048
openssl req -new -key "$CERTS_DIR/ldap.key" \
  -out "$CERTS_DIR/ldap.csr" -subj "/CN=ldap" \
  -addext "subjectAltName=DNS:ldap,DNS:localhost,IP:127.0.0.1"
openssl x509 -req -in "$CERTS_DIR/ldap.csr" \
  -CA "$CERTS_DIR/ca.crt" -CAkey "$CERTS_DIR/ca.key" \
  -CAcreateserial -out "$CERTS_DIR/ldap.crt" -days 365 \
  -copy_extensions copy

echo "Generating DH params..."
openssl dhparam -out "$CERTS_DIR/dhparam.pem" 2048

echo "Setting permissions..."
chmod 644 "$CERTS_DIR/ca.crt" "$CERTS_DIR/ca.key" "$CERTS_DIR/ca.srl"
chmod 644 "$CERTS_DIR/ldap.crt" "$CERTS_DIR/ldap.csr"
chmod 600 "$CERTS_DIR/ldap.key"
chmod 644 "$CERTS_DIR/dhparam.pem"

echo "Done. Certs generated in $CERTS_DIR"
