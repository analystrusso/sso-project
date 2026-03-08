#!/bin/bash
set -e

SCRIPT_DIR="$(dirname "$0")"
LDAP_URI="${LDAP_URI:-ldaps://127.0.0.1:636}"
LDAP_ADMIN="${LDAP_ADMIN:-cn=admin,dc=example,dc=in}"
LDAP_PASS="${LDAP_PASS:-secret}"
CA_CERT="${CA_CERT:-certs/ca.crt}"

echo "Waiting for LDAP to be ready..."
until LDAPTLS_CACERT="$CA_CERT" \
	ldapsearch -H "$LDAP_URI" \
	-x -b "" -s base "(objectClass=*)" &>/dev/null; do
	echo "LDAP not ready, retrying in 3s..."
	sleep 3
done

echo "Seeding LDAP..."
LDAPTLS_CACERT="$CA_CERT" ldapadd \
  -H "$LDAP_URI" \
  -x -D "$LDAP_ADMIN" \
  -w "$LDAP_PASS" \
  -f "$SCRIPT_DIR/seed.ldif" 2>&1 | grep -v "Already exists" || true

echo "Done."
