import { apiClient } from './client'
import type { LoginRequest, LoginResponse, RegisterUserRequest, TokenResponse, OrgSummary, User } from '@/types'

export interface ResetTokenVerifyResponse {
  valid: boolean
  email?: string
  message?: string
}

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>('/auth/login', { email: data.email, password: data.password })
      .then((r) => r.data),

  register: (data: RegisterUserRequest) =>
    apiClient.post<{ message: string; user_id: string }>('/auth/register', data).then((r) => r.data),

  refreshToken: (refresh_token: string) =>
    apiClient.post<TokenResponse>('/auth/token/refresh', { refresh_token }).then((r) => r.data),

  revokeToken: (refresh_token: string) =>
    apiClient.post('/auth/token/revoke', { refresh_token }).then((r) => r.data),

  getMe: () => apiClient.get<User>('/auth/me').then((r) => r.data),

  myOrgs: () => apiClient.get<OrgSummary[]>('/auth/my-orgs').then((r) => r.data),

  switchOrg: (orgId: string) =>
    apiClient.post<TokenResponse>(`/auth/switch-org/${orgId}`).then((r) => r.data),

  setDefaultOrg: (orgId: string) =>
    apiClient.patch(`/auth/default-org/${orgId}`).then((r) => r.data),

  acceptInvite: (token: string) =>
    apiClient.post('/auth/accept-invite', { token }).then((r) => r.data),

  changePassword: (data: { old_password: string; new_password: string }) =>
    apiClient.post('/auth/change-password', data).then((r) => r.data),

  forgotPassword: (email: string) =>
    apiClient.post('/auth/forgot-password', { email }).then((r) => r.data),

  verifyResetToken: (token: string) =>
    apiClient.get<ResetTokenVerifyResponse>(`/auth/reset-password/verify/${token}`).then((r) => r.data),

  resetPassword: (token: string, new_password: string) =>
    apiClient.post('/auth/reset-password', { token, new_password }).then((r) => r.data),
}
