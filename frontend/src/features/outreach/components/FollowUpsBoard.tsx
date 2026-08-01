import { Link } from 'react-router-dom'
import { useNeedsNextMessage } from '../hooks'
import { MESSAGE_STAGES } from '../constants'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'

// Surfaces exactly what GET /outreach/needs-next-message computes (see app/api/v1/outreach.py) --
// outreaches sitting in awaiting_reply whose stage's min_days gap has already elapsed -- so you
// don't have to open every lead individually to find out which ones are due for a follow-up.
export function FollowUpsBoard() {
  const { data, isLoading } = useNeedsNextMessage()
  if (isLoading || !data?.length) return null

  return (
    <Alert variant="destructive" className="mb-4">
      <AlertTitle>
        {data.length} lead{data.length === 1 ? '' : 's'} due for a follow-up
      </AlertTitle>
      <AlertDescription>
        <ul className="list-disc space-y-1 pl-4">
          {data.map((item) => {
            const stage = MESSAGE_STAGES[item.message_count]
            return (
              <li key={item.id}>
                <Link to={`/leads/${item.lead_id}`} className="font-medium text-foreground hover:underline">
                  {item.lead_title}
                </Link>
                {' — '}
                {item.days_since_last_message} day{item.days_since_last_message === 1 ? '' : 's'} since your last
                message, send the {stage.label} message now.
              </li>
            )
          })}
        </ul>
      </AlertDescription>
    </Alert>
  )
}
