// Mirrors app/schemas/lead.py and app/schemas/outreach.py.

export type FitVerdict = 'good_fit' | 'maybe' | 'not_a_fit'
export type FitStatusFilter = FitVerdict | 'not_checked'

// Mirrors CLOSE_STATUSES in app/api/v1/outreach.py.
export type CloseStatus = 'closed_won' | 'closed_declined' | 'closed_no_response' | 'closed_not_interested'

// Mirrors OUTREACH_STATUSES in app/api/v1/leads.py (Outreach.status values plus "not_started").
export type OutreachStatusFilter =
  | 'not_started'
  | 'connection_drafted'
  | 'connection_sent'
  | 'connection_accepted'
  | 'connection_declined'
  | 'connection_no_response'
  | 'message_drafted'
  | 'awaiting_reply'
  | 'replied'
  | 'closed_won'
  | 'closed_declined'
  | 'closed_no_response'
  | 'closed_not_interested'

export interface LeadOut {
  id: number
  source: string
  external_id: string
  title: string
  description: string
  url: string
  author: string
  contact_email: string | null
  is_manual: boolean
  origin_type: 'disclosed_need' | 'prospected'
  posted_at: string | null
  fetched_at: string
  latest_verdict: FitVerdict | null
  latest_outreach_status: Exclude<OutreachStatusFilter, 'not_started'> | null
}

export interface LeadManualIn {
  url: string
  raw_content?: string
  origin_type?: 'disclosed_need' | 'prospected'
  author?: string
}

export interface IngestResult {
  fetched: number
  inserted: number
  skipped_duplicates: number
}

export interface LeadListOut {
  items: LeadOut[]
  total: number
}

export interface MatchOut {
  id: number
  lead_id: number
  fit_verdict: FitVerdict
  lead_type: string | null
  fit_reasoning: string
  created_at: string
}

// One deterministic rule a draft broke. `code` is stable and aggregatable (see check-stats);
// `detail` is the sentence written for a human. Mirrors app/services/message_checks.py.
export interface CheckFailure {
  code: string
  detail: string
}

export interface OutreachMessageOut {
  id: number
  outreach_id: number
  sender: 'me' | 'them'
  body: string
  created_at: string
  // Rules this draft STILL breaks after the automatic retry. Empty for clean drafts, for messages
  // they sent, and for anything drafted before checks existed.
  check_failures: CheckFailure[]
}

export interface PendingConnectionOut {
  id: number
  lead_id: number
  lead_author: string
  lead_title: string
  days_waiting: number
}

export interface CheckStatRow {
  code: string
  first_attempt: number
  unresolved: number
}

export interface CheckStatsOut {
  drafts: number
  clean_first_time: number
  retried: number
  retry_fixed_all: number
  still_broken: number
  by_rule: CheckStatRow[]
}

export interface OutreachOut {
  id: number
  lead_id: number
  match_id: number | null
  origin_type: 'disclosed_need' | 'prospected'
  status: string
  message_count: number
  created_at: string
  updated_at: string
}

export interface OutreachDetailOut extends OutreachOut {
  messages: OutreachMessageOut[]
}

export interface NeedsNextMessageOut extends OutreachOut {
  lead_title: string
  days_since_last_message: number
}
