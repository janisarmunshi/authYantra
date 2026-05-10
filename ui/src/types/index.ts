// ─── Organizations ────────────────────────────────────────────────────────────

export interface Organization {
  id: string
  name: string
  slug: string | null
  description: string | null
  entra_id_tenant_id: string | null
  entra_id_client_id: string | null
  is_active: boolean
  mfa_required: boolean
  created_at: string
  updated_at: string
}

export interface OrgSummary {
  id: string
  name: string
  role: string
  is_default: boolean
}

export interface OrgMember {
  user_id: string
  email: string
  username: string | null
  role: string
  is_default: boolean
  joined_at: string
}

export interface OrgInvite {
  id: string
  invited_email: string
  role: string
  expires_at: string
  accepted_at: string | null
}

export interface CreateOrganizationRequest {
  name: string
}

export interface UpdateEntraIdRequest {
  tenant_id: string
  client_id: string
  client_secret: string
}

export type MembershipRole = 'owner' | 'admin' | 'developer' | 'auditor' | 'billing' | 'member'

// ─── Identity Providers ───────────────────────────────────────────────────────

export type IdpType = 'google' | 'github' | 'microsoft' | 'facebook' | 'linkedin' | 'saml' | 'oidc' | 'magic_link'

export interface IdentityProvider {
  id: string
  name: string
  type: IdpType
  is_active: boolean
  auto_provision: boolean
  default_role: MembershipRole
  created_at: string
  updated_at: string
}

export interface CreateIdentityProviderRequest {
  name: string
  type: IdpType
  config: Record<string, unknown>
  attribute_mapping: Record<string, string>
  auto_provision: boolean
  default_role: MembershipRole
}

export interface UpdateIdentityProviderRequest {
  name?: string
  config?: Record<string, unknown>
  attribute_mapping?: Record<string, string>
  auto_provision?: boolean
  default_role?: MembershipRole
  is_active?: boolean
}

// ─── Users ────────────────────────────────────────────────────────────────────

export interface User {
  id: string
  organization_id: string | null
  email: string
  email_verified: boolean
  username: string | null
  display_name: string | null
  avatar_url: string | null
  is_active: boolean
  is_locked: boolean
  mfa_enabled: boolean
  entra_id: string | null
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface RegisterUserRequest {
  email: string
  password: string
  username?: string
}

export interface LoginRequest {
  email: string
  password: string
  mfa_code?: string
}

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

// ─── Tokens ───────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginResponse extends TokenResponse {
  expires_in: number
  org_id: string | null
  needs_org_selection: boolean
  organizations: OrgSummary[]
  mfa_required: boolean
  mfa_token: string | null
}

export interface TokenPayload {
  sub: string
  org_id: string | null
  roles: string[]
  type: string
  exp: number
  iat: number
}

// ─── Roles ────────────────────────────────────────────────────────────────────

export interface Role {
  id: string
  organization_id: string
  name: string
  description: string | null
  permissions: Record<string, string[]>
  is_active: boolean
  is_system: boolean
  created_at: string
  updated_at: string
}

export interface CreateRoleRequest {
  name: string
  description?: string
  permissions: Record<string, string[]>
}

export interface UpdateRoleRequest {
  name?: string
  description?: string
  permissions?: Record<string, string[]>
  is_active?: boolean
}

// ─── Apps ─────────────────────────────────────────────────────────────────────

export interface RegisteredApp {
  id: string
  organization_id: string
  app_name: string
  app_type: 'web' | 'desktop' | 'mobile' | 'service'
  client_id: string | null
  api_key: string
  redirect_uris: string[]
  allowed_scopes: string[]
  allowed_grant_types: string[]
  access_token_lifetime: number
  refresh_token_lifetime: number
  is_active: boolean
  is_confidential: boolean
  created_at: string
  updated_at: string
}

export interface CreateAppRequest {
  app_name: string
  app_type: 'web' | 'desktop' | 'mobile' | 'service'
  redirect_uris: string[]
  allowed_scopes?: string[]
  allowed_grant_types?: string[]
  is_confidential?: boolean
}

// ─── Endpoints ────────────────────────────────────────────────────────────────

export interface RegisteredEndpoint {
  id: string
  organization_id: string
  endpoint: string
  actions: string[]
  description: string | null
  created_at: string
  updated_at: string
}

export interface RegisterEndpointRequest {
  endpoint: string
  actions: string[]
  description?: string
}

// ─── MFA ──────────────────────────────────────────────────────────────────────

export interface MfaSetupResponse {
  credential_id: string
  totp_uri: string
  secret: string
  backup_codes: string[]
}

export interface MfaStatus {
  enabled: boolean
  type: string | null
  last_used_at: string | null
}

// ─── Audit Log ────────────────────────────────────────────────────────────────

export interface AuditLog {
  id: string
  org_id: string | null
  user_id: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  ip_address: string | null
  status: 'success' | 'failure'
  details: Record<string, unknown> | null
  created_at: string
}

// ─── Auth Context ─────────────────────────────────────────────────────────────

export interface AuthUser {
  user_id: string
  org_id: string | null
  email: string
  roles: string[]
}
