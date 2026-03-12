# SSO Platform — OpenLDAP + Keycloak + FastAPI

A containerized single sign-on platform built on a real enterprise architecture: OpenLDAP as the identity source of truth, Keycloak as the identity provider, and FastAPI as a role-gated intranet web application. The full stack — including observability — runs in Docker Compose and provisions itself from scratch with a single command.

---

## Architecture

```
Browser
  │
  ▼
FastAPI (port 8000)        ← OIDC authorization code flow, cookie-based auth
  │
  ▼
Keycloak (port 8080)       ← Identity provider, token issuance, group/role mapping
  │
  ▼
OpenLDAP (port 636/LDAPS)  ← User credentials and group membership (source of truth)

All services → Promtail → Loki → Grafana
OpenLDAP cn=Monitor → openldap-exporter → Prometheus → Grafana
Keycloak :9000/metrics → Prometheus → Grafana
FastAPI /metrics → Prometheus → Grafana
```

**Authentication flow:**
1. User clicks Login on the FastAPI app and is redirected to Keycloak's login page
2. Keycloak validates credentials against OpenLDAP over LDAPS
3. Keycloak checks group membership, maps it to realm roles, and issues a signed JWT
4. FastAPI stores the JWT in an `httponly` cookie and redirects to the homepage
5. Protected routes decode the cookie and enforce role-based access — no second login required

---

## Prerequisites

- Docker Engine 24+
- Docker Compose v2+
- Make
- `openssl` and `ldap-utils` (for cert generation and LDAP seeding)

Tested on Ubuntu 22.04 and 24.04. Not tested on macOS or Windows.

---

## Quick Start

```bash
# 1. Clone the repository
git clone <repo-url>
cd sso-project

# 2. Copy the environment file and set your secrets
cp .env.example .env

# 3. Generate TLS certificates
make certs

# 4. Set script permissions
chmod 755 certs/generate.sh ldap/seed.sh keycloak/init.sh keycloak/export-realm.sh

# 5. Bring up the full stack
make fresh
```

`make fresh` tears down any existing stack, rebuilds containers, seeds the LDAP directory, and fully initializes Keycloak — including setting the client secret, binding LDAP credentials, syncing users, and mapping roles to groups. No manual steps required.

---

## Service Endpoints

| Service | URL | Credentials |
|---|---|---|
| Intranet app | http://localhost:8000 | See seed.ldif |
| Keycloak admin | http://localhost:8080 | admin / adminpass |
| Keycloak management | http://localhost:9000 | — |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |

---

## Users and Roles

Defined in `ldap/seed.ldif`. Two test users are provided:

| Username | Password | Role | Access |
|---|---|---|---|
| testuser | testpass | devops | DevOps portal |
| testuser2 | testpass2 | appdev | AppDev portal |

To add users, add entries to `ldap/seed.ldif` following the existing format. Increment `uidNumber` for each new user. Re-run `make fresh` to apply changes.

---

## Directory Structure

```
sso-project/
├── app/
│   ├── main.py               # FastAPI app — OIDC flow, cookie auth, role-gated routes
│   ├── requirements.txt
│   └── templates/
│       ├── base.html         # Shared layout and navbar with role-based link visibility
│       ├── home.html         # Landing page — shows role-specific content cards
│       ├── devops.html       # DevOps portal page (requires devops role)
│       ├── appdev.html       # AppDev portal page (requires appdev role)
│       └── 403.html          # Access denied page
├── certs/
│   ├── generate.sh           # Generates self-signed CA and LDAP cert with correct SANs
│   ├── ca.crt / ca.key
│   ├── ldap.crt / ldap.key
│   └── dhparam.pem
├── keycloak/
│   ├── init.sh               # Fully initializes Keycloak after import — sets LDAP bind
│   │                         # credential, syncs users, maps roles to groups, sets client secret
│   ├── export-realm.sh       # Exports realm config to realm-export.json
│   └── realm-export.json     # Auto-imported by Keycloak on startup
├── ldap/
│   ├── slapd.conf            # OpenLDAP configuration — TLS, schema, monitor access
│   ├── base.ldif             # Base directory structure (OUs, organization)
│   ├── seed.ldif             # Users and groups — edit this to add/modify users
│   └── seed.sh               # Applies seed.ldif to a running LDAP instance
├── monitoring/
│   ├── prometheus.yml        # Scrape config for all three services
│   ├── promtail.yml          # Log shipping config
│   └── grafana/
│       └── provisioning/
│           ├── datasources/
│           │   └── datasources.yml
│           └── dashboards/
│               ├── dashboards.yml
│               ├── FastAPI-*.json
│               ├── Keycloak-*.json
│               └── OpenLDAP-*.json
├── Dockerfile
├── docker-compose.yaml
├── Makefile
├── .env
└── .env.example
```

---

## Makefile Targets

| Target | Description |
|---|---|
| `make fresh` | Full teardown, rebuild, seed LDAP, initialize Keycloak |
| `make up` | Start all containers |
| `make down` | Stop and remove containers (preserves volumes) |
| `make build` | Rebuild containers |
| `make logs` | Follow logs for all containers |
| `make status` | Show container status |
| `make certs` | Generate TLS certificates |
| `make seed` | Seed LDAP directory |
| `make init` | Initialize Keycloak |
| `make export-realm` | Export current Keycloak realm to realm-export.json |

---

## Security Notes

**What is hardened:**
- LDAP traffic is encrypted with LDAPS (port 636) using a self-signed CA with correct certificate SANs
- JWTs are stored in `httponly`, `SameSite=lax` cookies — inaccessible to JavaScript, protecting against XSS and CSRF
- Keycloak secrets are never stored in the realm export — `init.sh` injects them at runtime from `.env`
- OpenLDAP admin credentials are hashed with SSHA in `slapd.conf`

**Known limitations:**
- Self-signed certificates will produce browser warnings if used outside localhost
- JWT expiry is handled — expired tokens redirect to login — but token refresh is not implemented. Sessions will require re-login after the token expires
- Keycloak admin and Grafana credentials in `.env.example` are defaults and should be changed for any non-local deployment

---

## How It Works

**Why OpenLDAP?**
LDAP is the standard protocol for centralized identity management in enterprise environments. OpenLDAP is the open-source implementation. It stores users, credentials, and group memberships and serves as the single source of truth — meaning changes to a user's groups in LDAP are reflected across all connected applications after the next sync.

**Why Keycloak?**
Keycloak is an open-source identity provider that implements OIDC and SAML. It sits between the application and the identity store, handling authentication, token issuance, and session management. Applications never see user passwords — they only see signed tokens. Keycloak federates users from OpenLDAP and maps LDAP group membership to realm roles that appear in the JWT.

**Why FastAPI?**
FastAPI is a modern Python web framework well-suited for demonstrating OIDC integration. It handles the authorization code flow, stores the JWT in a secure cookie, and uses a role-checking dependency to protect routes — all with minimal code.

**Why cookies instead of Bearer tokens?**
Bearer tokens stored in `localStorage` are accessible to JavaScript and vulnerable to XSS attacks. `httponly` cookies cannot be read by JavaScript at all, making them the correct choice for browser-based applications. The tradeoff is that cookies require `SameSite` configuration to prevent CSRF — which is set in this project.
