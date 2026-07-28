import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useLead } from '../hooks'
import { parseLeadProfile } from '../utils'
import { useFitCheck } from '@/features/outreach/hooks'
import { OutreachPanel } from '@/features/outreach/components/OutreachPanel'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { MatchOut } from '@/api/types'

const VERDICT_VARIANT: Record<MatchOut['fit_verdict'], 'default' | 'secondary' | 'destructive'> = {
  good_fit: 'default',
  maybe: 'secondary',
  not_a_fit: 'destructive',
}

export function LeadDetailPage() {
  const { id } = useParams<{ id: string }>()
  const leadId = Number(id)
  const { data: lead, isLoading, error } = useLead(leadId)
  const fitCheck = useFitCheck()
  const [result, setResult] = useState<MatchOut | null>(null)

  return (
    <div className="min-h-svh bg-muted/30">
      <header className="border-b bg-background">
        <div className="mx-auto max-w-2xl px-6 py-4">
          <Link to="/" className="text-sm text-muted-foreground hover:text-foreground">
            ← Back to leads
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-6">
        {isLoading && <p className="text-sm text-muted-foreground">Loading...</p>}
        {error && <p className="text-sm text-destructive">Failed to load lead: {error.message}</p>}

        {lead && (
          <div className="flex flex-col gap-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl font-semibold text-foreground">{lead.title}</h1>
                <a
                  href={lead.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-muted-foreground hover:text-foreground hover:underline"
                >
                  {lead.url}
                </a>
              </div>
              <Badge variant="outline">{lead.origin_type}</Badge>
            </div>

            <Card size="sm">
              <CardContent className="flex items-center gap-3">
                <Button
                  size="sm"
                  disabled={fitCheck.isPending}
                  onClick={() =>
                    fitCheck.mutate({ leadId: lead.id }, { onSuccess: (match) => setResult(match) })
                  }
                >
                  {fitCheck.isPending ? 'Checking...' : 'Run fit-check'}
                </Button>
                {result && <Badge variant={VERDICT_VARIANT[result.fit_verdict]}>{result.fit_verdict}</Badge>}
              </CardContent>
              {result && (
                <CardContent>
                  <p className="text-sm text-muted-foreground">{result.fit_reasoning}</p>
                </CardContent>
              )}
            </Card>

            <Card size="sm">
              <CardHeader>
                <CardTitle className="text-base">Outreach</CardTitle>
              </CardHeader>
              <CardContent>
                <OutreachPanel leadId={lead.id} fitVerdict={result?.fit_verdict ?? lead.latest_verdict} />
              </CardContent>
            </Card>

            <LeadProfileView description={lead.description} />
          </div>
        )}
      </main>
    </div>
  )
}

function LeadProfileView({ description }: { description: string }) {
  const profile = parseLeadProfile(description)

  return (
    <div className="flex flex-col gap-4">
      {(profile.headline || profile.location || profile.meta.length > 0) && (
        <Card size="sm">
          <CardContent className="flex flex-col gap-1">
            {profile.headline && <p className="font-medium text-foreground">{profile.headline}</p>}
            {profile.location && <p className="text-sm text-muted-foreground">{profile.location}</p>}
            {profile.meta.length > 0 && (
              <p className="text-sm text-muted-foreground">{profile.meta.join(' · ')}</p>
            )}
          </CardContent>
        </Card>
      )}

      {profile.sections.map((section) => (
        <Card key={section.label}>
          <CardHeader>
            <CardTitle>{section.label}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {section.paragraphs.map((paragraph, i) => (
              <p key={i} className="text-sm whitespace-pre-line text-foreground">
                {paragraph}
              </p>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
