import { apiClient } from './client'
import type { Role, CreateRoleRequest, UpdateRoleRequest } from '@/types'

export const rolesApi = {
  list: (orgId: string) =>
    apiClient.get<Role[]>(`/roles/${orgId}`).then((r) => r.data),

  create: (orgId: string, data: CreateRoleRequest) =>
    apiClient.post<Role>(`/roles/${orgId}`, data).then((r) => r.data),

  update: (orgId: string, roleId: string, data: UpdateRoleRequest) =>
    apiClient.patch<Role>(`/roles/${orgId}/${roleId}`, data).then((r) => r.data),

  delete: (orgId: string, roleId: string) =>
    apiClient.delete(`/roles/${orgId}/${roleId}`).then((r) => r.data),

  // User-role assignment
  assignRole: (userId: string, orgId: string, roleId: string) =>
    apiClient.post(`/users/${userId}/roles/${orgId}`, { role_id: roleId }).then((r) => r.data),

  removeRole: (userId: string, orgId: string, roleId: string) =>
    apiClient.delete(`/users/${userId}/roles/${orgId}/${roleId}`).then((r) => r.data),

  getUserRoles: (userId: string, orgId: string) =>
    apiClient.get<Role[]>(`/users/${userId}/roles/${orgId}`).then((r) => r.data),
}
