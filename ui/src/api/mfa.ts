import { apiClient } from './client'
import type { MfaSetupResponse, MfaStatus } from '@/types'

export const mfaApi = {
  setupTotp: () =>
    apiClient.post<MfaSetupResponse>('/mfa/totp/setup').then((r) => r.data),

  verifyTotp: (credential_id: string, code: string) =>
    apiClient.post<{ message: string }>('/mfa/totp/verify', { credential_id, code }).then((r) => r.data),

  disable: () =>
    apiClient.delete<{ message: string }>('/mfa/disable').then((r) => r.data),

  status: () =>
    apiClient.get<MfaStatus>('/mfa/status').then((r) => r.data),
}
