import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AddLeadForm } from './AddLeadForm'
import { LeadsList } from './LeadsList'
import { BulkFitCheckDialog } from './BulkFitCheckDialog'
import { AttentionRail } from '@/features/outreach/components/AttentionRail'
import { useLeads } from '../hooks'
import type { LeadFilters } from '@/api/leads'
import { Button } from '@/components/ui/button'
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

// Filters and page live in the URL (not component state) so they survive navigating to a lead and
// back, a page reload, or sharing the link -- the thing that used to reset to blank every time you
// opened a lead from a filtered list.
function readFilters(params: URLSearchParams): LeadFilters {
  return {
    search: params.get('q') || undefined,
    originType: (params.get('origin') as LeadFilters['originType']) || undefined,
    fitStatus: (params.get('fit') as LeadFilters['fitStatus']) || undefined,
    outreachStatus: (params.get('status') as LeadFilters['outreachStatus']) || undefined,
  }
}

function readPage(params: URLSearchParams): number {
  const raw = Number(params.get('page'))
  return Number.isFinite(raw) && raw > 1 ? raw - 1 : 0
}

export function LeadsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = useMemo(() => readFilters(searchParams), [searchParams])
  const page = readPage(searchParams)
  const [searchInput, setSearchInput] = useState(filters.search ?? '')

  const { data, isLoading, error } = useLeads(PAGE_SIZE, page * PAGE_SIZE, filters)
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  function updateParams(partial: Record<string, string | undefined>) {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        for (const [key, value] of Object.entries(partial)) {
          if (value) next.set(key, value)
          else next.delete(key)
        }
        next.delete('page')
        return next
      },
      { replace: true },
    )
  }

  // Debounce free-text search so typing doesn't fire a request (or a history entry) per keystroke.
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (searchInput !== (filters.search ?? '')) updateParams({ q: searchInput || undefined })
    }, SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timeout)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput])

  function setPage(next: number) {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev)
      if (next > 0) params.set('page', String(next + 1))
      else params.delete('page')
      return params
    })
  }

  const activeFilterCount = [filters.search, filters.originType, filters.fitStatus, filters.outreachStatus].filter(
    Boolean,
  ).length

  function clearFilters() {
    setSearchInput('')
    setSearchParams({}, { replace: true })
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Leads</h1>
          <p className="text-sm text-muted-foreground">Review leads and run fit-checks</p>
        </div>
        <div className="flex items-center gap-2">
          <BulkFitCheckDialog />
          <AddLeadForm />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px] lg:items-start">
        <div className="flex min-w-0 flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2 rounded-xl border bg-background p-3">
            <Input
              type="search"
              placeholder="Search name or profile text..."
              className="min-w-0 flex-1 sm:max-w-xs"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />

            <NativeSelect
              size="sm"
              value={filters.originType ?? 'all'}
              onChange={(e) => updateParams({ origin: e.target.value === 'all' ? undefined : e.target.value })}
            >
              <NativeSelectOption value="all">All origins</NativeSelectOption>
              <NativeSelectOption value="disclosed_need">Disclosed need</NativeSelectOption>
              <NativeSelectOption value="hiring_signal">Hiring signal</NativeSelectOption>
              <NativeSelectOption value="prospected">Prospected</NativeSelectOption>
            </NativeSelect>

            <NativeSelect
              size="sm"
              value={filters.fitStatus ?? 'all'}
              onChange={(e) => updateParams({ fit: e.target.value === 'all' ? undefined : e.target.value })}
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
              onChange={(e) => updateParams({ status: e.target.value === 'all' ? undefined : e.target.value })}
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
              <NativeSelectOption value="closed_seen_no_reply">Seen, no reply (closed)</NativeSelectOption>
              <NativeSelectOption value="closed_not_seen">Not seen (closed)</NativeSelectOption>
              <NativeSelectOption value="closed_not_interested">Not interested (my call)</NativeSelectOption>
            </NativeSelect>

            {activeFilterCount > 0 && (
              <Button size="sm" variant="ghost" onClick={clearFilters}>
                Clear filters ({activeFilterCount})
              </Button>
            )}

            {data !== undefined && (
              <span className="ml-auto text-sm text-muted-foreground">{data.total} lead{data.total === 1 ? '' : 's'}</span>
            )}
          </div>

          <LeadsList leads={data?.items} isLoading={isLoading} error={error} />

          {data && data.total > PAGE_SIZE && (
            <div className="flex items-center justify-between">
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
                        setPage(Math.max(0, page - 1))
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
                        setPage(Math.min(totalPages - 1, page + 1))
                      }}
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            </div>
          )}
        </div>

        <aside className="lg:sticky lg:top-20">
          <AttentionRail />
        </aside>
      </div>
    </div>
  )
}
