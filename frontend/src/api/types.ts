// Mirrors app/schemas/lead.py and app/schemas/outreach.py.

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
}

export interface LeadManualIn {
  url: string
  raw_content: string
  origin_type?: 'disclosed_need' | 'prospected'
  author?: string
}

export interface IngestResult {
  fetched: number
  inserted: number
  skipped_duplicates: number
}

export interface MatchOut {
  id: number
  lead_id: number
  fit_verdict: 'good_fit' | 'maybe' | 'not_a_fit'
  fit_reasoning: string
  created_at: string
}

export interface OutreachMessageOut {
  id: number
  outreach_id: number
  sender: 'me' | 'them'
  body: string
  created_at: string
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
