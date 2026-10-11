import {
  DAYS_BEFORE_FIRST_MESSAGE,
  MAX_MESSAGE_STAGES,
  MESSAGE_STAGES,
  REPLY_WINDOW_HOURS,
  SEND_WINDOW,
} from './constants'
import type { OutreachDetailOut } from '@/api/types'

export interface Reminder {
  text: string
  urgent: boolean
}

const HOUR_MS = 1000 * 60 * 60
const DAY_MS = HOUR_MS * 24

// created_at comes back from the API as a naive timestamp ("2026-08-01T12:53:00") because the
// column is a plain DateTime (app/models/outreach.py) -- the value is UTC, but the string carries
// no designator, and JS parses that form as *local* time. Left alone, every elapsed-time figure
// here is off by the viewer's UTC offset, which is enough to flip the 24h/48h thresholds below.
function parseServerDate(isoDate: string): Date {
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(isoDate)
  return new Date(hasZone ? isoDate : `${isoDate}Z`)
}

function daysSince(isoDate: string): number {
  return Math.floor((Date.now() - parseServerDate(isoDate).getTime()) / DAY_MS)
}

function hoursSince(isoDate: string): number {
  return Math.floor((Date.now() - parseServerDate(isoDate).getTime()) / HOUR_MS)
}

function isInSendWindow(now: Date): boolean {
  return (
    SEND_WINDOW.days.includes(now.getDay()) &&
    now.getHours() >= SEND_WINDOW.startHour &&
    now.getHours() < SEND_WINDOW.endHour
  )
}

// Next moment the window opens, searching forward a full week so it always lands on a real day.
function nextSendWindowOpen(now: Date): Date | null {
  for (let offset = 0; offset < 8; offset++) {
    const candidate = new Date(now)
    candidate.setDate(now.getDate() + offset)
    if (!SEND_WINDOW.days.includes(candidate.getDay())) continue
    candidate.setHours(SEND_WINDOW.startHour, 0, 0, 0)
    if (candidate.getTime() > now.getTime()) return candidate
  }
  return null
}

function formatWindowOpen(when: Date): string {
  const weekday = when.toLocaleDateString(undefined, { weekday: 'long' })
  const time = when.toLocaleTimeString(undefined, { hour: 'numeric' })
  return `${weekday} at ${time}`
}

// Shown on the two states where you're about to paste a draft into LinkedIn. Only surfaces when
// you're *outside* the window -- inside it, the advice is "carry on", which isn't worth a bullet.
// Never urgent: this is a nudge, and it must not escalate the whole notice to "Action needed".
function sendWindowReminder(): Reminder[] {
  const now = new Date()
  if (isInSendWindow(now)) return []

  const next = nextSendWindowOpen(now)
  const suffix = next ? ` Next good window: ${formatWindowOpen(next)}, your local time.` : ''
  return [
    {
      text: `Sending now is fine, but LinkedIn replies peak Tue-Wed, 9am-4pm.${suffix}`,
      urgent: false,
    },
  ]
}

// How long they've been waiting on a response from me. Their reply is the last message from
// "them" -- not the last message in the thread, since drafting a suggestion appends one from "me".
function replyLatencyReminder(outreach: OutreachDetailOut): Reminder[] {
  const theirLast = [...outreach.messages].reverse().find((m) => m.sender === 'them')
  if (!theirLast) return []

  const elapsed = hoursSince(theirLast.created_at)
  if (elapsed >= REPLY_WINDOW_HOURS.stale) {
    return [
      {
        text: `Over ${REPLY_WINDOW_HOURS.stale} hours since they replied — this is going cold. Send something today, even if it's short.`,
        urgent: true,
      },
    ]
  }
  if (elapsed >= REPLY_WINDOW_HOURS.target) {
    return [
      {
        text: `${elapsed} hours since they replied — responding inside ${REPLY_WINDOW_HOURS.stale} hours is when this is most likely to convert.`,
        urgent: false,
      },
    ]
  }
  return []
}

