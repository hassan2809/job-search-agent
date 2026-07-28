import type { OutreachMessageOut } from '@/api/types'

export function MessageThread({ messages }: { messages: OutreachMessageOut[] }) {
  if (!messages.length) return null

  return (
    <div className="flex flex-col gap-2">
      {messages.map((message) => (
        <div key={message.id} className={`flex ${message.sender === 'me' ? 'justify-end' : 'justify-start'}`}>
          <div
            className={`max-w-[80%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
              message.sender === 'me' ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'
            }`}
          >
            {message.body}
          </div>
        </div>
      ))}
    </div>
  )
}
