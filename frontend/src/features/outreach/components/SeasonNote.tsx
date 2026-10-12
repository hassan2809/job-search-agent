import { seasonAdvice } from '../constants'

const TONE_STYLE = {
  avoid: 'border-destructive/40 bg-destructive/5 text-destructive',
  quiet: 'border-border bg-muted/40 text-muted-foreground',
  good: 'border-border bg-muted/40 text-foreground',
} as const

// One line, once, on the leads page. Viewer's local month, since that is the only calendar the
// browser has and the advice is about business seasons rather than anything per-lead.
export function SeasonNote() {
  const advice = seasonAdvice(new Date().getMonth())
  if (!advice) return null

  return (
    <p className={`rounded-md border px-3 py-2 text-sm ${TONE_STYLE[advice.tone]}`}>
      {advice.note}
    </p>
  )
}
