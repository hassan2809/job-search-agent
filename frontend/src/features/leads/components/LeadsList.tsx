import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getLeadSubtitle } from '../utils'
import { useFitCheck } from '@/features/outreach/hooks'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardAction, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
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
  connection_no_response: 'secondary',
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

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading leads...</p>
  if (error) return <p className="text-sm text-destructive">Failed to load leads: {error.message}</p>
  if (!leads?.length) return <p className="text-sm text-muted-foreground">No leads yet — add one to get started.</p>

  return (
    <div className="flex flex-col gap-3">
      {leads.map((lead) => {
        const result = results[lead.id]
        const verdict = result?.fit_verdict ?? lead.latest_verdict
        const isChecking = fitCheck.isPending && fitCheck.variables?.leadId === lead.id
        const subtitle = getLeadSubtitle(lead)

        return (
          <Card key={lead.id} size="sm">
            <CardHeader>
              <CardTitle>
                <Link to={`/leads/${lead.id}`} className="hover:underline">
                  {lead.title || lead.url}
                </Link>
              </CardTitle>
              <CardAction className="flex items-center gap-2">
                <Badge variant="outline">{lead.origin_type}</Badge>
                <Button
                  size="sm"
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
              </CardAction>
            </CardHeader>

            {subtitle && (
              <CardContent>
                <p className="line-clamp-1 text-sm text-muted-foreground">{subtitle}</p>
              </CardContent>
            )}

            {(verdict || lead.latest_outreach_status) && (
              <CardFooter className="flex items-center gap-2">
                {verdict && <Badge variant={VERDICT_VARIANT[verdict]}>{verdict}</Badge>}
                {lead.latest_outreach_status && (
                  <Badge variant={outreachStatusVariant(lead.latest_outreach_status)}>
                    {lead.latest_outreach_status}
                  </Badge>
                )}
                {result && <span className="line-clamp-1 text-sm text-muted-foreground">{result.fit_reasoning}</span>}
              </CardFooter>
            )}
          </Card>
        )
      })}
    </div>
  )
}
