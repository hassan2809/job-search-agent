import { useState } from 'react'
import { useReviseMessage } from '../hooks'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { OutreachMessageOut } from '@/api/types'

// Common edits, so the frequent cases are one click instead of typing the same sentence again.
const QUICK_INSTRUCTIONS = ['Make it shorter', 'Less formal', 'Drop the last line']

function ReviseBox({
  outreachId,
  message,
  onDone,
}: {
  outreachId: number
  message: OutreachMessageOut
  onDone: () => void
}) {
  const [instruction, setInstruction] = useState('')
  const revise = useReviseMessage()

  function submit(text: string) {
    if (!text.trim()) return
    revise.mutate(
      { id: outreachId, messageId: message.id, instruction: text },
      { onSuccess: onDone },
    )
  }

  return (
    <div className="flex flex-col gap-1.5 rounded-md border bg-card p-2">
      <Textarea
        rows={2}
        autoFocus
        placeholder="What should change? e.g. drop the portfolio link, mention Guard XP instead, make it warmer"
        value={instruction}
        onChange={(e) => setInstruction(e.target.value)}
        disabled={revise.isPending}
      />
      <div className="flex flex-wrap gap-1">
        {QUICK_INSTRUCTIONS.map((quick) => (
          <button
            key={quick}
            type="button"
            className="rounded border px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted"
            disabled={revise.isPending}
            onClick={() => setInstruction(quick)}
          >
            {quick}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2">
        <Button size="sm" disabled={revise.isPending || !instruction.trim()} onClick={() => submit(instruction)}>
          {revise.isPending ? 'Revising...' : 'Revise'}
        </Button>
        <Button size="sm" variant="ghost" disabled={revise.isPending} onClick={onDone}>
          Cancel
        </Button>
      </div>
      {revise.error && <p className="text-xs text-destructive">{revise.error.message}</p>}
    </div>
  )
}

export function MessageThread({ messages, outreachId }: { messages: OutreachMessageOut[]; outreachId: number }) {
  const [revising, setRevising] = useState<number | null>(null)

  if (!messages.length) return null

  return (
    <div className="flex flex-col gap-2">
      {messages.map((message) => {
        // Rules the automatic retry could not fix. Worth flagging because these drafts are the ones
        // that need a human edit before they go out -- everything else has already been verified.
        const failures = message.check_failures ?? []
        const isMine = message.sender === 'me'

        return (
          <div key={message.id} className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}>
            <div className="flex max-w-[80%] flex-col gap-1">
              <div
                className={`rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                  isMine ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'
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

              {/* Only my own drafts can be revised -- their replies are a record of what they said. */}
              {isMine &&
                (revising === message.id ? (
                  <ReviseBox outreachId={outreachId} message={message} onDone={() => setRevising(null)} />
                ) : (
                  <button
                    type="button"
                    className="self-end text-xs text-muted-foreground underline underline-offset-4 hover:text-foreground"
                    onClick={() => setRevising(message.id)}
                  >
                    Revise
                  </button>
                ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
