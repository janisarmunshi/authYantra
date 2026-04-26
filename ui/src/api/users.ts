import { apiClient } from './client'
import type { User } from '@/types'

export const usersApi = {
  list: (orgId: string) =>
    apiClient.get<User[]>(`/users/${orgId}`).then((r) => r.data),

  delete: (orgId: string, userId: string) =>
    apiClient.delete(`/users/${orgId}/${userId}`).then((r) => r.data),
}
