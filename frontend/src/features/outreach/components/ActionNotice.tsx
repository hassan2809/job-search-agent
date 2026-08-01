import { getReminders } from '../reminders'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import type { OutreachDetailOut } from '@/api/types'

export function ActionNotice({ outreach }: { outreach: OutreachDetailOut }) {
  const reminders = getReminders(outreach)
  if (!reminders.length) return null

  const hasUrgent = reminders.some((r) => r.urgent)

  return (
    <Alert variant={hasUrgent ? 'destructive' : 'default'}>
      <AlertTitle>{hasUrgent ? 'Action needed' : 'Status'}</AlertTitle>
      <AlertDescription>
        <ul className="list-disc space-y-1 pl-4">
          {reminders.map((reminder, i) => (
            // Advisory reminders sit in the same list as urgent ones, so in a destructive alert
            // they'd inherit the alarm colour and read as things you must act on. Mute them back
            // out -- a declaration on the <li> beats the colour inherited from the description.
            <li key={i} className={reminder.urgent ? undefined : 'text-muted-foreground'}>
              {reminder.text}
            </li>
          ))}
        </ul>
      </AlertDescription>
    </Alert>
  )
}
