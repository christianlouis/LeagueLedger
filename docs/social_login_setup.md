# Setting Up Social Login in LeagueLedger

LeagueLedger supports multiple social login (OAuth) providers to give your users various options for authentication. This document explains how to set up each supported provider.

## Table of Contents
1. [General Setup](#general-setup)
2. [Callback URLs](#callback-urls)
3. [Provider-Specific Instructions](#provider-specific-instructions)
   - [Google](#google)
   - [GitHub](#github)
   - [Facebook](#facebook)
   - [Microsoft](#microsoft)
   - [Discord](#discord)
   - [LinkedIn](#linkedin)
   - [Authentik](#authentik)
4. [Troubleshooting](#troubleshooting)

## General Setup

To enable social login in LeagueLedger, you need to:

1. Register your application with the desired OAuth provider(s)
2. Obtain client ID and client secret credentials
3. Add these credentials to your environment variables or `.env` file
4. Restart the application

Only providers with valid credentials will appear on the login page.

## Callback URLs

Each OAuth provider requires you to configure a **Redirect URI** (also known as a callback URL). This is where the provider redirects users after they authenticate.

For LeagueLedger, use the following pattern:
```
https://your-domain.com/auth/oauth-callback/{provider_id}
```

Replace:
- `your-domain.com` with your actual domain
- `{provider_id}` with one of: `google`, `github`, `facebook`, `microsoft`, `discord`, `linkedin`, or `authentik`

For local development, use:
```
http://localhost:8000/auth/oauth-callback/{provider_id}
```

**Important:** Most OAuth providers require exact URL matches, including protocol (http/https), domain, path, and any query parameters. Make sure to register the exact URL as shown above.

## Provider-Specific Instructions

### Google

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

### GitHub

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in your application details:
   - Application name: "LeagueLedger"
   - Homepage URL: Your app's URL or `http://localhost:8000`
   - Authorization callback URL:
     ```
     http://localhost:8000/auth/oauth-callback/github
     ```
4. Click "Register application"
5. Generate a new client secret
6. Add to your `.env` file:
   ```
   GITHUB_CLIENT_ID=your-client-id
   GITHUB_CLIENT_SECRET=your-client-secret
   ```

### Facebook

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

### Microsoft

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

### Discord

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

### LinkedIn

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

### Authentik

1. Access your Authentik admin interface
2. Go to "Applications" > "Providers" > "Create"
3. Select "OAuth2/OIDC Provider"
4. Configure the provider:
   - Name: LeagueLedger
   - Client Type: Confidential
   - Redirect URIs:
     ```
     http://localhost:8000/auth/oauth-callback/authentik
     ```
   - Signing Key: Select an appropriate key or create one
5. Save the provider
6. Create an application:
   - Go to "Applications" > "Applications" > "Create"
   - Name: LeagueLedger
   - Slug: leagueledger
   - Provider: Select the provider you just created
7. Save the application
8. Note the Client ID and Client Secret
9. Add to your `.env` file:
   ```
   AUTHENTIK_CLIENT_ID=your-client-id
   AUTHENTIK_CLIENT_SECRET=your-client-secret
   AUTHENTIK_CONFIG_URL=https://your-authentik-domain/application/o/leagueledger/.well-known/openid-configuration
   ```

## Troubleshooting

### Common Issues:

1. **Provider not showing on login page**
   - Check that client ID and secret are correctly set in your environment/`.env` file
   - Verify that values are not empty strings
   - Check application logs for initialization errors

2. **Authentication Error after provider login**
   - Verify that the redirect URI is exactly as registered with the provider
   - Check for protocol mismatch (http vs https)
   - Ensure all required scopes have been granted

3. **"Can't retrieve user email" errors**
   - Ensure you've requested the email scope from the provider
   - Some providers (like GitHub) require special permissions for email access

### Checking Provider Status:

You can check which providers are correctly configured by examining the login page:
- Only providers with valid credentials will appear as login options
- Look at application logs during startup for provider initialization messages

### Provider-Specific Tips:

- **Google**: Ensure the Google+ API is enabled in your Google Cloud project
- **GitHub**: For private email addresses, request the `user:email` scope
- **Discord**: Discord applications might need to be verified if you have a large user base
- **Microsoft**: Ensure the Microsoft Graph API permissions include User.Read

For more help, check the [official documentation](https://example.com/leagueledger/docs) or open an issue on the project repository.