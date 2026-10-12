import { Link } from 'react-router-dom'
import { useCheckStats, useEpisodes, useGenerateReflection, useReflection } from '@/features/outreach/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { EpisodeOutcome } from '@/api/types'

// Human labels for the outcome buckets app/services/episodes.py computes. seen_no_reply and
// not_seen are the read-receipt split of what used to be one undifferentiated "no reply" bucket --
// they are why this page exists.
const OUTCOME_LABELS: Record<EpisodeOutcome, string> = {
  won: 'Won',
  replied: 'Replied',
  declined: 'Declined (said no)',
  accepted_no_reply: 'No reply, seen status unchecked',
  seen_no_reply: 'Seen, no reply',
  not_seen: 'Never seen',
  connection_declined: 'Connection declined',
  connection_ignored: 'Connection request ignored',
  dropped: 'Dropped (my call)',
  open: 'Still in flight',
}

const OUTCOME_VARIANT: Record<EpisodeOutcome, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  won: 'default',
  replied: 'default',
  declined: 'secondary',
  accepted_no_reply: 'outline',
  seen_no_reply: 'destructive',
  not_seen: 'outline',
  connection_declined: 'secondary',
  connection_ignored: 'outline',
  dropped: 'secondary',
  open: 'outline',
}

// Ordered so the funnel reads top to bottom: worked, engaged-but-no, never landed, unresolved.
const OUTCOME_ORDER: EpisodeOutcome[] = [
  'won',
  'replied',
  'declined',
  'seen_no_reply',
  'not_seen',
  'accepted_no_reply',
  'connection_declined',
  'connection_ignored',
  'dropped',
  'open',
]

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-2xl font-semibold tabular-nums">{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  )
}

function OutcomeBar({ outcome, count, max }: { outcome: EpisodeOutcome; count: number; max: number }) {
  const pct = max > 0 ? Math.round((count / max) * 100) : 0
  return (
    <div className="flex items-center gap-2">
      <Badge variant={OUTCOME_VARIANT[outcome]} className="w-52 shrink-0 justify-start whitespace-normal text-left">
        {OUTCOME_LABELS[outcome] ?? outcome}
      </Badge>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
      </div>
      <span className="w-6 shrink-0 text-right text-xs tabular-nums text-muted-foreground">{count}</span>
    </div>
  )
}

export function EfficiencyPage() {
  const { data, isLoading, error } = useEpisodes()
  const { data: reflection } = useReflection()
  const generateReflection = useGenerateReflection()
  const { data: checkStats } = useCheckStats()

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-foreground">Efficiency</h1>
        <p className="text-sm text-muted-foreground">
          What past outreach actually taught -- reconstructed from outcomes, nothing stored twice.
        </p>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Loading...</p>}
      {error && <p className="text-sm text-destructive">{error.message}</p>}

      {data && (
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Overview</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-6">
              <Stat label="Total outreaches" value={data.summary.total} />
              <Stat label="With a known outcome" value={data.summary.with_known_outcome} />
              <Stat label="Replied" value={data.summary.replied} />
              <Stat label="Still open" value={data.summary.open} />
              <Stat label="Dropped (my call)" value={data.summary.dropped_by_me} />
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Outcome funnel</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-2">
                {data.summary.total === 0 ? (
                  <p className="text-sm text-muted-foreground">No outreach recorded yet.</p>
                ) : (
                  <>
                    {OUTCOME_ORDER.filter((o) => data.summary.by_outcome[o] > 0).map((outcome) => (
                      <OutcomeBar
                        key={outcome}
                        outcome={outcome}
                        count={data.summary.by_outcome[outcome] ?? 0}
                        max={data.summary.total}
                      />
                    ))}
                    <p className="mt-2 text-xs text-muted-foreground">
                      "Seen, no reply" and "Never seen" only split out from the generic "no reply"
                      bucket when you close a thread using one of those two Close out options instead
                      of the plain "No response" one.
                    </p>
                  </>
                )}
              </CardContent>
            </Card>

            {Object.keys(data.summary.by_lead_type).length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Reply rate by lead type</CardTitle>
                </CardHeader>
                <CardContent>
                  <table className="w-full text-sm">
                    <thead className="text-muted-foreground">
                      <tr>
                        <th className="text-left font-normal">Type</th>
                        <th className="w-20 text-right font-normal">Episodes</th>
                        <th className="w-20 text-right font-normal">Replied</th>
                        <th className="w-24 text-right font-normal">Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(data.summary.by_lead_type)
                        .sort(([, a], [, b]) => b.episodes - a.episodes)
                        .map(([type, row]) => (
                          <tr key={type}>
                            <td className="py-0.5">{type}</td>
                            <td className="text-right tabular-nums">{row.episodes}</td>
                            <td className="text-right tabular-nums">{row.replied}</td>
                            <td className="text-right tabular-nums text-muted-foreground">
                              {row.episodes > 0 ? Math.round((row.replied / row.episodes) * 100) : 0}%
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Learned guidance</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {reflection ? (
                  <>
                    <p className="text-xs text-muted-foreground">
                      Distilled from {reflection.episode_count} closed episodes on{' '}
                      {new Date(reflection.created_at).toLocaleDateString()}. Injected into every new draft.
                    </p>
                    <p className="whitespace-pre-wrap text-sm">{reflection.guidance}</p>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No reflection generated yet. Needs at least 30 outreaches with a known outcome so it
                    isn't learning from noise.
                  </p>
                )}
                <div>
                  <Button size="sm" variant="outline" disabled={generateReflection.isPending} onClick={() => generateReflection.mutate()}>
                    {generateReflection.isPending ? 'Generating...' : 'Regenerate from current data'}
                  </Button>
                  {generateReflection.error && (
                    <p className="mt-1 text-xs text-destructive">{generateReflection.error.message}</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {checkStats && checkStats.drafts > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Draft quality</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {checkStats.drafts} drafts checked.{' '}
                    {Math.round((checkStats.clean_first_time / checkStats.drafts) * 100)}% clean first time.{' '}
                    {checkStats.still_broken} still need editing before sending.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Recent episodes</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {data.episodes.length === 0 && (
                <p className="text-sm text-muted-foreground">Nothing sent yet.</p>
              )}
              {[...data.episodes]
                .reverse()
                .slice(0, 25)
                .map((episode) => (
                  <div key={episode.outreach_id} className="flex flex-col gap-1 border-b pb-2 last:border-b-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        to={`/leads/${episode.lead_id}`}
                        className="text-sm font-medium text-foreground hover:underline"
                      >
                        {episode.lead_author || `Lead #${episode.lead_id}`}
                      </Link>
                      <Badge variant={OUTCOME_VARIANT[episode.outcome]}>
                        {OUTCOME_LABELS[episode.outcome] ?? episode.outcome}
                      </Badge>
                      {episode.lead_type && <span className="text-xs text-muted-foreground">{episode.lead_type}</span>}
                      <span className="text-xs text-muted-foreground">
                        {episode.stages_sent} message{episode.stages_sent === 1 ? '' : 's'} sent
                      </span>
                    </div>
                    {episode.hook && (
                      <p className="text-xs text-muted-foreground">Opened: "{episode.hook}"</p>
                    )}
                  </div>
                ))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
