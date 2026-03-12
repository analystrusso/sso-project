# sso-project

This project will have me design an SSO system using OpenLDAP and Keycloak, and wire them up to a basic app written in Python using FastAPI. The project is running in a series of Docker containers using docker-compose:

To run this, you'll need to install docker compose and make, and it should go without saying that this runs best (solely?) on Linux. Set script permissions to 755, and then run "make fresh" from the project root.

Edit seed.ldif to alter users and groups. 

Login page for web app is localhost:8000, see seed.ldif for login credentials. 

Keycloak admin logon is localhost:8080, login is admin/adminpass

Keycloak management port is localhost:9000

Grafana login is localhost:3000 with admin/admin (it'll prompt you to set a new password afterwards). 

Logging in with testuser should redirect you to the devops landing page, while testuser2 should redirect you to the appdev page. 

Ok, now that the run directions are out of the way, here's what's actually going on.

Directory structure:
```
sso-project/
        app/
            main.py
            templates/
                403.html
                appdev.html
                base.html
                devops.html
                home.html
        certs/
            ca.crt
            ca.key
            ca.srl
            dhparam.pem
            generate.sh
            ldap.crt
            ldap.csr
            ldap.key
            truststore.jks
        keycloak/
            init.sh
            realm-export.sh
            realm-export.json
        ldap/
            base.ldif
            seed.ldif
            seed.sh
            slapd.conf
        monitoring/
            grafana/
            prometheus.yml
            promtail.yml
                provisioning/
                datasources/
                    datasources.yml
                dashboards/
                    dashboards.yml
                    FastAPI-1772888747131.json
                    Keycloak-1772888768333.json
                    OpenLDAP-1772888780488.json
```
