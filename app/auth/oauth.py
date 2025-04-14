import os
from httpx_oauth.clients.openid import OpenID
from httpx_oauth.oauth2 import GetAccessTokenError
from fastapi import HTTPException, Request
from starlette.responses import RedirectResponse
from typing import Optional, Dict, Any
import json
import httpx
from urllib.parse import urlencode

class AuthentikOAuth:
    def __init__(self):
        self.client_id = os.getenv("AUTHENTIK_CLIENT_ID", "dRXLBdTdG6JSHqkcM0ZQBPwBVMBrG6SF32LZ1XAT")
        self.client_secret = os.getenv("AUTHENTIK_CLIENT_SECRET", 
                                      "hn1aKecLeYj1tVc7QtsavrWjSOF4t7Ty1akVTmUqvIFJF1y0H3Myv7InUxAX6E2GLpMxxhhZZ2aUSJ9VEQz7zGcMbgUeMStxx2U7bEQxmuOGjZf0XJbOBGjdwGZYJlz7")
        self.config_url = os.getenv("AUTHENTIK_CONFIG_URL", 
                                  "https://authentik.hosterra.net/application/o/leagueledger/.well-known/openid-configuration")
        self.client = None
        self.initialize_client()

    def initialize_client(self):
        try:
            self.client = OpenID(
                client_id=self.client_id,
                client_secret=self.client_secret,
                openid_configuration_endpoint=self.config_url,
            )
        except Exception as e:
            print(f"Error initializing Authentik OAuth client: {str(e)}")
            self.client = None

    async def get_login_url(self, request: Request, redirect_uri: str) -> str:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="OAuth client could not be initialized")
            
        try:
            authorization_url = await self.client.get_authorization_url(
                redirect_uri=redirect_uri,
                scope=["openid", "email", "profile"],
                state=str(request.session.get("session_id", "")),
            )
            return authorization_url
        except Exception as e:
            print(f"Error getting authorization URL: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")

    async def get_user_info(self, request: Request, redirect_uri: str, code: str) -> Dict[str, Any]:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="OAuth client could not be initialized")
            
        try:
            # Exchange code for token
            token = await self.client.get_access_token(
                code=code,
                redirect_uri=redirect_uri,
            )
            
            access_token = token.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="Could not get access token")
                
            # Get user info from OpenID userinfo endpoint
            async with httpx.AsyncClient() as client:
                # Get the configuration to find the userinfo_endpoint
                config_response = await client.get(self.config_url)
                if config_response.status_code != 200:
                    raise HTTPException(status_code=500, detail="Could not fetch OpenID configuration")
                
                config = config_response.json()
                userinfo_endpoint = config.get("userinfo_endpoint")
                
                if not userinfo_endpoint:
                    raise HTTPException(status_code=500, detail="UserInfo endpoint not found in OpenID configuration")
                
                # Make request to userinfo endpoint
                headers = {"Authorization": f"Bearer {access_token}"}
                user_response = await client.get(userinfo_endpoint, headers=headers)
                
                if user_response.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"Error fetching user info: {user_response.text}")
                
                return user_response.json()
            
        except GetAccessTokenError as e:
            error_description = e.args[0]
            raise HTTPException(status_code=400, detail=f"OAuth error: {error_description}")
        except Exception as e:
            print(f"Error getting user info: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")

# Instantiate the OAuth client for the application to use
authentik_oauth = AuthentikOAuth()
