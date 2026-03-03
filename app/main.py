import os
import uvicorn
import logging
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import RedirectResponse, JSONResponse
from keycloak import KeycloakOpenID


keycloak_internal_url = "http://keycloak:8080/"
keycloak_external_url = "http://localhost:8080/"
client = "intranet-app"
realm = "intranet-app"

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{keycloak_external_url}realms/{realm}/protocol/openid-connect/auth",
    tokenUrl=f"{keycloak_external_url}realms/{realm}/protocol/openid-connect/token"
)

keycloak_openid = KeycloakOpenID(
    server_url=keycloak_internal_url,
    client_id="intranet-app",
    realm_name = "intranet-app",
    client_secret_key=os.environ.get("KEYCLOAK_CLIENT_SECRET")
)


def require_role(required_role: str):
    async def role_checker(token:str = Depends(oauth2_scheme)):
        user_info = keycloak_openid.userinfo(token)

        roles = user_info.get("realm_access", {}).get("roles", [])

        if required_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden"
            )
        
        return user_info
    return role_checker

app = FastAPI()


@app.get("/protected")
async def protected(token: str = Depends(oauth2_scheme)):
    try:
        user_info = keycloak_openid.userinfo(token)
        return {"user": user_info}
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
@app.get("/login")
async def login():
    auth_url = (
        f"{keycloak_external_url}realms/{realm}/protocol/openid-connect/auth"
        f"?client_id={client}"
        f"&redirect_uri=http://localhost:8000/callback"
        f"&response_type=code"
        f"&scope=openid"
    )
    return RedirectResponse(auth_url)
    

@app.get("/callback")
async def callback(code: str):
    token = keycloak_openid.token(
        grant_type="authorization_code",
        code=code,
        redirect_uri="http://localhost:8000/callback"
    )
    return JSONResponse(token)

@app.get("/")
async def homepage():
    return {"message": "Welcome to the intranet homepage"}

@app.get("/devops")
async def devops_page(user=Depends(require_role("devops"))):
    return {"message": f"Welcome DevOps member {user['preferred_username']}"}

@app.get("/appdev")
async def appdev_page(user=Depends(require_role("appdev"))):
    return {"message": f"Welcome AppDev member {user['preferred_username']}"}