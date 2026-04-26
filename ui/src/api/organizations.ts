import { apiClient } from './client'
import type {
  Organization,
  CreateOrganizationRequest,
  UpdateEntraIdRequest,
  RegisteredApp,
  CreateAppRequest,
} from '@/types'

export const organizationsApi = {
  create: (data: CreateOrganizationRequest) =>
    apiClient.post<Organization>('/orgs', data).then((r) => r.data),

  getById: (orgId: string) =>
    apiClient.get<Organization>(`/orgs/${orgId}`).then((r) => r.data),

  updateEntraId: (orgId: string, data: UpdateEntraIdRequest) =>
    apiClient.patch<Organization>(`/orgs/${orgId}/entra`, data).then((r) => r.data),

  // Apps
  createApp: (orgId: string, data: CreateAppRequest) =>
    apiClient.post<RegisteredApp>(`/orgs/${orgId}/apps`, data).then((r) => r.data),

  getApp: (orgId: string, appId: string) =>
    apiClient.get<RegisteredApp>(`/orgs/${orgId}/apps/${appId}`).then((r) => r.data),
}
