// Mirrors MESSAGE_STAGES in app/api/v1/outreach.py exactly -- label + the minimum days that must
// pass after the previous message before this stage is "due".
export const MESSAGE_STAGES = [
  { label: 'Intro & overlap', minDays: 3 },
  { label: 'Show my work', minDays: 5 },
  { label: 'Direct offer', minDays: 6 },
  { label: 'Soft close', minDays: 7 },
] as const

export const MAX_MESSAGE_STAGES = MESSAGE_STAGES.length

// How long to leave a newly accepted connection before the first real message.
// linkedin_outreach_strategies.txt puts the first follow-up 3-5 days after acceptance. Messaging
// the instant someone accepts is the clearest tell of an automated sequence, and it is the one
// moment where waiting costs nothing: they have just seen your name.
// The exception is when they said something on accepting -- that is a live conversation, and
// leaving it three days is rude rather than patient.
export const DAYS_BEFORE_FIRST_MESSAGE = 3

// They answered. c2b_outreach_strategies.txt puts replying inside 24-48 hours at the point a warm
// thread is most likely to convert, so this goes urgent fast.
export const HOURS_BEFORE_REPLY_IS_LATE = 48

export interface SeasonAdvice {
  tone: 'avoid' | 'good' | 'quiet'
  note: string
}

// c2b_outreach_strategies.txt's seasonal windows for freelance pitching. Advisory only, and it is
// the softest guidance in either research file: one source, and plainly written for a US/European
// business calendar. Several of these leads are in MENA, the Nordics and Australia, where the dead
// weeks fall differently. Shown once on the leads page rather than on every draft, because the
// month is the same for every lead and repeating it per message would be pure noise.
const SEASONS: Record<number, SeasonAdvice> = {
  0: { tone: 'avoid', note: 'Early January is still slow. Expect lower response until people are back properly.' },
  1: { tone: 'good', note: 'February to April is project planning season, one of the two best windows.' },
  2: { tone: 'good', note: 'February to April is project planning season, one of the two best windows.' },
  3: { tone: 'good', note: 'February to April is project planning season, one of the two best windows.' },
  5: { tone: 'quiet', note: 'June and July are slower. Good for building relationships rather than pitching.' },
  6: { tone: 'quiet', note: 'June and July are slower. Good for building relationships rather than pitching.' },
  7: { tone: 'avoid', note: 'August is a dead month: vacations and back-to-school. Expect low reply rates.' },
  8: { tone: 'good', note: 'September to November is the year-end push, one of the two best windows.' },
  9: { tone: 'good', note: 'September to November is the year-end push, one of the two best windows.' },
  10: { tone: 'good', note: 'September to November is the year-end push, one of the two best windows.' },
  11: { tone: 'avoid', note: 'December is the worst month to pitch. Worth queueing leads for the new year instead.' },
}

// May says nothing in the source, so it returns nothing rather than inventing a verdict.
export function seasonAdvice(month: number): SeasonAdvice | null {
  return SEASONS[month] ?? null
}

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
