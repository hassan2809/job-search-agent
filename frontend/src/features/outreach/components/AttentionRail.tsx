import { SeasonNote } from './SeasonNote'
import { PendingConnectionsBoard } from './PendingConnectionsBoard'
import { FollowUpsBoard } from './FollowUpsBoard'
import { DraftQualityPanel } from './DraftQualityPanel'

// Groups everything that used to be stacked full-width above the leads list (season note, pending
// connections, follow-ups due, draft quality) into one side rail. Each board already renders
// nothing when it has nothing to say, so an empty rail collapses to nothing on its own.
export function AttentionRail() {
  return (
    <div className="flex flex-col gap-4">
      <SeasonNote />
      <PendingConnectionsBoard />
      <FollowUpsBoard />
      <DraftQualityPanel />
    </div>
  )
}
