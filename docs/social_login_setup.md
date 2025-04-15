# Social Login Setup

This guide provides instructions for setting up various social login providers for LeagueLedger.

## Table of Contents
- [Google OAuth Setup](#google-oauth-setup)
- [Facebook Login Setup](#facebook-login-setup) 
- [GitHub OAuth Setup](#github-oauth-setup)
- [LinkedIn OAuth Setup](#linkedin-oauth-setup)
- [Microsoft OAuth Setup](#microsoft-oauth-setup)
- [Discord OAuth Setup](#discord-oauth-setup)
- [NetID OAuth Setup](#netid-oauth-setup)

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Select "Web application" as the application type
6. Add the following authorized redirect URI:
   ```
   http://localhost:8000/auth/oauth-callback/google
   ```
   (Plus your production URL if applicable)
7. Click "Create"
8. Note the Client ID and Client Secret
9. Add to your `.env` file:
   ```
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

## Facebook Login Setup

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new app (choose "Consumer" or "Business" type)
3. Navigate to "Add a Product" > "Facebook Login" > "Web"
4. In Settings > Basic, note your App ID and App Secret
5. In Facebook Login > Settings, add the following OAuth Redirect URI:
   ```
   http://localhost:8000/auth/oauth-callback/facebook
   ```
6. Add to your `.env` file:
   ```
   FACEBOOK_CLIENT_ID=your-app-id
   FACEBOOK_CLIENT_SECRET=your-app-secret
   ```

## GitHub OAuth Setup

### 1. Create a GitHub OAuth App

1. Go to your GitHub account settings
2. Click on "Developer settings" in the left sidebar
3. Click on "OAuth Apps" and then "New OAuth App"
4. Fill out the form:
   - **Application name**: LeagueLedger
   - **Homepage URL**: Your site's URL (e.g. https://leagueledger.com)
   - **Application description**: (Optional) A description of your app
   - **Authorization callback URL**: Your callback URL (e.g. https://leagueledger.com/auth/oauth-callback/github)
5. Click "Register application"
6. You'll receive a Client ID
7. Click "Generate a new client secret" to create your Client Secret
8. Save both the Client ID and Client Secret safely

### 2. Configure Environment Variables

Add the following variables to your `.env` file:

```
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

### 3. Security Considerations

- **Never commit your Client Secret to version control**
- Store your Client Secret securely in environment variables or a secret management system
- In production, update the callback URL to use your production domain
- Consider implementing additional security measures like CSRF protection

### 4. Testing GitHub Login

After configuration:
1. Ensure the server is running with the environment variables loaded
2. Navigate to the login page
3. Click the "Login with GitHub" button
4. You should be redirected to GitHub's authorization page
5. After authorizing, you should be redirected back to your application and logged in

### 5. Troubleshooting GitHub OAuth

- **Invalid callback URL**: Ensure the callback URL registered in GitHub matches exactly what your application uses
- **Rate limiting**: GitHub has API rate limits that might affect your OAuth flow
- **Scope issues**: If you're not receiving email information, ensure you've requested the `user:email` scope
- **Token refresh**: If tokens expire, implement a refresh flow

## LinkedIn OAuth Setup

1. Go to the [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
2. Click "Create app"
3. Fill in the required app details:
   - App name: "LeagueLedger"
   - LinkedIn Page: Your company's LinkedIn page (or your personal page if needed)
   - App logo: Upload your app logo
   - Legal agreement: Accept the terms
4. Click "Create app"
5. Add the "Sign In with LinkedIn" product to your app
6. Configure OAuth settings:
   - Authorized redirect URLs:
     ```
     http://localhost:8000/auth/oauth-callback/linkedin
     ```
     (Plus your production URL if applicable)
7. Under "OAuth 2.0 settings", note the Client ID and generate a Client Secret
8. Request the appropriate scopes:
   - r_liteprofile (for basic profile information)
   - r_emailaddress (for user email address)
9. Add to your `.env` file:
   ```
   LINKEDIN_CLIENT_ID=your-client-id
   LINKEDIN_CLIENT_SECRET=your-client-secret
   ```

## Microsoft OAuth Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to "App registrations"
3. Click "New registration"
4. Enter a name for your application
5. For "Supported account types," choose an option based on your needs
   (typically "Accounts in any organizational directory and personal Microsoft accounts")
6. Add the following Redirect URI (type: Web):
   ```
   http://localhost:8000/auth/oauth-callback/microsoft
   ```
7. Click "Register"
8. Note the Application (client) ID
9. Create a client secret: Navigate to "Certificates & secrets" > "New client secret"
10. Add to your `.env` file:
    ```
    MICROSOFT_CLIENT_ID=your-client-id
    MICROSOFT_CLIENT_SECRET=your-client-secret
    MICROSOFT_TENANT=common
    ```
    Note: Use `common` for multi-tenant apps, or your specific tenant ID

## Discord OAuth Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Enter a name and click "Create"
4. Go to the "OAuth2" section in the left sidebar
5. Note the Client ID and generate a Client Secret
6. Add the following redirect URL:
   ```
   http://localhost:8000/auth/oauth-callback/discord
   ```
7. In the "OAuth2 URL Generator" section, select the "identify" and "email" scopes
8. Add to your `.env` file:
   ```
   DISCORD_CLIENT_ID=your-client-id
   DISCORD_CLIENT_SECRET=your-client-secret
   ```

## NetID OAuth Setup

### 1. Create a NetID Service

1. Go to the [NetID Developer Zone](https://developer.netid.de/)
2. Create an account or log in with your existing credentials
3. Go to "Services" in the menu and click "Add service"
4. Fill in the required details:
   - **Service domain**: Your site's domain (e.g., leagueledger.com)
   - **URL privacy policy**: Link to your privacy policy
   - **URL terms of usage**: Link to your terms of service
   - Click "Add service"

### 2. Create a NetID Client

1. In your service's detail view, click "Add client"
2. Select the application type:
   - For web application: select "Website"
   - For mobile apps: select "Native / Mobile App (PKCE)"
3. Fill out the required fields:
   - **Name**: "LeagueLedger"
   - **Callback URL**: Your callback URL (e.g., https://leagueledger.com/auth/oauth-callback/netid)
   - **Token signing**: Select "RS256" (recommended)
4. Save the client configuration
5. Note the Client ID and Client Secret

### 3. Configure Environment Variables

Add the following variables to your `.env` file:

```
NETID_CLIENT_ID=your_netid_client_id
NETID_CLIENT_SECRET=your_netid_client_secret
```

### 4. Testing

During development, you'll need to:
1. Add test users to your service in the NetID Developer Zone
2. Use these test users when testing the login functionality
3. Request production approval once your integration is ready

### 5. Requesting Production Approval

When ready for production:
1. Go to your service's details in the NetID Developer Zone
2. Click "Request service release"
3. NetID will review your integration and approve it for production use

### 6. Helpful Resources

- [NetID Technical Documentation](https://developer.netid.de/single-sign-on-integration/technical-details/)
- [NetID Styleguide](https://developer.netid.de/single-sign-on-integration/styleguide/) for button styling requirements