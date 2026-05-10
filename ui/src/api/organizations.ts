import { apiClient } from './client'
import type {
  Organization, CreateOrganizationRequest, UpdateEntraIdRequest,
  RegisteredApp, CreateAppRequest, OrgMember, OrgInvite,
  IdentityProvider, CreateIdentityProviderRequest, UpdateIdentityProviderRequest,
} from '@/types'

export const organizationsApi = {
  create: (data: CreateOrganizationRequest) =>
    apiClient.post<Organization & { access_token: string; refresh_token: string; expires_in: number }>('/orgs', data).then((r) => r.data),

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

  deleteOrg: (orgId: string) =>
    apiClient.delete(`/orgs/${orgId}`).then((r) => r.data),

  // Apps
  listApps: (orgId: string) =>
    apiClient.get<RegisteredApp[]>(`/orgs/${orgId}/apps`).then((r) => r.data),

  createApp: (orgId: string, data: CreateAppRequest) =>
    apiClient.post<RegisteredApp>(`/orgs/${orgId}/apps`, data).then((r) => r.data),

  deleteApp: (orgId: string, appId: string) =>
    apiClient.delete(`/orgs/${orgId}/apps/${appId}`).then((r) => r.data),

  getApp: (orgId: string, appId: string) =>
    apiClient.get<RegisteredApp>(`/orgs/${orgId}/apps/${appId}`).then((r) => r.data),

  // Identity Providers
  listIdps: (orgId: string) =>
    apiClient.get<IdentityProvider[]>(`/orgs/${orgId}/idps`).then((r) => r.data),

  createIdp: (orgId: string, data: CreateIdentityProviderRequest) =>
    apiClient.post<IdentityProvider>(`/orgs/${orgId}/idps`, data).then((r) => r.data),

  updateIdp: (orgId: string, idpId: string, data: UpdateIdentityProviderRequest) =>
    apiClient.patch<IdentityProvider>(`/orgs/${orgId}/idps/${idpId}`, data).then((r) => r.data),

  deleteIdp: (orgId: string, idpId: string) =>
    apiClient.delete(`/orgs/${orgId}/idps/${idpId}`).then((r) => r.data),
}
