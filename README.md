# sso-project

This project will have me design an SSO system using OpenLDAP and Keycloak, and wire them up to a basic app written in Python using FastAPI. The project is running in a series of Docker containers using docker-compose:

```
version: '2'
services:
  ldap:
    image: osixia/openldap:latest
    container_name: ldap
    environment:
      - LDAP_ORGANIZATION=<redacted>
      - LDAP_DOMAIN=<redacted>.in
      - "LDAP_BASE_DN=dc=<redacted>,dc=in"
      - LDAP_ADMIN_PASSWORD=<redacted>
    volumes:
      - ldap_data:/var/lib/ldap
      - ldap_config:/etc/ldap/slapd.d
    ports:
      - 389:389
      - 636:636
  
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    container_name: keycloak
    environment:
      - KEYCLOAK_ADMIN=<redacted>
      - KEYCLOAK_ADMIN_PASSWORD=<redacted>
    volumes:
      - keycloak_data:/opt/keycloak/data
    command: start-dev
    ports:
      - "8080:8080"
    depends_on:
      - ldap

  intranet-app:
    build: .
    container_name: intranet-app
    ports:
      - "8000:8000"
    depends_on:
      - keycloak

volumes:
  ldap_data:
  ldap_config:
  keycloak_data:
```

And this is my Dockerfile:
```
FROM python:3.11-slim

WORKDIR /app
COPY app/requirements.txt .
RUN pip install -r requirements.txt
COPY app/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

The app itself isn't built yet -- only the groundwork is laid. Currently, I'm working on setting up a permanent admin user in keycloak and getting persistent storage set up so the realm config and user federation doesn't wipe itself each time I stop and start the containers.

I have three users set up in OpenLDAP spread across two groups, devops and appdev. Each group is nested inside a parent OU called groups. 

