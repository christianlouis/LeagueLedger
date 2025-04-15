import os
from abc import ABC, abstractmethod
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.clients.github import GitHubOAuth2
from httpx_oauth.clients.facebook import FacebookOAuth2
from httpx_oauth.clients.discord import DiscordOAuth2
# LinkedIn OAuth client
from httpx_oauth.clients.linkedin import LinkedInOAuth2
# Microsoft client import may not be available in all httpx_oauth versions
try:
    from httpx_oauth.clients.microsoft import MicrosoftOAuth2
    MICROSOFT_AVAILABLE = True
except ImportError:
    # Custom implementation if the package doesn't have it
    from httpx_oauth.oauth2 import OAuth2, GetAccessTokenError
    MICROSOFT_AVAILABLE = False
    
    # Basic Microsoft OAuth2 implementation if not available in the library
    class MicrosoftOAuth2(OAuth2):
        def __init__(
            self,
            client_id: str,
            client_secret: str,
            tenant: str = "common",
        ):
            super().__init__(
                client_id=client_id,
                client_secret=client_secret,
                authorize_endpoint=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
                access_token_endpoint=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                refresh_token_endpoint=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                base_scopes=["openid", "profile", "email"],
            )

from httpx_oauth.clients.openid import OpenID
from httpx_oauth.oauth2 import GetAccessTokenError
from fastapi import HTTPException, Request
from starlette.responses import RedirectResponse
from typing import Optional, Dict, Any, List, Type
import json
import httpx
from urllib.parse import urlencode

