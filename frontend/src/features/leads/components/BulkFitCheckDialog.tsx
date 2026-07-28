import { useState } from 'react'
import { useBulkFitCheck } from '../hooks'
import { Button } from '@/components/ui/button'
import { Progress, ProgressLabel, ProgressValue } from '@/components/ui/progress'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

export function BulkFitCheckDialog() {
  const [open, setOpen] = useState(false)
  const bulkFitCheck = useBulkFitCheck()
  const remaining = bulkFitCheck.total - bulkFitCheck.completed
  const percent = bulkFitCheck.total > 0 ? Math.round((bulkFitCheck.completed / bulkFitCheck.total) * 100) : 0
  const isDone = !bulkFitCheck.running && bulkFitCheck.total > 0

  return (
    <>
      <Button
        size="sm"
        variant="outline"
        onClick={() => {
          setOpen(true)
          bulkFitCheck.run()
        }}
      >
        Run fit-check for all unchecked
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent showCloseButton={!bulkFitCheck.running}>
          <DialogHeader>
            <DialogTitle>Running fit-checks</DialogTitle>
            <DialogDescription>
              {bulkFitCheck.total === 0 && bulkFitCheck.running
                ? 'Finding unchecked leads...'
                : isDone
                  ? `Done — ${bulkFitCheck.completed} checked${bulkFitCheck.failed ? `, ${bulkFitCheck.failed} failed` : ''}.`
                  : 'Checking leads one at a time so this stays within rate limits.'}
            </DialogDescription>
          </DialogHeader>

          {bulkFitCheck.total > 0 && (
            <Progress value={percent}>
              <div className="flex w-full items-center justify-between">
                <ProgressLabel>
                  {bulkFitCheck.completed} of {bulkFitCheck.total} checked
                  {remaining > 0 ? ` · ${remaining} left` : ''}
                </ProgressLabel>
                <ProgressValue />
              </div>
            </Progress>
          )}

          {isDone && (
            <DialogFooter>
              <Button size="sm" onClick={() => setOpen(false)}>
                Close
              </Button>
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
