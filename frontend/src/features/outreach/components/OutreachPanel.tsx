import { useState } from 'react'
import { MessageThread } from './MessageThread'
import { ActionNotice } from './ActionNotice'
import {
  useCloseOutreach,
  useConnect,
  useConnectionResponse,
  useConnectWithoutNote,
  useDraftEmail,
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
import type { FitVerdict, OutreachDetailOut } from '@/api/types'

function ErrorText({ error }: { error: Error | null }) {
  if (!error) return null
  return <p className="text-sm text-destructive">{error.message}</p>
}

// Email runs independently of the LinkedIn connection lifecycle -- the plan sends it first, before
// any connection request -- so this renders the same way whether there's no outreach yet, a closed
// one, or an active one, rather than being wired into any one status branch above.
function EmailSection({
  leadId,
  contactEmail,
  outreach,
}: {
  leadId: number
  contactEmail: string | null
  outreach: OutreachDetailOut | null
}) {
  const draftEmail = useDraftEmail()
  const hasEmailSent = outreach?.messages.some((m) => m.channel === 'email') ?? false

  if (!contactEmail) {
    return (
      <p className="text-xs text-muted-foreground">
        No contact email saved for this lead yet. Look one up (Hunter.io or the company site) and save
        it above to enable email outreach.
      </p>
    )
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {!hasEmailSent ? (
        <Button
          size="sm"
          variant="outline"
          disabled={draftEmail.isPending}
          onClick={() => draftEmail.mutate({ leadId, followUpStage: 'opening' })}
        >
          {draftEmail.isPending ? 'Drafting...' : 'Draft opening email'}
        </Button>
      ) : (
        <>
          <Button
            size="sm"
            variant="outline"
            disabled={draftEmail.isPending}
            onClick={() => draftEmail.mutate({ leadId, followUpStage: 'value_add' })}
          >
            {draftEmail.isPending ? 'Drafting...' : 'Draft day-4 follow-up'}
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={draftEmail.isPending}
            onClick={() => draftEmail.mutate({ leadId, followUpStage: 'clear_ask' })}
          >
            {draftEmail.isPending ? 'Drafting...' : 'Draft day-10 follow-up'}
          </Button>
        </>
      )}
      <ErrorText error={draftEmail.error} />
    </div>
  )
}

export function OutreachPanel({
  leadId,
  fitVerdict,
  contactEmail,
}: {
  leadId: number
  fitVerdict: FitVerdict | null
  contactEmail: string | null
}) {
  const { data: outreach, isLoading } = useOutreachByLead(leadId)
  const connect = useConnect()
  const connectWithoutNote = useConnectWithoutNote()
  const markConnectionSent = useMarkConnectionSent()
  const connectionResponse = useConnectionResponse()
  const nextMessage = useNextMessage()
  const markSent = useMarkSent()
  const markReplySent = useMarkReplySent()
  const reply = useReply()
  const closeOutreach = useCloseOutreach()
  const passOnLead = usePassOnLead()
  const [replyBody, setReplyBody] = useState('')
  const [replyChannel, setReplyChannel] = useState<'linkedin' | 'email'>('linkedin')

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading outreach status...</p>

  if (!outreach) {
    const canConnect = fitVerdict && fitVerdict !== 'not_a_fit'
    return (
      <div className="flex flex-col gap-3">
        {!fitVerdict && <p className="text-sm text-muted-foreground">Run a fit-check first to unlock outreach.</p>}
        {fitVerdict === 'not_a_fit' && (
          <p className="text-sm text-muted-foreground">Fit-check came back "not a fit" — no outreach.</p>
        )}
        <div className="flex flex-wrap gap-2">
          {canConnect && (
            <>
              <Button size="sm" disabled={connect.isPending} onClick={() => connect.mutate({ leadId })}>
                {connect.isPending ? 'Drafting...' : 'Send connection request'}
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={connectWithoutNote.isPending}
                onClick={() => connectWithoutNote.mutate(leadId)}
              >
                {connectWithoutNote.isPending ? 'Saving...' : 'Connect without a note'}
              </Button>
            </>
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
        <ErrorText error={connect.error ?? connectWithoutNote.error ?? passOnLead.error} />
        {canConnect && (
          <div className="border-t pt-3">
            <EmailSection leadId={leadId} contactEmail={contactEmail} outreach={null} />
          </div>
        )}
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
        {/* Closed on LinkedIn is not closed everywhere -- a fresh email touch reopens this thread
            server-side (see POST /outreach/{lead_id}/email), which is deliberate per the plan. */}
        <div className="border-t pt-3">
          <p className="mb-2 text-xs text-muted-foreground">Closed on LinkedIn, but email is a separate channel:</p>
          <EmailSection leadId={leadId} contactEmail={contactEmail} outreach={outreach} />
        </div>
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
            <div className="flex items-center gap-3 text-sm">
              <span className="text-muted-foreground">Came in on:</span>
              <label className="flex items-center gap-1.5">
                <input
                  type="radio"
                  name="reply_channel"
                  checked={replyChannel === 'linkedin'}
                  onChange={() => setReplyChannel('linkedin')}
                />
                LinkedIn
              </label>
              <label className="flex items-center gap-1.5">
                <input
                  type="radio"
                  name="reply_channel"
                  checked={replyChannel === 'email'}
                  onChange={() => setReplyChannel('email')}
                />
                Email
              </label>
            </div>
            <Button
              size="sm"
              disabled={reply.isPending || !replyBody.trim()}
              onClick={() =>
                reply.mutate(
                  { id: outreach.id, body: replyBody, channel: replyChannel },
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

      <div className="border-t pt-3">
        <p className="mb-2 text-xs text-muted-foreground">Email (separate from the LinkedIn sequence above):</p>
        <EmailSection leadId={leadId} contactEmail={contactEmail} outreach={outreach} />
      </div>

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
