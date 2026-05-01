// ─── Organizations ────────────────────────────────────────────────────────────

export interface Organization {
  id: string
  name: string
  entra_id_tenant_id: string | null
  entra_id_client_id: string | null
  is_active: boolean
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

// ─── Users ────────────────────────────────────────────────────────────────────

export interface User {
  id: string
  organization_id: string | null
  email: string
  username: string | null
  is_active: boolean
  entra_id: string | null
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
  permissions: Record<string, string[]>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateRoleRequest {
  name: string
  permissions: Record<string, string[]>
}

export interface UpdateRoleRequest {
  name?: string
  permissions?: Record<string, string[]>
  is_active?: boolean
}

// ─── Apps ─────────────────────────────────────────────────────────────────────

export interface RegisteredApp {
  id: string
  organization_id: string
  app_name: string
  app_type: 'web' | 'desktop' | 'mobile'
  api_key: string
  redirect_uris: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateAppRequest {
  app_name: string
  app_type: 'web' | 'desktop' | 'mobile'
  redirect_uris: string[]
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

// ─── Auth Context ─────────────────────────────────────────────────────────────

export interface AuthUser {
  user_id: string
  org_id: string | null
  email: string
  roles: string[]
}
