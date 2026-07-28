import { api } from './client'
import type { IngestResult, LeadManualIn, LeadOut } from './types'

export const leadsApi = {
  list: (limit = 50) => api.get<LeadOut[]>(`/leads?limit=${limit}`),
  addManual: (payload: LeadManualIn) => api.post<LeadOut>('/leads/manual', payload),
  bulkImport: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.postForm<IngestResult>('/leads/bulk-import', form)
  },
}
