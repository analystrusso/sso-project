#!/bin/bash
set -e

KEYCLOAK_URL="${KEYCLOAK_EXTERNAL_URL:-http://localhost:8080}"
KEYCLOAK_ADMIN="${KEYCLOAK_ADMIN:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-adminpass}"
REALM="${KEYCLOAK_REALM:-intranet-app}"
CLIENT_ID="${KEYCLOAK_CLIENT_ID:-intranet-app}"
LDAP_BIND_PASSWORD="${LDAP_PASS:-secret}"
LDAP_FEDERATION_NAME="ldap"



echo "Waiting for Keycloak to be ready..."
until curl -s "${KEYCLOAK_URL}/realms/master" | python3 -c "import sys,json; json.load(sys.stdin)" &>/dev/null; do
  echo "Keycloak not ready, retrying in 5s..."
  sleep 5
done
echo "Keycloak is ready, waiting 5s for token endpoint..."
sleep 5


echo "Getting admin token..."
TOKEN_RESPONSE=$(curl -s -X POST \
  "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli&grant_type=password&username=${KEYCLOAK_ADMIN}&password=${KEYCLOAK_ADMIN_PASSWORD}")

echo "Token response: $TOKEN_RESPONSE"

ADMIN_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

if [ -z "$ADMIN_TOKEN" ]; then
  echo "ERROR: Failed to get admin token. Check KEYCLOAK_ADMIN_PASSWORD."
  exit 1
fi

echo "Getting LDAP federation ID..."
LDAP_ID=$(curl -s \
  "${KEYCLOAK_URL}/admin/realms/${REALM}/components?type=org.keycloak.storage.UserStorageProvider" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  | python3 -c "import sys,json; providers=json.load(sys.stdin); print(next(p['id'] for p in providers if p['name']=='${LDAP_FEDERATION_NAME}'))")

if [ -z "$LDAP_ID" ]; then
  echo "ERROR: Could not find LDAP federation named '${LDAP_FEDERATION_NAME}'."
  exit 1
fi

echo "Setting LDAP bind credential..."
LDAP_CONFIG=$(curl -s \
  "${KEYCLOAK_URL}/admin/realms/${REALM}/components/${LDAP_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}")

UPDATED_CONFIG=$(echo "$LDAP_CONFIG" | python3 -c "
import sys, json
config = json.load(sys.stdin)
config['config']['bindCredential'] = ['${LDAP_BIND_PASSWORD}']
print(json.dumps(config))
")

curl -s -X PUT \
  "${KEYCLOAK_URL}/admin/realms/${REALM}/components/${LDAP_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$UPDATED_CONFIG"

echo "Syncing LDAP users..."
curl -s -X POST \
  "${KEYCLOAK_URL}/admin/realms/${REALM}/user-storage/${LDAP_ID}/sync?action=triggerFullSync" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"

echo "Getting client UUID..."
CLIENT_UUID=$(curl -s \
  "${KEYCLOAK_URL}/admin/realms/${REALM}/clients?clientId=${CLIENT_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  | python3 -c "import sys,json; clients=json.load(sys.stdin); print(clients[0]['id'])")

if [ -z "$CLIENT_UUID" ]; then
  echo "ERROR: Could not find client '${CLIENT_ID}'."
  exit 1
fi

echo "Setting client secret..."
NEW_SECRET=$(curl -s -X POST \
  "${KEYCLOAK_URL}/admin/realms/${REALM}/clients/${CLIENT_UUID}/client-secret" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["value"])')

if [ -z "$NEW_SECRET" ]; then
  echo "ERROR: Failed to generate client secret."
  exit 1
fi

echo "Updating .env with new client secret..."
sed -i "s/^KEYCLOAK_CLIENT_SECRET=.*/KEYCLOAK_CLIENT_SECRET=${NEW_SECRET}/" .env

echo "Restarting intranet-app to pick up new secret..."
sleep 30
docker compose stop intranet-app && docker compose up -d intranet-app

echo "New client secret: ${NEW_SECRET}"
