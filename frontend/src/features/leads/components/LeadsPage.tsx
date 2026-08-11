import { useEffect, useState } from 'react'
import { AddLeadForm } from './AddLeadForm'
import { LeadsList } from './LeadsList'
import { BulkFitCheckDialog } from './BulkFitCheckDialog'
import { FollowUpsBoard } from '@/features/outreach/components/FollowUpsBoard'
import { DraftQualityPanel } from '@/features/outreach/components/DraftQualityPanel'
import { PendingConnectionsBoard } from '@/features/outreach/components/PendingConnectionsBoard'
import { SeasonNote } from '@/features/outreach/components/SeasonNote'
import { useLeads } from '../hooks'
import type { LeadFilters } from '@/api/leads'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'

const PAGE_SIZE = 10
const SEARCH_DEBOUNCE_MS = 300

export function LeadsPage() {
  const [page, setPage] = useState(0)
  const [filters, setFilters] = useState<LeadFilters>({})
  const [searchInput, setSearchInput] = useState('')
  const { data, isLoading, error } = useLeads(PAGE_SIZE, page * PAGE_SIZE, filters)
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  function updateFilters(partial: Partial<LeadFilters>) {
    setFilters((prev) => ({ ...prev, ...partial }))
    setPage(0)
  }

  // Debounce free-text search so typing doesn't fire a request per keystroke.
  useEffect(() => {
    const timeout = setTimeout(() => {
      updateFilters({ search: searchInput || undefined })
    }, SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timeout)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput])

  return (
    <div className="min-h-svh bg-muted/30">
      <header className="border-b bg-background">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-lg font-semibold text-foreground">Client Outreach Agent</h1>
            <p className="text-sm text-muted-foreground">Review leads and run fit-checks</p>
          </div>
          <AddLeadForm />
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-6">
        <SeasonNote />

        <PendingConnectionsBoard />

        <FollowUpsBoard />

        <DraftQualityPanel />

        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-1 items-center gap-2">
            <Input
              type="search"
              placeholder="Search name or profile text..."
              className="max-w-xs"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />

            <NativeSelect
              size="sm"
              value={filters.originType ?? 'all'}
              onChange={(e) =>
                updateFilters({
                  originType: e.target.value === 'all' ? undefined : (e.target.value as LeadFilters['originType']),
                })
              }
            >
              <NativeSelectOption value="all">All origins</NativeSelectOption>
              <NativeSelectOption value="disclosed_need">Disclosed need</NativeSelectOption>
              <NativeSelectOption value="prospected">Prospected</NativeSelectOption>
            </NativeSelect>

            <NativeSelect
              size="sm"
              value={filters.fitStatus ?? 'all'}
              onChange={(e) =>
                updateFilters({
                  fitStatus: e.target.value === 'all' ? undefined : (e.target.value as LeadFilters['fitStatus']),
                })
              }
            >
              <NativeSelectOption value="all">All fit statuses</NativeSelectOption>
              <NativeSelectOption value="not_checked">Not checked</NativeSelectOption>
              <NativeSelectOption value="good_fit">Good fit</NativeSelectOption>
              <NativeSelectOption value="maybe">Maybe</NativeSelectOption>
              <NativeSelectOption value="not_a_fit">Not a fit</NativeSelectOption>
            </NativeSelect>

            <NativeSelect
              size="sm"
              value={filters.outreachStatus ?? 'all'}
              onChange={(e) =>
                updateFilters({
                  outreachStatus:
                    e.target.value === 'all' ? undefined : (e.target.value as LeadFilters['outreachStatus']),
                })
              }
            >
              <NativeSelectOption value="all">All outreach statuses</NativeSelectOption>
              <NativeSelectOption value="not_started">Not started</NativeSelectOption>
              <NativeSelectOption value="connection_drafted">Connection drafted</NativeSelectOption>
              <NativeSelectOption value="connection_sent">Connection sent</NativeSelectOption>
              <NativeSelectOption value="connection_accepted">Connection accepted</NativeSelectOption>
              <NativeSelectOption value="connection_declined">Connection declined</NativeSelectOption>
              <NativeSelectOption value="connection_no_response">Connection no response</NativeSelectOption>
              <NativeSelectOption value="message_drafted">Message drafted</NativeSelectOption>
              <NativeSelectOption value="awaiting_reply">Awaiting reply</NativeSelectOption>
              <NativeSelectOption value="replied">Replied</NativeSelectOption>
              <NativeSelectOption value="closed_won">Won</NativeSelectOption>
              <NativeSelectOption value="closed_declined">Declined</NativeSelectOption>
              <NativeSelectOption value="closed_no_response">No response (closed)</NativeSelectOption>
              <NativeSelectOption value="closed_not_interested">Not interested (my call)</NativeSelectOption>
            </NativeSelect>
          </div>

          <BulkFitCheckDialog />
        </div>

        <LeadsList leads={data?.items} isLoading={isLoading} error={error} />

        {data && data.total > PAGE_SIZE && (
          <div className="mt-6 flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Showing {page * PAGE_SIZE + 1}-{Math.min((page + 1) * PAGE_SIZE, data.total)} of {data.total}
            </p>
            <Pagination className="mx-0 w-auto">
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    href="#"
                    onClick={(e) => {
                      e.preventDefault()
                      setPage((p) => Math.max(0, p - 1))
                    }}
                  />
                </PaginationItem>
                <PaginationItem>
                  <span className="px-2 text-sm text-muted-foreground">
                    Page {page + 1} of {totalPages}
                  </span>
                </PaginationItem>
                <PaginationItem>
                  <PaginationNext
                    href="#"
                    onClick={(e) => {
                      e.preventDefault()
                      setPage((p) => Math.min(totalPages - 1, p + 1))
                    }}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          </div>
        )}
      </main>
    </div>
  )
}
