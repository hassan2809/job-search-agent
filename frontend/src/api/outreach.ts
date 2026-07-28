import { api } from './client'
import type { MatchOut, NeedsNextMessageOut, OutreachDetailOut, OutreachOut } from './types'

export const outreachApi = {
  // Both idempotent by default (see app/api/v1/outreach.py) -- pass force to deliberately re-run.
  fitCheck: (leadId: number, force = false) =>
    api.post<MatchOut>(`/outreach/${leadId}/fit-check${force ? '?force=true' : ''}`),
  connect: (leadId: number, force = false) =>
    api.post<OutreachDetailOut>(`/outreach/${leadId}/connect${force ? '?force=true' : ''}`),

  markConnectionSent: (id: number) => api.post<OutreachOut>(`/outreach/${id}/mark-connection-sent`),
  connectionResponse: (id: number, status: 'accepted' | 'declined' | 'no_response') =>
    api.post<OutreachOut>(`/outreach/${id}/connection-response`, { status }),

  nextMessage: (id: number) => api.post<OutreachDetailOut>(`/outreach/${id}/next-message`),
  markSent: (id: number) => api.post<OutreachOut>(`/outreach/${id}/mark-sent`),

  // body: one new message, or a full pasted thread to sync retroactively.
  reply: (id: number, body: string) => api.post<OutreachDetailOut>(`/outreach/${id}/reply`, { body }),

  close: (id: number, status: 'closed_won' | 'closed_declined' | 'closed_no_response') =>
    api.post<OutreachOut>(`/outreach/${id}/close`, { status }),

  needsNextMessage: (minDaysOverride?: number) =>
    api.get<NeedsNextMessageOut[]>(
      `/outreach/needs-next-message${minDaysOverride !== undefined ? `?min_days_override=${minDaysOverride}` : ''}`,
    ),

  get: (id: number) => api.get<OutreachDetailOut>(`/outreach/${id}`),
  getByLead: (leadId: number) => api.get<OutreachDetailOut>(`/outreach/by-lead/${leadId}`),
}
