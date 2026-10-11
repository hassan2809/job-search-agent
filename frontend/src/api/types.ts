// Mirrors app/schemas/lead.py and app/schemas/outreach.py.

// Mirrors ORIGIN_GUIDANCE in app/services/outreach.py. hiring_signal is an indirect-but-real signal
// (a job ad for a manual ops role, funding news, a new Head of Ops/CTO) distinct from disclosed_need
// (they personally said "I need a developer").
export type OriginType = 'disclosed_need' | 'hiring_signal' | 'prospected'

export type FitVerdict = 'good_fit' | 'maybe' | 'not_a_fit'
export type FitStatusFilter = FitVerdict | 'not_checked'

// Mirrors CLOSE_STATUSES in app/api/v1/outreach.py. closed_seen_no_reply and closed_not_seen are
// the read-receipt split of closed_no_response, chosen at close time rather than tracked per message.
export type CloseStatus =
  | 'closed_won'
  | 'closed_declined'
  | 'closed_no_response'
  | 'closed_seen_no_reply'
  | 'closed_not_seen'
  | 'closed_not_interested'

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
  | 'closed_seen_no_reply'
  | 'closed_not_seen'
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
  origin_type: OriginType
  posted_at: string | null
  fetched_at: string
  latest_verdict: FitVerdict | null
  latest_outreach_status: Exclude<OutreachStatusFilter, 'not_started'> | null
}

export interface LeadManualIn {
  url: string
  raw_content?: string
  origin_type?: OriginType
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
  // Which channel this specific message went out on. A lead can get both over time, so this lives
  // on the message, not the outreach. Defaults to 'linkedin' for everything sent before email
  // existed as a channel.
  channel: 'linkedin' | 'email'
  created_at: string
  // Rules this draft STILL breaks after the automatic retry. Empty for clean drafts, for messages
  // they sent, and for anything drafted before checks existed.
  check_failures: CheckFailure[]
}

// opening = first email, value_add = day-4 follow-up, clear_ask = day-10 follow-up. Mirrors
// FOLLOW_UP_GUIDANCE in app/services/outreach.py.
export type EmailFollowUpStage = 'opening' | 'value_add' | 'clear_ask'

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
  origin_type: OriginType
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

// Mirrors app/services/episodes.py's Episode dataclass / app/schemas/outreach.py's EpisodeOut.
// One reconstructed past (or in-flight) outreach -- nothing here is stored, it's derived on read.
export type EpisodeOutcome =
  | 'won'
  | 'replied'
  | 'declined'
  | 'accepted_no_reply'
  | 'seen_no_reply'
  | 'not_seen'
  | 'connection_declined'
  | 'connection_ignored'
  | 'dropped'
  | 'open'

export interface EpisodeOut {
  outreach_id: number
  lead_id: number
  lead_author: string
  lead_type: string | null
  fit_verdict: FitVerdict | null
  origin_type: OriginType
  status: string
  outcome: EpisodeOutcome
  connection_accepted: boolean | null
  stages_sent: number
  got_reply: boolean
  days_to_first_reply: number | null
  hook: string
  projects_mentioned: string[]
  unresolved_failures: number
}

export interface EpisodesOut {
  // Mirrors app/services/episodes.py's summarise(): counts a human can read without re-deriving.
  summary: {
    total: number
    with_known_outcome: number
    open: number
    dropped_by_me: number
    replied: number
    by_lead_type: Record<string, { episodes: number; replied: number }>
    by_outcome: Record<string, number>
  }
  episodes: EpisodeOut[]
}

export interface ReflectionOut {
  id: number
  episode_count: number
  guidance: string
  created_at: string
}
