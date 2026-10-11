import { useState, type FormEvent } from 'react'
import { useAddLead } from '../hooks'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import type { OriginType } from '@/api/types'

export function AddLeadForm() {
  const [open, setOpen] = useState(false)
  const [url, setUrl] = useState('')
  const [originType, setOriginType] = useState<OriginType>('prospected')
  const [rawContent, setRawContent] = useState('')
  const [showPaste, setShowPaste] = useState(false)
  const addLead = useAddLead()

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    addLead.mutate(
      { url, origin_type: originType, raw_content: rawContent.trim() || undefined },
      {
        onSuccess: () => {
          setUrl('')
          setRawContent('')
          setShowPaste(false)
          setOpen(false)
        },
        // A scrape failure leaves the lead saved but empty, and re-submitting the same URL retries
        // it. Open the paste box so the fallback is right there instead of a dead end.
        onError: () => setShowPaste(true),
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button />}>Add lead</DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add a lead</DialogTitle>
            <DialogDescription>
              Paste a LinkedIn profile URL. On submit we scrape and save the profile.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-3 py-4">
            <Input
              type="url"
              placeholder="https://www.linkedin.com/in/..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              disabled={addLead.isPending}
            />
            <div className="flex items-center gap-4 text-sm">
              <label className="flex items-center gap-1.5">
                <input
                  type="radio"
                  name="origin_type"
                  checked={originType === 'disclosed_need'}
                  onChange={() => setOriginType('disclosed_need')}
                  disabled={addLead.isPending}
                />
                Disclosed need
              </label>
              <label className="flex items-center gap-1.5">
                <input
                  type="radio"
                  name="origin_type"
                  checked={originType === 'hiring_signal'}
                  onChange={() => setOriginType('hiring_signal')}
                  disabled={addLead.isPending}
                />
                Hiring signal
              </label>
              <label className="flex items-center gap-1.5">
                <input
                  type="radio"
                  name="origin_type"
                  checked={originType === 'prospected'}
                  onChange={() => setOriginType('prospected')}
                  disabled={addLead.isPending}
                />
                Prospected
              </label>
            </div>
            {addLead.error && <p className="text-sm text-destructive">{addLead.error.message}</p>}

            {showPaste ? (
              <div className="flex flex-col gap-1.5">
                <label className="text-sm text-muted-foreground">
                  Profile text (optional). Paste the profile here to skip scraping entirely, which is
                  the way through when LinkedIn asks for a login.
                </label>
                <Textarea
                  rows={6}
                  placeholder="Paste the full LinkedIn profile text..."
                  value={rawContent}
                  onChange={(e) => setRawContent(e.target.value)}
                  disabled={addLead.isPending}
                />
              </div>
            ) : (
              <button
                type="button"
                className="self-start text-sm text-muted-foreground underline underline-offset-4"
                onClick={() => setShowPaste(true)}
              >
                Paste profile text instead of scraping
              </button>
            )}
          </div>

          <DialogFooter>
            <Button type="submit" disabled={addLead.isPending}>
              {addLead.isPending
                ? rawContent.trim()
                  ? 'Saving...'
                  : 'Scraping profile...'
                : addLead.error
                  ? 'Retry'
                  : 'Add lead'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
