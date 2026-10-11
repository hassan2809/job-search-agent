import { api } from './client'
import type { FitStatusFilter, IngestResult, LeadListOut, LeadManualIn, LeadOut, OriginType, OutreachStatusFilter } from './types'

export interface LeadFilters {
  originType?: OriginType
  fitStatus?: FitStatusFilter
  outreachStatus?: OutreachStatusFilter
  search?: string
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, String(value))
  }
  return search.toString()
}

export const leadsApi = {
  list: (limit = 20, offset = 0, filters: LeadFilters = {}) =>
    api.get<LeadListOut>(
      `/leads?${buildQuery({
        limit,
        offset,
        origin_type: filters.originType,
        fit_status: filters.fitStatus,
        outreach_status: filters.outreachStatus,
        search: filters.search || undefined,
      })}`,
    ),
  get: (id: number) => api.get<LeadOut>(`/leads/${id}`),
  addManual: (payload: LeadManualIn) => api.post<LeadOut>('/leads/manual', payload),
  // Looked up by hand (Hunter.io, the company site) -- there is no live lookup integration.
  setContactEmail: (id: number, contactEmail: string) =>
    api.put<LeadOut>(`/leads/${id}/contact-email`, { contact_email: contactEmail }),
  bulkImport: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.postForm<IngestResult>('/leads/bulk-import', form)
  },
}
