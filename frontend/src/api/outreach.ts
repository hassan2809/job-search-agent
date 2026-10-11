import { api } from './client'
import type {
  CheckStatsOut,
  CloseStatus,
  EmailFollowUpStage,
  EpisodesOut,
  MatchOut,
  NeedsNextMessageOut,
  PendingConnectionOut,
  OutreachDetailOut,
  OutreachOut,
  ReflectionOut,
} from './types'

export const outreachApi = {
  // Both idempotent by default (see app/api/v1/outreach.py) -- pass force to deliberately re-run.
  fitCheck: (leadId: number, force = false) =>
    api.post<MatchOut>(`/outreach/${leadId}/fit-check${force ? '?force=true' : ''}`),
  connect: (leadId: number, force = false) =>
    api.post<OutreachDetailOut>(`/outreach/${leadId}/connect${force ? '?force=true' : ''}`),
  // No LLM-drafted note -- for when LinkedIn Premium's note limit is the bottleneck. Goes straight
  // to connection_sent since there is no draft to review first.
  connectWithoutNote: (leadId: number) =>
    api.post<OutreachDetailOut>(`/outreach/${leadId}/connect-without-note`),
  // Marks the lead as not worth pursuing at any point -- even before fit-check/connect happen.
  pass: (leadId: number) => api.post<OutreachOut>(`/outreach/${leadId}/pass`),

  // Drafts a cold email: the opening touch, or a day-4/day-10 follow-up. Not idempotent -- every
  // call drafts a fresh one, since sending more than one email to the same lead is the point.
  // Requires the lead to already have a contact_email saved.
  draftEmail: (leadId: number, followUpStage: EmailFollowUpStage = 'opening') =>
    api.post<OutreachDetailOut>(`/outreach/${leadId}/email`, { follow_up_stage: followUpStage }),

  markConnectionSent: (id: number) => api.post<OutreachOut>(`/outreach/${id}/mark-connection-sent`),
  connectionResponse: (id: number, status: 'accepted' | 'declined' | 'no_response') =>
    api.post<OutreachOut>(`/outreach/${id}/connection-response`, { status }),

  nextMessage: (id: number) => api.post<OutreachDetailOut>(`/outreach/${id}/next-message`),
  markSent: (id: number) => api.post<OutreachOut>(`/outreach/${id}/mark-sent`),

  // body: one new message, or a full pasted thread to sync retroactively. channel tags which
  // channel they replied on, so the suggested response goes out the same way.
  reply: (id: number, body: string, channel: 'linkedin' | 'email' = 'linkedin') =>
    api.post<OutreachDetailOut>(`/outreach/${id}/reply`, { body, channel }),
  // Records that the suggested response was actually sent -- returns the thread to awaiting_reply.
  markReplySent: (id: number) => api.post<OutreachOut>(`/outreach/${id}/mark-reply-sent`),

  // Rewrites one drafted message in place, following a free-text instruction.
  revise: (id: number, messageId: number, instruction: string) =>
    api.post<OutreachDetailOut>(`/outreach/${id}/messages/${messageId}/revise`, { instruction }),

  close: (id: number, status: CloseStatus) => api.post<OutreachOut>(`/outreach/${id}/close`, { status }),

  needsNextMessage: (minDaysOverride?: number) =>
    api.get<NeedsNextMessageOut[]>(
      `/outreach/needs-next-message${minDaysOverride !== undefined ? `?min_days_override=${minDaysOverride}` : ''}`,
    ),

  // Connection requests sent but never resolved -- the hole in the funnel.
  pendingConnections: () => api.get<PendingConnectionOut[]>('/outreach/pending-connections'),

  // How often the deterministic draft checks fire, and whether the automatic retry fixes them.
  checkStats: () => api.get<CheckStatsOut>('/outreach/check-stats'),

  // Every past outreach reconstructed as an episode, plus counts. Derived on read, nothing stored.
  episodes: () => api.get<EpisodesOut>('/outreach/episodes'),
  // Distills every closed episode into standing guidance, and stores it. 409s below the minimum
  // episode count -- the caller should surface that detail message rather than retry.
  generateReflection: () => api.post<ReflectionOut>('/outreach/reflections/generate'),
  latestReflection: () => api.get<ReflectionOut | null>('/outreach/reflections'),

  get: (id: number) => api.get<OutreachDetailOut>(`/outreach/${id}`),
  getByLead: (leadId: number) => api.get<OutreachDetailOut>(`/outreach/by-lead/${leadId}`),
}
