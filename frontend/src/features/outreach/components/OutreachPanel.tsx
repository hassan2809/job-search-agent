import { useState } from 'react'
import { MessageThread } from './MessageThread'
import { ActionNotice } from './ActionNotice'
import {
  useCloseOutreach,
  useConnect,
  useConnectionResponse,
  useMarkConnectionSent,
  useMarkReplySent,
  useMarkSent,
  useNextMessage,
  useOutreachByLead,
  usePassOnLead,
  useReply,
} from '../hooks'
import { MAX_MESSAGE_STAGES, MESSAGE_STAGES } from '../constants'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { FitVerdict } from '@/api/types'

function ErrorText({ error }: { error: Error | null }) {
  if (!error) return null
  return <p className="text-sm text-destructive">{error.message}</p>
}

export function OutreachPanel({ leadId, fitVerdict }: { leadId: number; fitVerdict: FitVerdict | null }) {
  const { data: outreach, isLoading } = useOutreachByLead(leadId)
  const connect = useConnect()
  const markConnectionSent = useMarkConnectionSent()
  const connectionResponse = useConnectionResponse()
  const nextMessage = useNextMessage()
  const markSent = useMarkSent()
  const markReplySent = useMarkReplySent()
  const reply = useReply()
  const closeOutreach = useCloseOutreach()
  const passOnLead = usePassOnLead()
  const [replyBody, setReplyBody] = useState('')

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading outreach status...</p>

  if (!outreach) {
    const canConnect = fitVerdict && fitVerdict !== 'not_a_fit'
    return (
      <div className="flex flex-col gap-2">
        {!fitVerdict && <p className="text-sm text-muted-foreground">Run a fit-check first to unlock outreach.</p>}
        {fitVerdict === 'not_a_fit' && (
          <p className="text-sm text-muted-foreground">Fit-check came back "not a fit" — no connection request.</p>
        )}
        <div className="flex gap-2">
          {canConnect && (
            <Button size="sm" disabled={connect.isPending} onClick={() => connect.mutate({ leadId })}>
              {connect.isPending ? 'Drafting...' : 'Send connection request'}
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            disabled={passOnLead.isPending}
            onClick={() => passOnLead.mutate(leadId)}
          >
            {passOnLead.isPending ? 'Saving...' : 'Not interested (my call)'}
          </Button>
        </div>
        <ErrorText error={connect.error ?? passOnLead.error} />
      </div>
    )
  }

  const closedStatuses = [
    'connection_declined',
    'connection_no_response',
    'closed_won',
    'closed_declined',
    'closed_no_response',
    'closed_seen_no_reply',
    'closed_not_seen',
    'closed_not_interested',
  ]
  if (closedStatuses.includes(outreach.status)) {
    return (
      <div className="flex flex-col gap-3">
        <Badge variant="secondary">{outreach.status}</Badge>
        <MessageThread messages={outreach.messages} outreachId={outreach.id} />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Badge variant="outline">{outreach.status}</Badge>
        {outreach.message_count > 0 && (
          <span className="text-sm text-muted-foreground">
            {outreach.message_count}/{MAX_MESSAGE_STAGES} staged messages sent
          </span>
        )}
      </div>

      <ActionNotice outreach={outreach} />

      <MessageThread messages={outreach.messages} outreachId={outreach.id} />

      {outreach.status === 'connection_drafted' && (
        <div className="flex flex-col gap-2">
          <Button size="sm" disabled={markConnectionSent.isPending} onClick={() => markConnectionSent.mutate(outreach.id)}>
            {markConnectionSent.isPending ? 'Saving...' : 'Mark connection request sent'}
          </Button>
          <ErrorText error={markConnectionSent.error} />
        </div>
      )}

      {outreach.status === 'connection_sent' && (
        <div className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground">Did they accept the connection request?</p>
          <div className="flex gap-2">
            <Button
              size="sm"
              disabled={connectionResponse.isPending}
              onClick={() => connectionResponse.mutate({ id: outreach.id, status: 'accepted' })}
            >
              Accepted
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={connectionResponse.isPending}
              onClick={() => connectionResponse.mutate({ id: outreach.id, status: 'declined' })}
            >
              Declined
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={connectionResponse.isPending}
              onClick={() => connectionResponse.mutate({ id: outreach.id, status: 'no_response' })}
            >
              No response
            </Button>
          </div>
          <ErrorText error={connectionResponse.error} />
        </div>
      )}

      {/* Also offered from 'replied' -- a reply pauses the staged sequence, it doesn't end it. */}
      {(outreach.status === 'connection_accepted' ||
        outreach.status === 'awaiting_reply' ||
        outreach.status === 'replied') &&
        outreach.message_count < MAX_MESSAGE_STAGES && (
          <div className="flex flex-col gap-2">
            <Button size="sm" disabled={nextMessage.isPending} onClick={() => nextMessage.mutate(outreach.id)}>
              {nextMessage.isPending
                ? 'Drafting...'
                : `Draft next message (${MESSAGE_STAGES[outreach.message_count].label})`}
            </Button>
            <ErrorText error={nextMessage.error} />
          </div>
        )}

      {outreach.status === 'message_drafted' && (
        <div className="flex flex-col gap-2">
          <Button size="sm" disabled={markSent.isPending} onClick={() => markSent.mutate(outreach.id)}>
            {markSent.isPending ? 'Saving...' : 'Mark message sent'}
          </Button>
          <ErrorText error={markSent.error} />
        </div>
      )}

      {outreach.status === 'replied' && (
        <div className="flex flex-col gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={markReplySent.isPending}
            onClick={() => markReplySent.mutate(outreach.id)}
          >
            {markReplySent.isPending ? 'Saving...' : 'Mark suggested reply sent'}
          </Button>
          <ErrorText error={markReplySent.error} />
        </div>
      )}

      {/* Also offered from 'connection_accepted' -- people often send a note when they accept. */}
      {(outreach.status === 'connection_accepted' ||
        outreach.status === 'awaiting_reply' ||
        outreach.status === 'replied') && (
        <Card size="sm">
          <CardHeader>
            <CardTitle className="text-sm">Log their reply</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <Textarea
              placeholder="Paste what they said..."
              rows={3}
              value={replyBody}
              onChange={(e) => setReplyBody(e.target.value)}
            />
            <Button
              size="sm"
              disabled={reply.isPending || !replyBody.trim()}
              onClick={() =>
                reply.mutate(
                  { id: outreach.id, body: replyBody },
                  { onSuccess: () => setReplyBody('') },
                )
              }
            >
              {reply.isPending ? 'Getting suggestion...' : 'Submit reply & get suggestion'}
            </Button>
            <ErrorText error={reply.error} />
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-2 border-t pt-3">
        <span className="text-sm text-muted-foreground">Close out:</span>
        <Button
          size="sm"
          variant="outline"
          disabled={closeOutreach.isPending}
          onClick={() => closeOutreach.mutate({ id: outreach.id, status: 'closed_won' })}
        >
          Won
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={closeOutreach.isPending}
          onClick={() => closeOutreach.mutate({ id: outreach.id, status: 'closed_declined' })}
        >
          Declined
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={closeOutreach.isPending}
          onClick={() => closeOutreach.mutate({ id: outreach.id, status: 'closed_seen_no_reply' })}
        >
          Seen, no reply
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={closeOutreach.isPending}
          onClick={() => closeOutreach.mutate({ id: outreach.id, status: 'closed_not_seen' })}
        >
          Not seen
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={closeOutreach.isPending}
          onClick={() => closeOutreach.mutate({ id: outreach.id, status: 'closed_not_interested' })}
        >
          Not interested (my call)
        </Button>
        <ErrorText error={closeOutreach.error} />
      </div>
    </div>
  )
}
