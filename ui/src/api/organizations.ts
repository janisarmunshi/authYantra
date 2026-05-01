import { apiClient } from './client'
import type {
  Organization, CreateOrganizationRequest, UpdateEntraIdRequest,
  RegisteredApp, CreateAppRequest, OrgMember, OrgInvite,
} from '@/types'

export const organizationsApi = {
  create: (data: CreateOrganizationRequest) =>
    apiClient.post<Organization>('/orgs', data).then((r) => r.data),

  getById: (orgId: string) =>
    apiClient.get<Organization>(`/orgs/${orgId}`).then((r) => r.data),

  updateEntraId: (orgId: string, data: UpdateEntraIdRequest) =>
    apiClient.patch<Organization>(`/orgs/${orgId}/entra`, data).then((r) => r.data),

  // Members
  listMembers: (orgId: string) =>
    apiClient.get<OrgMember[]>(`/orgs/${orgId}/members`).then((r) => r.data),

  addMember: (orgId: string, email: string, role: string) =>
    apiClient.post(`/orgs/${orgId}/members`, { email, role }).then((r) => r.data),

  removeMember: (orgId: string, userId: string) =>
    apiClient.delete(`/orgs/${orgId}/members/${userId}`).then((r) => r.data),

  // Invites
  invite: (orgId: string, email: string, role: string) =>
    apiClient.post<OrgInvite>(`/orgs/${orgId}/invite`, { email, role }).then((r) => r.data),

  listInvites: (orgId: string) =>
    apiClient.get<OrgInvite[]>(`/orgs/${orgId}/invites`).then((r) => r.data),

  // Apps
  createApp: (orgId: string, data: CreateAppRequest) =>
    apiClient.post<RegisteredApp>(`/orgs/${orgId}/apps`, data).then((r) => r.data),

  getApp: (orgId: string, appId: string) =>
    apiClient.get<RegisteredApp>(`/orgs/${orgId}/apps/${appId}`).then((r) => r.data),
}