class OAuthProvider(ABC):
    """Base class for all OAuth providers"""
    
    # Provider identifier - should be unique and lowercase
    provider_id = "base"
    
    # Display name for UI
    display_name = "Base Provider"
    
    # Icon class (for UI rendering, e.g. Font Awesome)
    icon_class = "fas fa-sign-in-alt"
    
    # Default button color (hex or valid CSS color name)
    button_color = "#333333"
    
    def __init__(self):
        self.client = None
        self.initialize_client()
    
    @abstractmethod
    def initialize_client(self):
        """Initialize the specific OAuth client"""
        pass
        
    @abstractmethod
    async def get_login_url(self, request: Request, redirect_uri: str) -> str:
        """Get the authorization URL for this provider"""
        pass
        
    @abstractmethod
    async def get_user_info(self, request: Request, redirect_uri: str, code: str) -> Dict[str, Any]:
        """Get user information from the provider"""
        pass
    
    def get_normalized_user_data(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize provider-specific user data into a standard format
        
        Returns:
            Dict with standard fields:
                - id: Unique identifier from provider
                - email: User email (if available)
                - name: User's full/display name
                - first_name: User's first name (if available)
                - last_name: User's last name (if available)
                - picture: URL to user's avatar/picture (if available)
                - raw: The original user_info dict
        """
        # Default implementation - should be overridden by providers
        return {
            "id": str(user_info.get("id", "")),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "first_name": user_info.get("given_name"),
            "last_name": user_info.get("family_name"),
            "picture": user_info.get("picture"),
            "raw": user_info
        }

class AuthentikOAuth(OAuthProvider):
    """Authentik OpenID Connect OAuth provider"""
    
    provider_id = "authentik"
    display_name = "Authentik"
    icon_class = "fas fa-shield-alt"
    button_color = "#fd4b2d"
    
    def __init__(self):
        self.client_id = os.getenv("AUTHENTIK_CLIENT_ID", "yourAuthentikClientID")
        self.client_secret = os.getenv("AUTHENTIK_CLIENT_SECRET", "yourAuthentikClientSecret")
        self.config_url = os.getenv("AUTHENTIK_CONFIG_URL", 
                                  "https://authentik.example.com/application/o/leagueledger/.well-known/openid-configuration")
        super().__init__()

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

class GoogleOAuth(OAuthProvider):
    """Google OAuth provider implementation"""
    
    provider_id = "google"
    display_name = "Google"
    icon_class = "fab fa-google"
    button_color = "#4285F4"
    
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        super().__init__()
    
    def initialize_client(self):
        if not self.client_id or not self.client_secret:
            self.client = None
            return
            
        try:
            self.client = GoogleOAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
        except Exception as e:
            print(f"Error initializing Google OAuth client: {str(e)}")
            self.client = None
    
    async def get_login_url(self, request: Request, redirect_uri: str) -> str:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="Google OAuth client could not be initialized")
        
        try:
            authorization_url = await self.client.get_authorization_url(
                redirect_uri=redirect_uri,
                scope=["openid", "email", "profile"],
                state=str(request.session.get("session_id", "")),
                extras_params={"access_type": "offline", "prompt": "select_account"}
            )
            return authorization_url
        except Exception as e:
            print(f"Error getting Google authorization URL: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    async def get_user_info(self, request: Request, redirect_uri: str, code: str) -> Dict[str, Any]:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="Google OAuth client could not be initialized")
        
        try:
            # Exchange code for token
            token = await self.client.get_access_token(
                code=code, 
                redirect_uri=redirect_uri
            )
            
            access_token = token.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="Could not get Google access token")
            
            # Get user info from Google
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"Error fetching Google user info: {response.text}")
                
                return response.json()
                
        except GetAccessTokenError as e:
            error_description = e.args[0]
            raise HTTPException(status_code=400, detail=f"Google OAuth error: {error_description}")
        except Exception as e:
            print(f"Error getting Google user info: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    def get_normalized_user_data(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        # Google specific normalization
        return {
            "id": user_info.get("sub", ""),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "first_name": user_info.get("given_name"),
            "last_name": user_info.get("family_name"),
            "picture": user_info.get("picture"),
            "raw": user_info
        }

class GitHubOAuth(OAuthProvider):
    """GitHub OAuth provider implementation"""
    
    provider_id = "github"
    display_name = "GitHub" 
    icon_class = "fab fa-github"
    button_color = "#171515"
    
    def __init__(self):
        self.client_id = os.getenv("GITHUB_CLIENT_ID", "")
        self.client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")
        super().__init__()
    
    def initialize_client(self):
        if not self.client_id or not self.client_secret:
            self.client = None
            return
            
        try:
            self.client = GitHubOAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
        except Exception as e:
            print(f"Error initializing GitHub OAuth client: {str(e)}")
            self.client = None
            
    async def get_login_url(self, request: Request, redirect_uri: str) -> str:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="GitHub OAuth client could not be initialized")
        
        try:
            authorization_url = await self.client.get_authorization_url(
                redirect_uri=redirect_uri,
                scope=["user:email"],
                state=str(request.session.get("session_id", "")),
            )
            return authorization_url
        except Exception as e:
            print(f"Error getting GitHub authorization URL: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    async def get_user_info(self, request: Request, redirect_uri: str, code: str) -> Dict[str, Any]:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="GitHub OAuth client could not be initialized")
            
        try:
            # Exchange code for token
            token = await self.client.get_access_token(
                code=code, 
                redirect_uri=redirect_uri
            )
            
            access_token = token.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="Could not get GitHub access token")
            
            # Get user info from GitHub
            user_data = {}
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                # Get user profile
                user_response = await client.get(
                    "https://api.github.com/user",
                    headers=headers
                )
                
                if user_response.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"Error fetching GitHub user info: {user_response.text}")
                
                user_data = user_response.json()
                
                # Get user emails
                email_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers=headers
                )
                
                if email_response.status_code == 200:
                    emails = email_response.json()
                    primary_email = next((email for email in emails if email.get("primary") is True), None)
                    if primary_email:
                        user_data["email"] = primary_email.get("email")
                
                return user_data
                
        except GetAccessTokenError as e:
            error_description = e.args[0]
            raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {error_description}")
        except Exception as e:
            print(f"Error getting GitHub user info: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    def get_normalized_user_data(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        # GitHub specific normalization
        name_parts = (user_info.get("name") or "").split(" ", 1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        return {
            "id": str(user_info.get("id", "")),
            "email": user_info.get("email"),
            "name": user_info.get("name") or user_info.get("login"),
            "first_name": first_name,
            "last_name": last_name,
            "picture": user_info.get("avatar_url"),
            "raw": user_info
        }

class FacebookOAuth(OAuthProvider):
    """Facebook OAuth provider implementation"""
    
    provider_id = "facebook"
    display_name = "Facebook"
    icon_class = "fab fa-facebook"
    button_color = "#1877F2"
    
    def __init__(self):
        self.client_id = os.getenv("FACEBOOK_CLIENT_ID", "")
        self.client_secret = os.getenv("FACEBOOK_CLIENT_SECRET", "")
        super().__init__()
        
    def initialize_client(self):
        if not self.client_id or not self.client_secret:
            self.client = None
            return
            
        try:
            self.client = FacebookOAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
        except Exception as e:
            print(f"Error initializing Facebook OAuth client: {str(e)}")
            self.client = None
    
    async def get_login_url(self, request: Request, redirect_uri: str) -> str:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="Facebook OAuth client could not be initialized")
        
        try:
            authorization_url = await self.client.get_authorization_url(
                redirect_uri=redirect_uri,
                scope=["email", "public_profile"],
                state=str(request.session.get("session_id", ""))
            )
            return authorization_url
        except Exception as e:
            print(f"Error getting Facebook authorization URL: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    async def get_user_info(self, request: Request, redirect_uri: str, code: str) -> Dict[str, Any]:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="Facebook OAuth client could not be initialized")
        
        try:
            # Exchange code for token
            token = await self.client.get_access_token(
                code=code,
                redirect_uri=redirect_uri
            )
            
            access_token = token.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="Could not get Facebook access token")
            
            # Get user info from Facebook
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://graph.facebook.com/me",
                    params={
                        "access_token": access_token,
                        "fields": "id,name,email,first_name,last_name,picture"
                    }
                )
                
                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"Error fetching Facebook user info: {response.text}")
                
                return response.json()
                
        except GetAccessTokenError as e:
            error_description = e.args[0]
            raise HTTPException(status_code=400, detail=f"Facebook OAuth error: {error_description}")
        except Exception as e:
            print(f"Error getting Facebook user info: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    def get_normalized_user_data(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        # Facebook specific normalization
        picture_url = None
        if "picture" in user_info and "data" in user_info["picture"]:
            picture_url = user_info["picture"]["data"].get("url")
            
        return {
            "id": user_info.get("id", ""),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "first_name": user_info.get("first_name"),
            "last_name": user_info.get("last_name"),
            "picture": picture_url,
            "raw": user_info
        }

class MicrosoftOAuth(OAuthProvider):
    """Microsoft OAuth provider implementation"""
    
    provider_id = "microsoft"
    display_name = "Microsoft"
    icon_class = "fab fa-microsoft"
    button_color = "#00A4EF"
    
    def __init__(self):
        self.client_id = os.getenv("MICROSOFT_CLIENT_ID", "")
        self.client_secret = os.getenv("MICROSOFT_CLIENT_SECRET", "")
        self.tenant = os.getenv("MICROSOFT_TENANT", "common")  # "common" for multi-tenant apps
        super().__init__()
    
    def initialize_client(self):
        if not self.client_id or not self.client_secret:
            self.client = None
            return
            
        try:
            self.client = MicrosoftOAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret,
                tenant=self.tenant
            )
        except Exception as e:
            print(f"Error initializing Microsoft OAuth client: {str(e)}")
            self.client = None
    
    async def get_login_url(self, request: Request, redirect_uri: str) -> str:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="Microsoft OAuth client could not be initialized")
        
        try:
            authorization_url = await self.client.get_authorization_url(
                redirect_uri=redirect_uri,
                scope=["User.Read", "email", "profile", "openid"],
                state=str(request.session.get("session_id", ""))
            )
            return authorization_url
        except Exception as e:
            print(f"Error getting Microsoft authorization URL: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    async def get_user_info(self, request: Request, redirect_uri: str, code: str) -> Dict[str, Any]:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="Microsoft OAuth client could not be initialized")
        
        try:
            # Exchange code for token
            token = await self.client.get_access_token(
                code=code,
                redirect_uri=redirect_uri
            )
            
            access_token = token.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="Could not get Microsoft access token")
            
            # Get user info from Microsoft Graph API
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"Error fetching Microsoft user info: {response.text}")
                
                return response.json()
                
        except GetAccessTokenError as e:
            error_description = e.args[0]
            raise HTTPException(status_code=400, detail=f"Microsoft OAuth error: {error_description}")
        except Exception as e:
            print(f"Error getting Microsoft user info: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    def get_normalized_user_data(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": user_info.get("id", ""),
            "email": user_info.get("mail") or user_info.get("userPrincipalName"),
            "name": user_info.get("displayName"),
            "first_name": user_info.get("givenName"),
            "last_name": user_info.get("surname"),
            "picture": None,  # Microsoft Graph doesn't include photo in basic profile
            "raw": user_info
        }

class DiscordOAuth(OAuthProvider):
    """Discord OAuth provider implementation"""
    
    provider_id = "discord"
    display_name = "Discord"
    icon_class = "fab fa-discord"
    button_color = "#5865F2"
    
    def __init__(self):
        self.client_id = os.getenv("DISCORD_CLIENT_ID", "")
        self.client_secret = os.getenv("DISCORD_CLIENT_SECRET", "")
        super().__init__()
    
    def initialize_client(self):
        if not self.client_id or not self.client_secret:
            self.client = None
            return
            
        try:
            self.client = DiscordOAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
        except Exception as e:
            print(f"Error initializing Discord OAuth client: {str(e)}")
            self.client = None
    
    async def get_login_url(self, request: Request, redirect_uri: str) -> str:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="Discord OAuth client could not be initialized")
        
        try:
            authorization_url = await self.client.get_authorization_url(
                redirect_uri=redirect_uri,
                scope=["identify", "email"],
                state=str(request.session.get("session_id", ""))
            )
            return authorization_url
        except Exception as e:
            print(f"Error getting Discord authorization URL: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    async def get_user_info(self, request: Request, redirect_uri: str, code: str) -> Dict[str, Any]:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="Discord OAuth client could not be initialized")
        
        try:
            # Exchange code for token
            token = await self.client.get_access_token(
                code=code,
                redirect_uri=redirect_uri
            )
            
            access_token = token.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="Could not get Discord access token")
            
            # Get user info from Discord API
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(
                    "https://discord.com/api/users/@me",
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"Error fetching Discord user info: {response.text}")
                
                return response.json()
                
        except GetAccessTokenError as e:
            error_description = e.args[0]
            raise HTTPException(status_code=400, detail=f"Discord OAuth error: {error_description}")
        except Exception as e:
            print(f"Error getting Discord user info: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    def get_normalized_user_data(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        avatar_url = None
        if user_info.get("avatar"):
            user_id = user_info.get("id")
            avatar_hash = user_info.get("avatar")
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
            
        # Discord doesn't split names, just has a username
        return {
            "id": user_info.get("id", ""),
            "email": user_info.get("email"),
            "name": user_info.get("username") or user_info.get("global_name"),
            "first_name": user_info.get("username", "").split("#", 1)[0],
            "last_name": "",
            "picture": avatar_url,
            "raw": user_info
        }

class LinkedInOAuth(OAuthProvider):
    """LinkedIn OAuth provider implementation using OpenID Connect"""
    
    provider_id = "linkedin"
    display_name = "LinkedIn"
    icon_class = "fab fa-linkedin"
    button_color = "#0077B5"
    
    # LinkedIn OIDC endpoints
    AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
    
    def __init__(self):
        self.client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
        self.client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")
        super().__init__()
    
    def initialize_client(self):
        if not self.client_id or not self.client_secret:
            self.client = None
            return
            
        try:
            # Create a custom OAuth2 client for LinkedIn OpenID Connect
            from httpx_oauth.oauth2 import OAuth2
            self.client = OAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret,
                authorize_endpoint=self.AUTHORIZATION_URL,
                access_token_endpoint=self.TOKEN_URL,
                refresh_token_endpoint=self.TOKEN_URL,
                base_scopes=["openid", "profile", "email"]
            )
        except Exception as e:
            print(f"Error initializing LinkedIn OAuth client: {str(e)}")
            self.client = None
    
    async def get_login_url(self, request: Request, redirect_uri: str) -> str:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="LinkedIn OAuth client could not be initialized")
        
        try:
            authorization_url = await self.client.get_authorization_url(
                redirect_uri=redirect_uri,
                # Using the required OpenID Connect scopes
                scope=["openid", "profile", "email"],
                state=str(request.session.get("session_id", ""))
            )
            return authorization_url
        except Exception as e:
            print(f"Error getting LinkedIn authorization URL: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    async def get_user_info(self, request: Request, redirect_uri: str, code: str) -> Dict[str, Any]:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="LinkedIn OAuth client could not be initialized")
        
        try:
            # Exchange code for token
            token = await self.client.get_access_token(
                code=code,
                redirect_uri=redirect_uri
            )
            
            access_token = token.get("access_token")
            id_token = token.get("id_token")  # JWT token containing basic user info
            
            if not access_token:
                raise HTTPException(status_code=400, detail="Could not get LinkedIn access token")
            
            # Get user info from LinkedIn UserInfo endpoint (OIDC standard endpoint)
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(
                    self.USERINFO_URL,
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"Error fetching LinkedIn user info: {response.text}")
                
                user_info = response.json()
                
                # The user info from the OIDC userinfo endpoint should already contain the 
                # email if requested in the scope, no need for a separate call
                
                return user_info
                
        except GetAccessTokenError as e:
            error_description = e.args[0]
            raise HTTPException(status_code=400, detail=f"LinkedIn OAuth error: {error_description}")
        except Exception as e:
            print(f"Error getting LinkedIn user info: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    def get_normalized_user_data(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        # LinkedIn OpenID Connect response normalization
        return {
            "id": user_info.get("sub", ""),  # 'sub' is the standard OIDC subject identifier
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "first_name": user_info.get("given_name"),
            "last_name": user_info.get("family_name"),
            "picture": user_info.get("picture"),
            "raw": user_info
        }

class NetIDOAuth(OAuthProvider):
    """NetID OAuth provider implementation"""
    
    provider_id = "netid"
    display_name = "netID"
    icon_class = "fas fa-check"  # Could be replaced with a custom netID icon class if available
    button_color = "#76b82a"
    
    # NetID OIDC endpoints
    AUTHORIZATION_URL = "https://broker.netid.de/authorize"
    TOKEN_URL = "https://broker.netid.de/token"
    USERINFO_URL = "https://broker.netid.de/userinfo"
    
    def __init__(self):
        self.client_id = os.getenv("NETID_CLIENT_ID", "")
        self.client_secret = os.getenv("NETID_CLIENT_SECRET", "")
        super().__init__()
    
    def initialize_client(self):
        if not self.client_id or not self.client_secret:
            self.client = None
            return
            
        try:
            # Create a custom OAuth2 client for NetID OpenID Connect
            from httpx_oauth.oauth2 import OAuth2
            self.client = OAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret,
                authorize_endpoint=self.AUTHORIZATION_URL,
                access_token_endpoint=self.TOKEN_URL,
                refresh_token_endpoint=self.TOKEN_URL,
                base_scopes=["openid", "email", "profile"]
            )
        except Exception as e:
            print(f"Error initializing NetID OAuth client: {str(e)}")
            self.client = None
    
    async def get_login_url(self, request: Request, redirect_uri: str) -> str:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="NetID OAuth client could not be initialized")
        
        try:
            authorization_url = await self.client.get_authorization_url(
                redirect_uri=redirect_uri,
                scope=["openid", "email", "profile"],
                state=str(request.session.get("session_id", ""))
            )
            return authorization_url
        except Exception as e:
            print(f"Error getting NetID authorization URL: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    async def get_user_info(self, request: Request, redirect_uri: str, code: str) -> Dict[str, Any]:
        if not self.client:
            self.initialize_client()
            
        if not self.client:
            raise HTTPException(status_code=500, detail="NetID OAuth client could not be initialized")
        
        try:
            # Exchange code for token
            token = await self.client.get_access_token(
                code=code,
                redirect_uri=redirect_uri
            )
            
            access_token = token.get("access_token")
            
            if not access_token:
                raise HTTPException(status_code=400, detail="Could not get NetID access token")
            
            # Get user info from NetID UserInfo endpoint
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(
                    self.USERINFO_URL,
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"Error fetching NetID user info: {response.text}")
                
                return response.json()
                
        except GetAccessTokenError as e:
            error_description = e.args[0]
            raise HTTPException(status_code=400, detail=f"NetID OAuth error: {error_description}")
        except Exception as e:
            print(f"Error getting NetID user info: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
    
    def get_normalized_user_data(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        # NetID OpenID Connect response normalization
        return {
            "id": user_info.get("sub", ""),  # 'sub' is the standard OIDC subject identifier
            "email": user_info.get("email"),
            "name": f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}".strip(),
            "first_name": user_info.get("given_name"),
            "last_name": user_info.get("family_name"),
            "picture": None,  # NetID might not provide profile picture
            "raw": user_info
        }

class OAuthManager:
    """
    Manager class for handling multiple OAuth providers
    """
    
    def __init__(self):
        self.providers: Dict[str, OAuthProvider] = {}
        self.register_default_providers()
    
    def register_default_providers(self):
        """Register all available providers"""
        self.register_provider(AuthentikOAuth())
        self.register_provider(GoogleOAuth())
        self.register_provider(FacebookOAuth())
        self.register_provider(GitHubOAuth())
        self.register_provider(MicrosoftOAuth())
        self.register_provider(DiscordOAuth())
        self.register_provider(LinkedInOAuth())
        self.register_provider(NetIDOAuth())  # Register NetID provider
    
    def register_provider(self, provider: OAuthProvider):
        """Register a new provider"""
        self.providers[provider.provider_id] = provider
    
    def get_provider(self, provider_id: str) -> Optional[OAuthProvider]:
        """Get a provider by ID"""
        return self.providers.get(provider_id)
    
    def get_available_providers(self) -> List[Dict[str, Any]]:
        """
        Get list of available providers (those with credentials configured)
        Returns a list of provider details for UI rendering
        """
        available_providers = []
        
        for provider_id, provider in self.providers.items():
            if provider.client is not None:
                available_providers.append({
                    "id": provider.provider_id,
                    "name": provider.display_name,
                    "icon": provider.icon_class,
                    "color": provider.button_color
                })
                
        return available_providers
    
    async def get_login_url(self, request: Request, provider_id: str, redirect_uri: str) -> str:
        """Get login URL for a specific provider"""
        provider = self.get_provider(provider_id)
        if not provider:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")
            
        return await provider.get_login_url(request, redirect_uri)
    
    async def get_user_info(self, request: Request, provider_id: str, 
                           redirect_uri: str, code: str) -> Dict[str, Any]:
        """Get user info from a specific provider"""
        provider = self.get_provider(provider_id)
        if not provider:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")
            
        # Get raw user info
        user_info = await provider.get_user_info(request, redirect_uri, code)
        
        # Normalize it
        return provider.get_normalized_user_data(user_info)

# Create the OAuth manager for the application to use
oauth_manager = OAuthManager()

# For backwards compatibility
authentik_oauth = oauth_manager.get_provider("authentik")
