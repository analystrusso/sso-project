import os
import logging
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import RedirectResponse, JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from keycloak import KeycloakOpenID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

keycloak_internal_url = os.environ.get("KEYCLOAK_INTERNAL_URL")
keycloak_external_url = os.environ.get("KEYCLOAK_EXTERNAL_URL")
app_base_url = os.environ.get("APP_BASE_URL")
client = os.environ.get("KEYCLOAK_CLIENT_ID")
realm = os.environ.get("KEYCLOAK_REALM")

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{keycloak_external_url}/realms/{realm}/protocol/openid-connect/auth",
    tokenUrl=f"{keycloak_external_url}/realms/{realm}/protocol/openid-connect/token"
)

keycloak_openid = KeycloakOpenID(
    server_url=keycloak_internal_url,
    client_id=client,
    realm_name=realm,
    client_secret_key=os.environ.get("KEYCLOAK_CLIENT_SECRET")
)

def require_role(required_role: str):
    async def role_checker(token: str = Depends(oauth2_scheme)):
        try:
            token_info = keycloak_openid.decode_token(token)
            roles = token_info.get("realm_access", {}).get("roles", [])
            if required_role not in roles:
                logger.warning(f"Access denied: missing role '{required_role}'")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden"
                )
            return token_info
        except HTTPException:
            raise
        except Exception:
            logger.warning("Token decode failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
    return role_checker

app = FastAPI()
Instrumentator().instrument(app).expose(app)

@app.get("/")
async def homepage():
    return {"message": "Welcome to the intranet homepage"}

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

@app.get("/callback")
async def callback(code: str):
    try:
        token = keycloak_openid.token(
            grant_type="authorization_code",
            code=code,
            redirect_uri=f"{app_base_url}/callback"
        )
        return JSONResponse(token)
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token exchange failed"
        )

@app.get("/devops")
async def devops_page(user=Depends(require_role("devops"))):
    return {"message": f"Welcome DevOps member {user['preferred_username']}"}

@app.get("/appdev")
async def appdev_page(user=Depends(require_role("appdev"))):
    return {"message": f"Welcome AppDev member {user['preferred_username']}"}