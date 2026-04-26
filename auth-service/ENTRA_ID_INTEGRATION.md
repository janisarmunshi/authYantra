# Microsoft Entra ID Integration Guide

## Phase 2: OAuth 2.0 SSO Authentication

This guide explains how to integrate Microsoft Entra ID (Azure AD) with the Auth Service for Single Sign-On (SSO) authentication.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Entra ID Setup](#entra-id-setup)
4. [Configuration](#configuration)
5. [API Endpoints](#api-endpoints)
6. [OAuth 2.0 Flow](#oauth-20-flow)
7. [Client Implementation](#client-implementation)
8. [Security Considerations](#security-considerations)
9. [Troubleshooting](#troubleshooting)

## Overview

The Auth Service now supports Microsoft Entra ID authentication using OAuth 2.0 Authorization Code flow with PKCE protection. Features include:

- **SSO Authentication**: Users can log in using their Microsoft Entra ID credentials
- **Auto User Creation**: New users are automatically created on first login
- **Account Linking**: Existing local users can link their Entra ID account
- **PKCE Protection**: Secure code authorization flow
- **Multi-Tenant**: Each organization can have separate Entra ID configuration

## Prerequisites

1. **Microsoft Azure Tenant**: You need access to an Azure tenant (M365, Office 365, etc.)
2. **Application Registration**: Entra ID app registered in Azure Portal
3. **Auth Service**: Phase 1 (local auth) fully deployed
4. **Network Access**: HTTPS callback URL accessible from Microsoft services

## Entra ID Setup

### Step 1: Register Application in Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Entra ID** > **App registrations** > **New registration**
3. **Name**: "Auth Service"
4. **Supported account types**: Select based on your needs:
   - Single organization (recommended for internal use)
   - Any organization (for multi-tenant)
5. **Redirect URI**: Select "Web" and enter your callback URL:
   ```
   https://yourdomain.com/auth/entra/callback
   ```
6. Click **Register**

### Step 2: Configure Redirect URIs

1. In app registration, go to **Redirect URIs**
2. Add all callback URLs for your environments:
   ```
   https://yourdomain.com/auth/entra/callback        # Production
   https://staging.yourdomain.com/auth/entra/callback # Staging
   http://localhost:8000/auth/entra/callback          # Local development
   ```
3. Select "Web" for each URI

### Step 3: Create Client Secret

1. Go to **Certificates & secrets** > **New client secret**
2. **Description**: "Auth Service"
3. **Expires**: Select "24 months" or preferred duration
4. Copy the **Value** (not the ID)
5. Save this securely - you'll need it in configuration

### Step 4: Get Tenant ID

1. In Entra ID, go to **Overview**
2. Copy the **Directory (tenant) ID**
3. Format: `00000000-0000-0000-0000-000000000000`

### Step 5: Get Application ID

1. In your app registration **Overview**
2. Copy the **Application (client) ID**

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# Microsoft Entra ID
ENTRA_ID_TENANT_ID=00000000-0000-0000-0000-000000000000
ENTRA_ID_CLIENT_ID=your-client-id
ENTRA_ID_CLIENT_SECRET=your-client-secret

# OAuth 2.0 settings (already in config.py with defaults)
OAUTH_STATE_EXPIRY=600
OAUTH_CODE_EXPIRY=3600
ENTRA_ID_SCOPE=User.Read profile email
```

### Per-Organization Configuration

If you have multiple Entra ID tenants (different organizations), configure each:

1. Create organization:
```bash
curl -X POST "http://localhost:8000/orgs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "entra_id_tenant_id": "tenant-guid-here"
  }'
```

2. Update with Entra ID credentials:
```bash
curl -X PUT "http://localhost:8000/orgs/{org_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "entra_id_client_id": "client-id",
    "entra_id_client_secret": "client-secret"
  }'
```

## API Endpoints

### 1. Get Authorization URL

Start the Entra ID login flow.

**Request:**
```
GET /auth/entra/authorize?organization_id={org_id}&redirect_uri={uri}&link_account={bool}

Query Parameters:
- organization_id: UUID of organization
- redirect_uri: URL to return to after login (must be registered in Entra ID)
- link_account: true if linking to existing account (default: false)
```

**Response:**
```json
{
  "authorization_url": "https://login.microsoftonline.com/...",
  "state": "csrf_protection_token"
}
```

**Example:**
```bash
curl -X GET "http://localhost:8000/auth/entra/authorize?organization_id=550e8400-e29b-41d4-a716-446655440000&redirect_uri=http://localhost:3000/sso/callback"
```

### 2. OAuth Callback Handler

Entra ID redirects here after user authentication.

**Request:**
```
GET /auth/entra/callback?code={code}&state={state}&organization_id={org_id}

Query Parameters:
- code: Authorization code from Entra ID
- state: CSRF token (must match)
- organization_id: Organization UUID
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### 3. Link Account (Authenticated)

Link Entra ID to existing local user account.

**Request:**
```
POST /auth/entra/link-account
Headers:
- Authorization: Bearer {access_token}

Body:
{
  "entra_id": "00000000-0000-0000-0000-000000000000"
}
```

**Response:**
```json
{
  "message": "Account linked successfully"
}
```

### 4. Unlink Account (Authenticated)

Remove Entra ID from user account.

**Request:**
```
POST /auth/entra/unlink-account
Headers:
- Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "message": "Account unlinked successfully"
}
```

## OAuth 2.0 Flow

### Complete Authentication Flow

```
┌─────────┐                                 ┌──────────────┐
│         │                                 │              │
│ Client  │                                 │  Microsoft   │
│(Web/    │                                 │  Entra ID    │
│Desktop) │                                 │              │
└────┬────┘                                 └──────┬───────┘
     │                                             │
     │ 1. GET /auth/entra/authorize               │
     ├────────────────────────────────────────>   │
     │        org_id, redirect_uri, state stored  │
     │                 authorization_url returned │
     │ <────────────────────────────────────────  │
     │                                             │
     │ 2. Redirect to authorization_url           │
     ├────────────────────────────────────────>   │
     │                                             │
     │ 3. User logs in to Microsoft               │
     │                                             │
     │ 4. Microsoft redirects with code & state   │
     │ <────────────────────────────────────────  │
     │                                             │
     │ 5. POST code & state to /auth/entra/callback
     │    (backend does this securely)            │
     │                                             │
     │    Server exchanges code for token →  HERE │
     │    Gets user info from Graph API  ────>   │
     │                                             │
     │ 6. User created/linked, JWT tokens returned
     │ <────────────────────────────────────────  │
     │                                             │
     │ 7. Redirect client to success page         │
     │    with tokens in URL or cookie            │
     │ <────────────────────────────────────────  │
```

### Detailed Step-by-Step

1. **Client initiates login**
   - User clicks "Sign in with Microsoft"
   - Client calls `GET /auth/entra/authorize`
   - Auth Service generates PKCE pair and state token
   - Stores state & code_verifier in database
   - Returns authorization URL

2. **User authenticates with Microsoft**
   - Client redirects user to authorization_url
   - User logs in to Entra ID
   - Microsoft redirects to your callback URL with auth code

3. **Auth Service processes callback**
   - Backend receives auth code and state
   - Verifies state against database
   - Exchanges code for access token (using PKCE)
   - Calls Microsoft Graph API to get user info
   - Checks if user exists (by Entra ID object ID)
   - Creates new user or links to existing

4. **Return tokens to client**
   - Generates JWT access + refresh tokens
   - Returns tokens in response
   - Client stores tokens and makes authenticated requests

## Client Implementation

### Web Application (React/Vue/Angular)

```javascript
// 1. Start SSO login
const startEntraLogin = async () => {
  const response = await fetch('http://localhost:8000/auth/entra/authorize', {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      organization_id: ORG_ID,
      redirect_uri: 'http://localhost:3000/sso/callback',
      link_account: false
    })
  });

  const { authorization_url } = await response.json();
  window.location.href = authorization_url;
};

// 2. Handle callback (in /sso/callback route)
const handleCallback = async () => {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  const state = params.get('state');
  const org_id = params.get('organization_id');

  const response = await fetch('http://localhost:8000/auth/entra/callback', {
    method: 'GET',
    body: new URLSearchParams({
      code,
      state,
      organization_id: org_id
    })
  });

  const { access_token, refresh_token } = await response.json();

  // Store tokens
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('refresh_token', refresh_token);

  // Redirect to dashboard
  window.location.href = '/dashboard';
};

// 3. Account linking
const linkEntraAccount = async (entraid) => {
  const response = await fetch('http://localhost:8000/auth/entra/link-account', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    },
    body: JSON.stringify({ entra_id: entraid })
  });

  if (response.ok) {
    alert('Account linked successfully');
  }
};
```

### Desktop Application

For desktop apps, use a local browser redirect:

1. Start local web server on `http://localhost:8001`
2. Register `http://localhost:8001/sso/callback` in Entra ID
3. Start SSO: redirect browser to authorization URL
4. Handle callback, extract tokens
5. Use tokens for API calls

### Mobile Application

For mobile apps, use:
- OAuth 2.0 Authorization Code with PKCE
- Native browser/in-app browser for login
- Callback to app deep link: `myapp://oauth/callback?code=...&state=...`

## Security Considerations

### CSRF Protection

- State token verified on callback
- Token stored in database and matched
- Expires after 10 minutes (configurable)

### PKCE Protection

- Code verifier stored securely on server
- Code challenge sent to Entra ID
- Code verifier required when exchanging code
- Prevents authorization code interception

### Token Security

- Access tokens: 15-minute expiry (can't be stolen long-term)
- Refresh tokens: 7-day expiry, rotated on use
- Tokens hashed in database
- Never expose client secret to client

### Production Checklist

- [ ] Use HTTPS for all endpoints (not HTTP)
- [ ] Redirect URIs must be HTTPS
- [ ] Store client secret in secure vault (not in code)
- [ ] Rotate client secrets every 90 days
- [ ] Enable MFA for Entra ID admin accounts
- [ ] Monitor failed login attempts
- [ ] Implement rate limiting on auth endpoints
- [ ] Log all authentication events
- [ ] Regular security audits

## Troubleshooting

### Issue: "state token mismatch"

**Cause**: Callback state doesn't match stored state

**Solution**:
1. Check database has EntraIDSession record
2. Verify state parameter in callback URL
3. Check state expiry (10 minutes default)
4. Look for clock skew between servers

### Issue: "Organization not found"

**Cause**: Invalid organization_id

**Solution**:
1. Verify organization_id exists
2. Check organization is active

### Issue: "Organization not configured for Entra ID"

**Cause**: Missing Entra ID credentials on organization

**Solution**:
1. Set `entra_id_tenant_id` on organization
2. Set `entra_id_client_id` on organization
3. Set `entra_id_client_secret` on organization

### Issue: "error_description: AADSTS65001 - User or admin has not consented"

**Cause**: Admin consent not granted for app

**Solution**:
1. Go to Azure Portal
2. Entra ID > App registrations > Auth Service
3. API permissions > Grant admin consent for {tenant}

### Issue: "Invalid redirect_uri"

**Cause**: Callback URL not registered in Entra ID

**Solution**:
1. Go to App registration
2. Authentication > Redirect URIs
3. Add exact callback URL (must be HTTPS in production)
4. Must match `send_to` parameter after login

### Issue: "User already linked to another account"

**Cause**: Trying to link Entra ID that's already linked

**Solution**:
1. Unlink from other account first
2. Or use a different Entra ID account

## Testing

### Manual Testing

1. **Local Setup**:
   ```bash
   # Start auth service
   python -m uvicorn main:app --reload

   # Start test client (in another terminal)
   # Use your web app or curl
   ```

2. **Test SSO Flow**:
   ```bash
   # Get authorization URL
   curl "http://localhost:8000/auth/entra/authorize?organization_id={orgid}&redirect_uri=http://localhost:3000/callback"

   # Visit the returned authorization_url in browser
   # After login, you'll be redirected with code & state

   # Exchange code for tokens
   curl "http://localhost:8000/auth/entra/callback?code={code}&state={state}&organization_id={orgid}"
   ```

3. **Test Account Linking**:
   ```bash
   # First log in with password
   curl -X POST "http://localhost:8000/auth/login" \
     -H "Organization-ID: {orgid}" \
     -d '{
       "email": "user@example.com",
       "password": "password"
     }'

   # Then link Entra ID
   curl -X POST "http://localhost:8000/auth/entra/link-account" \
     -H "Authorization: Bearer {access_token}" \
     -d '{"entra_id": "entra-object-id"}'
   ```

### Automated Testing

Tests are in `tests/test_entra_id.py`:

```bash
# Run all Entra ID tests
pytest tests/test_entra_id.py -v

# Run specific test
pytest tests/test_entra_id.py::test_generate_authorization_url_success -v

# Run with coverage
pytest tests/test_entra_id.py --cov
```

## Advanced Topics

### Multi-Tenant Setup

Each organization can have different Entra ID tenants:

```python
# Organization A uses Entra ID tenant 1
org_a.entra_id_tenant_id = "00000000-0000-0000-0000-000000000001"

# Organization B uses Entra ID tenant 2
org_b.entra_id_tenant_id = "00000000-0000-0000-0000-000000000002"

# Auth service routes to correct tenant automatically
```

### Group-Based Authorization (Phase 3+)

Future enhancement to sync Entra ID groups to local roles:

```python
# Retrieve user's groups from Graph API
# Map groups to local roles
# Assign roles on user creation
```

### Conditional Access

Leverage Entra ID's Conditional Access policies:
- Require MFA for specific users
- Block access from untrusted locations
- Enforce Windows Hello for WorkNow users

## Support & Documentation

- [Entra ID Documentation](https://docs.microsoft.com/en-us/entra/)
- [OAuth 2.0 Standard](https://tools.ietf.org/html/rfc6749)
- [PKCE (RFC 7636)](https://tools.ietf.org/html/rfc7636)
- [Microsoft Graph API](https://docs.microsoft.com/en-us/graph/)

## Next Steps

1. Test Phase 2 integration in development
2. Deploy to staging, verify with test tenant
3. Move to production with real Entra ID tenant
4. Monitor authentication metrics
5. Plan Phase 3 (group sync) or Phase 4 (hardening)
