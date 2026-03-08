#!/bin/bash
curl -s -X POST \
	  "http://localhost:8080/admin/realms/intranet-app/partial-export?exportClients=true&exportGroupsAndRoles=true" \
	  -H "Authorization: Bearer $(curl -s -X POST \
	    'http://localhost:8080/realms/master/protocol/openid-connect/token' \
	    -d 'client_id=admin-cli&grant_type=password&username=admin&password=adminpass' \
	    | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')" \
	  -H "Content-Type: application/json" \
	  > keycloak/realm-export.json
	echo "Realm exported to keycloak/realm-export.json"
