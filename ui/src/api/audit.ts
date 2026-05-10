import { apiClient } from './client'
import type { AuditLog } from '@/types'

export interface AuditLogFilters {
  action?: string
  user_id?: string
  status?: 'success' | 'failure'
  from_date?: string
  to_date?: string
  limit?: number
  offset?: number
}

export const auditApi = {
  list: (orgId: string, filters: AuditLogFilters = {}) => {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, v]) => v !== undefined && v !== '')
    )
    return apiClient
      .get<AuditLog[]>(`/admin/orgs/${orgId}/audit-logs`, { params })
      .then((r) => r.data)
  },
}
