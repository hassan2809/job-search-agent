import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getLeadSubtitle } from '../utils'
import { useFitCheck } from '@/features/outreach/hooks'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { LeadOut, MatchOut } from '@/api/types'

const VERDICT_VARIANT: Record<MatchOut['fit_verdict'], 'default' | 'secondary' | 'destructive'> = {
  good_fit: 'default',
  maybe: 'secondary',
  not_a_fit: 'destructive',
}

type BadgeVariant = 'default' | 'secondary' | 'destructive' | 'outline'
const OUTREACH_STATUS_VARIANT: Record<string, BadgeVariant> = {
  closed_won: 'default',
  closed_declined: 'destructive',
  connection_declined: 'destructive',
  closed_no_response: 'secondary',
  closed_seen_no_reply: 'secondary',
  closed_not_seen: 'secondary',
  connection_no_response: 'secondary',
  closed_not_interested: 'secondary',
}
const outreachStatusVariant = (status: string): BadgeVariant => OUTREACH_STATUS_VARIANT[status] ?? 'outline'

interface LeadsListProps {
  leads: LeadOut[] | undefined
  isLoading: boolean
  error: Error | null
}

export function LeadsList({ leads, isLoading, error }: LeadsListProps) {
  const fitCheck = useFitCheck()
  const [results, setResults] = useState<Record<number, MatchOut>>({})

  if (isLoading) {
    return (
      <div className="rounded-xl border bg-background p-8 text-center text-sm text-muted-foreground">
        Loading leads...
      </div>
    )
  }
  if (error) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-8 text-center text-sm text-destructive">
        Failed to load leads: {error.message}
      </div>
    )
  }
  if (!leads?.length) {
    return (
      <div className="rounded-xl border bg-background p-8 text-center text-sm text-muted-foreground">
        No leads match these filters.
      </div>
    )
  }

  return (
    <ul className="flex flex-col divide-y rounded-xl border bg-background">
      {leads.map((lead) => {
        const result = results[lead.id]
        const verdict = result?.fit_verdict ?? lead.latest_verdict
        const isChecking = fitCheck.isPending && fitCheck.variables?.leadId === lead.id
        const subtitle = result?.fit_reasoning ?? getLeadSubtitle(lead)

        return (
          <li key={lead.id} className="flex flex-wrap items-center gap-3 px-4 py-3 transition-colors hover:bg-muted/40">
            <div className="min-w-0 flex-1 basis-60">
              <Link to={`/leads/${lead.id}`} className="block truncate font-medium text-foreground hover:underline">
                {lead.title || lead.url}
              </Link>
              {subtitle && <p className="line-clamp-1 text-sm text-muted-foreground">{subtitle}</p>}
            </div>

            <div className="flex flex-shrink-0 items-center gap-1.5">
              <Badge variant="outline">{lead.origin_type}</Badge>
              {verdict && <Badge variant={VERDICT_VARIANT[verdict]}>{verdict}</Badge>}
              {lead.latest_outreach_status && (
                <Badge variant={outreachStatusVariant(lead.latest_outreach_status)}>
                  {lead.latest_outreach_status}
                </Badge>
              )}
            </div>

            <Button
              size="sm"
              variant="outline"
              disabled={isChecking}
              onClick={() =>
                fitCheck.mutate(
                  { leadId: lead.id },
                  { onSuccess: (match) => setResults((prev) => ({ ...prev, [lead.id]: match })) },
                )
              }
            >
              {isChecking ? 'Checking...' : 'Run fit-check'}
            </Button>
          </li>
        )
      })}
    </ul>
  )
}