// Same "what's due" logic as GET /outreach/needs-next-message in app/api/v1/outreach.py, applied
// to a single lead's outreach instead of scanning every awaiting_reply outreach globally.
export function getReminders(outreach: OutreachDetailOut): Reminder[] {
  switch (outreach.status) {
    case 'connection_drafted':
      return [
        { text: 'Connection request drafted — send it on LinkedIn, then mark it sent.', urgent: true },
        ...sendWindowReminder(),
      ]

    case 'connection_sent':
      return [{ text: 'Connection request sent — check LinkedIn and record whether they accepted.', urgent: false }]

    case 'connection_accepted': {
      // They may have replied on accepting. That is a live conversation, so the wait does not
      // apply -- answering is now the urgent thing, not the staged sequence.
      const theySpoke = outreach.messages.some((m) => m.sender === 'them')
      if (theySpoke) {
        return [
          { text: 'They said something when they accepted — reply to that before starting the sequence.', urgent: true },
        ]
      }

      const waited = daysSince(outreach.updated_at)
      const label = MESSAGE_STAGES[0].label
      if (waited >= DAYS_BEFORE_FIRST_MESSAGE) {
        return [
          {
            text: `Accepted ${waited} day${waited === 1 ? '' : 's'} ago — time to send your first message (${label}).`,
            urgent: true,
          },
        ]
      }
      const left = DAYS_BEFORE_FIRST_MESSAGE - waited
      return [
        {
          text: `Accepted ${waited === 0 ? 'today' : `${waited} day${waited === 1 ? '' : 's'} ago`}. Wait ${left} more day${left === 1 ? '' : 's'} before the first message (${label}) — messaging straight after someone accepts reads as automated.`,
          urgent: false,
        },
        {
          text: 'If they said something when they accepted, log it first so the message can respond to it.',
          urgent: false,
        },
      ]
    }

    case 'message_drafted': {
      // Email skips the connection_* states entirely and lands straight here as its opening touch
      // (see POST /outreach/{lead_id}/email), so this can't assume LinkedIn the way it used to.
      const lastMessage = outreach.messages[outreach.messages.length - 1]
      const channel = lastMessage?.channel === 'email' ? 'email' : 'LinkedIn'
      return [
        { text: `Message drafted — send it via ${channel}, then mark it sent.`, urgent: true },
        ...(channel === 'LinkedIn' ? sendWindowReminder() : []),
      ]
    }

    case 'awaiting_reply': {
      if (outreach.message_count >= MAX_MESSAGE_STAGES) {
        return [
          {
            text: `All ${MAX_MESSAGE_STAGES} staged messages sent with no reply — consider closing this as "No response".`,
            urgent: true,
          },
        ]
      }
      const stage = MESSAGE_STAGES[outreach.message_count]
      const lastMessage = outreach.messages[outreach.messages.length - 1]
      if (!lastMessage) return []
      const elapsed = daysSince(lastMessage.created_at)
      if (elapsed >= stage.minDays) {
        return [
          {
            text: `${elapsed} day${elapsed === 1 ? '' : 's'} since your last message — the next follow-up (${stage.label}) is due now.`,
            urgent: true,
          },
        ]
      }
      return [
        {
          text: `Waiting on a reply — next follow-up (${stage.label}) available in ${stage.minDays - elapsed} day(s).`,
          urgent: false,
        },
      ]
    }

    case 'replied': {
      const lastMessage = outreach.messages[outreach.messages.length - 1]
      const channel = lastMessage?.channel === 'email' ? 'email' : 'LinkedIn'
      return [
        {
          text: `They replied — review the suggested response below, send it via ${channel}, then mark it sent.`,
          urgent: true,
        },
        ...replyLatencyReminder(outreach),
        ...(channel === 'LinkedIn' ? sendWindowReminder() : []),
      ]
    }

    default:
      return []
  }
}
