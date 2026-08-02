import type { OutreachMessageOut } from '@/api/types'

export function MessageThread({ messages }: { messages: OutreachMessageOut[] }) {
  if (!messages.length) return null

  return (
    <div className="flex flex-col gap-2">
      {messages.map((message) => {
        // Rules the automatic retry could not fix. Worth flagging because these drafts are the ones
        // that need a human edit before they go out -- everything else has already been verified.
        const failures = message.check_failures ?? []

        return (
          <div key={message.id} className={`flex ${message.sender === 'me' ? 'justify-end' : 'justify-start'}`}>
            <div className="flex max-w-[80%] flex-col gap-1">
              <div
                className={`rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                  message.sender === 'me' ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'
                }`}
              >
                {message.body}
              </div>

              {failures.length > 0 && (
                <div className="rounded-md border border-destructive/40 bg-destructive/5 px-2.5 py-1.5 text-xs text-destructive">
                  <p className="font-medium">
                    {failures.length === 1 ? 'This draft breaks a rule' : `This draft breaks ${failures.length} rules`}
                    {' — edit before sending.'}
                  </p>
                  <ul className="mt-1 list-disc space-y-0.5 pl-4">
                    {failures.map((failure, i) => (
                      <li key={i}>{failure.detail}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
