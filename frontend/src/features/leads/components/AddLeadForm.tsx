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
import type { LeadManualIn } from '@/api/types'

export function AddLeadForm() {
  const [open, setOpen] = useState(false)
  const [url, setUrl] = useState('')
  const [rawContent, setRawContent] = useState('')
  const [originType, setOriginType] = useState<LeadManualIn['origin_type']>('prospected')
  const addLead = useAddLead()

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    addLead.mutate(
      { url, raw_content: rawContent, origin_type: originType },
      {
        onSuccess: () => {
          setUrl('')
          setRawContent('')
          setOpen(false)
        },
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
            <DialogDescription>Paste a LinkedIn profile/post URL and its content.</DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-3 py-4">
            <Input
              type="url"
              placeholder="https://www.linkedin.com/in/..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
            />
            <Textarea
              placeholder="Paste the profile/post content here"
              value={rawContent}
              onChange={(e) => setRawContent(e.target.value)}
              rows={5}
              required
            />
            <div className="flex items-center gap-4 text-sm">
              <label className="flex items-center gap-1.5">
                <input
                  type="radio"
                  name="origin_type"
                  checked={originType === 'disclosed_need'}
                  onChange={() => setOriginType('disclosed_need')}
                />
                Disclosed need
              </label>
              <label className="flex items-center gap-1.5">
                <input
                  type="radio"
                  name="origin_type"
                  checked={originType === 'prospected'}
                  onChange={() => setOriginType('prospected')}
                />
                Prospected
              </label>
            </div>
            {addLead.error && <p className="text-sm text-destructive">{addLead.error.message}</p>}
          </div>

          <DialogFooter>
            <Button type="submit" disabled={addLead.isPending}>
              {addLead.isPending ? 'Adding...' : 'Add lead'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
