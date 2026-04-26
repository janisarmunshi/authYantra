import { apiClient } from './client'
import type { RegisteredEndpoint, RegisterEndpointRequest } from '@/types'

export const endpointsApi = {
  list: (orgId: string) =>
    apiClient.get<RegisteredEndpoint[]>(`/endpoints/${orgId}`).then((r) => r.data),

  register: (orgId: string, data: RegisterEndpointRequest) =>
    apiClient.post<RegisteredEndpoint>(`/endpoints/${orgId}/register`, data).then((r) => r.data),
}
