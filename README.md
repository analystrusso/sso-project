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
/home
|
|
sso-projectdir----app--------------------------certs-------------keycloak-----------------ldap------------monitoring
                   |                             |                   |                      |                  |
                   |                             |                   |                      |                  |
                   main.py templates/            ca.crt              init.sh                base.ldif          grafana/provisioning/dashboards/datasources
                                |                ca.key              realm-export.json      seed.ldif          prometheus.yml          |            |
                                |                ca.srl              realm-export.sh        seed.sh            promtail.yml            |            |
                                403.html         dhparam.pem                                slapd.conf                                 dashboard.yml|
                                appdev.html      generate.sh                                                                           FastAPI-1772888747131.json
                                base.html        ldap.crt                                                                              Keycloak-1772888768333.json
                                devops.html      ldap.csr                                                                              OpenLDAP-1772888780488.json
                                home.html        ldap.key                                                                                           |
                                                 truststore.jks                                                                                     datasources.yml
