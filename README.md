# sso-project

This project will have me design an SSO system using OpenLDAP and Keycloak, and wire them up to a basic app written in Python using FastAPI. The project is running in a series of Docker containers using docker-compose:

To run this, you'll need to install docker compose and make, and it should go without saying that this runs best (solely?) on Linux. Set script permissions to 755, and then run "make fresh" from the project root.

Edit seed.ldif to alter users and groups. 

Login page for web app is localhost:8000, see seed.ldif for login credentials. 

Keycloak admin logon is localhost:8080, login is admin/adminpass

Keycloak management port is localhost:9000

Grafana login is localhost:3000 with admin/admin (it'll prompt you to set a new password afterwards). 

Logging in with testuser should redirect you to the devops landing page, while testuser2 should redirect you to the appdev page. 

