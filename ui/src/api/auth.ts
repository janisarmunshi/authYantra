import { apiClient } from './client'
import type {
  LoginRequest,
  RegisterUserRequest,
  TokenResponse,
  ChangePasswordRequest,
  User,
} from '@/types'

export interface ResetTokenVerifyResponse {
  valid: boolean
  email?: string
  message?: string
}

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient
      .post<TokenResponse>(
        '/auth/login',
        { email: data.email, password: data.password },         // body
        { headers: { 'organization-id': data.organization_id } } // header
      )
      .then((r) => r.data),

  register: (data: RegisterUserRequest) =>
    apiClient.post<TokenResponse>('/auth/register', data).then((r) => r.data),

  refreshToken: (refresh_token: string) =>
    apiClient.post<TokenResponse>('/auth/token/refresh', { refresh_token }).then((r) => r.data),

  revokeToken: (refresh_token: string) =>
    apiClient.post('/auth/token/revoke', { refresh_token }).then((r) => r.data),

  getMe: () => apiClient.get<User>('/auth/me').then((r) => r.data),

  changePassword: (data: ChangePasswordRequest) =>
    apiClient.post('/auth/change-password', data).then((r) => r.data),

  forgotPassword: (email: string, organization_id: string) =>
    apiClient.post('/auth/forgot-password', { email, organization_id }).then((r) => r.data),

  verifyResetToken: (token: string) =>
    apiClient
      .get<ResetTokenVerifyResponse>(`/auth/reset-password/verify/${token}`)
      .then((r) => r.data),

  resetPassword: (token: string, new_password: string) =>
    apiClient.post('/auth/reset-password', { token, new_password }).then((r) => r.data),
}
