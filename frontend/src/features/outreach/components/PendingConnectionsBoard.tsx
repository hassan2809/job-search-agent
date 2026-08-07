import { useState } from 'react'
import { useConnectionResponse, usePendingConnections } from '../hooks'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const PAGE = 8

// Recording the answer is the only step of the funnel a human has to supply, and every later
// measurement -- reply rate, which lead types work, whether a hook lands -- is derived from it.
// Batching it here rather than one lead page at a time is what makes it realistic to keep up with.
export function PendingConnectionsBoard() {
  const { data } = usePendingConnections()
  const respond = useConnectionResponse()
  const [showAll, setShowAll] = useState(false)

  if (!data || data.length === 0) return null

  const shown = showAll ? data : data.slice(0, PAGE)

  return (
    <Card size="sm" className="mb-4">
      <CardHeader>
        <CardTitle className="text-sm">
          {data.length} connection request{data.length === 1 ? '' : 's'} with no answer recorded
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">
          Check LinkedIn and record what happened. Until this is filled in there is no way to tell
          which approaches get accepted.
        </p>

        <ul className="flex flex-col divide-y">
          {shown.map((row) => (
            <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 py-1.5">
              <div className="min-w-0">
                <a href={`/leads/${row.lead_id}`} className="text-sm underline underline-offset-4">
                  {row.lead_author || row.lead_title || `Lead ${row.lead_id}`}
                </a>
                <span className="ml-2 text-xs text-muted-foreground">
                  {row.days_waiting} day{row.days_waiting === 1 ? '' : 's'} waiting
                </span>
              </div>
              <div className="flex gap-1">
                <Button
                  size="sm"
                  disabled={respond.isPending}
                  onClick={() => respond.mutate({ id: row.id, status: 'accepted' })}
                >
                  Accepted
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={respond.isPending}
                  onClick={() => respond.mutate({ id: row.id, status: 'declined' })}
                >
                  Declined
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={respond.isPending}
                  onClick={() => respond.mutate({ id: row.id, status: 'no_response' })}
                >
                  No response
                </Button>
              </div>
            </li>
          ))}
        </ul>

        {data.length > PAGE && (
          <button
            type="button"
            className="self-start text-xs text-muted-foreground underline underline-offset-4"
            onClick={() => setShowAll((v) => !v)}
          >
            {showAll ? 'Show fewer' : `Show all ${data.length}`}
          </button>
        )}
        {respond.error && <p className="text-sm text-destructive">{respond.error.message}</p>}
      </CardContent>
    </Card>
  )
}
