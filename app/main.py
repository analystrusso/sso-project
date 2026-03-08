import os
import logging
from fastapi import Depends, FastAPI, HTTPException, status, Request, Cookie
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from prometheus_fastapi_instrumentator import Instrumentator
from keycloak import KeycloakOpenID
from typing import Optional
from jose import jwt as jose_jwt

# Cookie is how FastAPI reads cookie values, Request is needed to pass to templates,
# Jinja2Templates handles HTML rendering, OAuth2AuthorizationCodeBearer is gone entirely
# from previous iteration since we're using cookies instead now.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

keycloak_internal_url = os.environ.get("KEYCLOAK_INTERNAL_URL")
keycloak_external_url = os.environ.get("KEYCLOAK_EXTERNAL_URL")
app_base_url = os.environ.get("APP_BASE_URL")
client = os.environ.get("KEYCLOAK_CLIENT_ID")
realm = os.environ.get("KEYCLOAK_REALM")

keycloak_openid = KeycloakOpenID(
    server_url=keycloak_internal_url + "/",     # The + "/" avoids problems stemming from lack of trailing slash, regardless of .env.
    client_id=client,
    realm_name=realm,
    client_secret_key=os.environ.get("KEYCLOAK_CLIENT_SECRET")
)

app = FastAPI()
Instrumentator().instrument(app).expose(app)
templates = Jinja2Templates(directory="templates")


# Get_current_user reads the access_token cookie and decodes it. Returns none if no or invalid cookie.
# This never raises an exception -- it's a soft check used by routes that work for logged-in and 
# anonymous users.
def get_current_user(access_token: Optional[str] = Cookie(None)):
    if not access_token:
        logger.info("get_current_user: no cookie found")
        return None
    try:
        token_info = jose_jwt.decode(
            access_token,
            key="",
            algorithms=["RS256"],
            options={"verify_signature": False, "verify_aud": False, "verify_exp": True}
        )
        logger.info(f"get_current_user: decoded token for {token_info.get('preferred_username')}")
        logger.info(f"get_current_user: full token: {token_info}")
        return token_info
    except Exception as e:
        logger.warning(f"get_current_user: decode failed: {e}")
        return None

# Require_role reads the token from Cookie(None) instead of Depends(oauth2_scheme) from last iteration.
# No cookie and token decode failure redirect leads to redirect to /login instead of raising 401.
# Wrong role leads to rendering 403.html instead of raising an exception so user sees a proper page.
# Takes request: Request as parameter because templates need it.
def require_role(required_role: str):
    def role_checker(request: Request, access_token: Optional[str] = Cookie(None)):
        if not access_token:
            return RedirectResponse(url="/login")
        try:
            token_info = jose_jwt.decode(
                access_token,
                key="",
                algorithms=["RS256"],
                options={"verify_signature": False, "verify_aud": False, "verify_exp": True}
)
            roles = token_info.get("realm_access", {}).get("roles", [])
            if required_role not in roles:
                logger.warning(f"Access denied: missing role '{required_role}'")
                return templates.TemplateResponse(
                    "403.html",
                    {"request": request, "username": token_info.get("preferred_username")},
                    status_code=status.HTTP_403_FORBIDDEN
                )
            return token_info
        except Exception:
            logger.warning("Token decode failed")
            return RedirectResponse(url="/login")
    return role_checker


# Homepage works for both logged-in and anonymous users. Passes username and roles to the template.
# Template decides what to show based on username and role. Anonymous users get a login prompt while
# logged-in users get role-based content cards.
@app.get("/")
async def homepage(request: Request, access_token: Optional[str] = Cookie(None)):
    user = get_current_user(access_token)
    if user:
        roles = user.get("realm_access", {}).get("roles", [])
        username = user.get("preferred_username")
    else:
        roles = []
        username = None
    return templates.TemplateResponse("home.html", {
        "request": request,
        "username": username,
        "roles": roles
    })

@app.get("/login")
async def login():
    auth_url = (
        f"{keycloak_external_url}/realms/{realm}/protocol/openid-connect/auth"
        f"?client_id={client}"
        f"&redirect_uri={app_base_url}/callback"
        f"&response_type=code"
        f"&scope=openid"
    )
    return RedirectResponse(auth_url)


# Redirects to / not /devops -- hompage then shows the right content based on roles.
# httponly=True should mean JavaScript can't read the cookie, thus protecting against XSS attacks.
# samesite="lax" means the cookie is sent on normal navigation but not on cross-site requests,
# protecting against CSRF.
# On failure, redirects to /login instead of raising an exception.
@app.get("/callback")
async def callback(code: str):
    try:
        token = keycloak_openid.token(
            grant_type="authorization_code",
            code=code,
            redirect_uri=f"{app_base_url}/callback"
        )
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key="access_token",
            value=token["access_token"],
            httponly=True,
            samesite="lax",
            path="/"
        )
        return response
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        return RedirectResponse(url="/login")


# On logout, the cookie is deleted from the browser and user is redirected to Keycloak's logout endpoint. 
# This invalidates the session server-side. Deleting just the cookie leaves the session active and invalidating
# just the session leaves cookie in-browser.
@app.get("/logout")
async def logout():
    response = RedirectResponse(
        url=f"{keycloak_external_url}/realms/{realm}/protocol/openid-connect/logout"
        f"?post_logout_redirect_uri={app_base_url}&client_id={client}"
    )
    response.delete_cookie("access_token", path="/")
    return response


# The isinstance check is necessary because 'require_role' can return three different things 
# — a `RedirectResponse` (not logged in), a `TemplateResponse` with 403.html (wrong role), or 
# the `token_info` dict (success). FastAPI's `Depends` passes whatever `require_role` returns as `user`, 
# so the route needs to check what it got and either pass it through or render the page.
@app.get("/devops")
async def devops_page(request: Request, user=Depends(require_role("devops"))):
    if isinstance(user, RedirectResponse) or isinstance(user, HTMLResponse):
        return user
    return templates.TemplateResponse("devops.html", {
        "request": request,
        "username": user.get("preferred_username")
    })

@app.get("/appdev")
async def appdev_page(request: Request, user=Depends(require_role("appdev"))):
    if isinstance(user, RedirectResponse) or isinstance(user, HTMLResponse):
        return user
    return templates.TemplateResponse("appdev.html", {
        "request": request,
        "username": user.get("preferred_username")
    })

# Overall flow:
# Anon user hits /, renders homepage with login button.
# Login redirects to Keycloak, where the user logs in with credentials.
# Keycloak redirects to /callback with auth code.
# /callback exchanges code for token, sets httponly cookie, and redirects to /.
# Homepage reads cookie, decodes token, gets roles, and renders role-specific content and nav links.
# User clicks DevOps link (for example), and /devops reads cookie via require_role. 
# If cookie is valid and has role, renders devops.html. If no cookie, redirects to /login.
# If wrong role, renders 403.html.
# When user clicks logout, cookie is deleted, Keycloak session is invalidated, and user redirected to homepage as anon user.

