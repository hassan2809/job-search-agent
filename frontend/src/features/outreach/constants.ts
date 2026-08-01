// Mirrors MESSAGE_STAGES in app/api/v1/outreach.py exactly -- label + the minimum days that must
// pass after the previous message before this stage is "due".
export const MESSAGE_STAGES = [
  { label: 'Intro & overlap', minDays: 3 },
  { label: 'Show my work', minDays: 5 },
  { label: 'Direct ask', minDays: 6 },
  { label: 'Soft close', minDays: 7 },
] as const

export const MAX_MESSAGE_STAGES = MESSAGE_STAGES.length

// From linkedin_outreach_strategies.txt's "How to increase response rate on LinkedIn" table:
// sending Tue-Wed between 9am and 4pm lifts engagement ~10%. Purely advisory -- it nudges when
// you paste a draft into LinkedIn, it never gates an action.
//
// This is evaluated against the *viewer's* local clock, because that's the only clock the browser
// has. The strategy really means the recipient's working hours, so the hint is only as good as the
// assumption that the lead keeps roughly the same hours you do -- treat it as a nudge, not a rule.
export const SEND_WINDOW: {
  days: readonly number[] // Date#getDay(): 2 = Tuesday, 3 = Wednesday
  startHour: number
  endHour: number // exclusive
} = {
  days: [2, 3],
  startHour: 9,
  endHour: 16,
}

// Same table: replying within 24-48 hours lifts conversions ~25%. `target` is when to start
// nudging, `stale` is when the thread is going cold.
export const REPLY_WINDOW_HOURS = { target: 24, stale: 48 } as const
