import { useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { leadsApi, type LeadFilters } from '@/api/leads'
import { outreachApi } from '@/api/outreach'
import type { LeadManualIn } from '@/api/types'

export const leadsKeys = {
  list: (limit: number, offset: number, filters: LeadFilters) =>
    ['leads', 'list', limit, offset, filters] as const,
  detail: (id: number) => ['leads', 'detail', id] as const,
}

export function useLeads(limit: number, offset: number, filters: LeadFilters = {}) {
  return useQuery({
    queryKey: leadsKeys.list(limit, offset, filters),
    queryFn: () => leadsApi.list(limit, offset, filters),
    placeholderData: keepPreviousData,
  })
}

export function useLead(id: number) {
  return useQuery({
    queryKey: leadsKeys.detail(id),
    queryFn: () => leadsApi.get(id),
    enabled: id > 0,
  })
}

export function useAddLead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: LeadManualIn) => leadsApi.addManual(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads', 'list'] })
    },
  })
}

export function useSetContactEmail() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, contactEmail }: { id: number; contactEmail: string }) =>
      leadsApi.setContactEmail(id, contactEmail),
    onSuccess: (data) => {
      queryClient.setQueryData(leadsKeys.detail(data.id), data)
      queryClient.invalidateQueries({ queryKey: ['leads', 'list'] })
    },
  })
}

interface BulkFitCheckState {
  running: boolean
  total: number
  completed: number
  failed: number
}

export function useBulkFitCheck() {
  const queryClient = useQueryClient()
  const [state, setState] = useState<BulkFitCheckState>({ running: false, total: 0, completed: 0, failed: 0 })

  async function run() {
    setState({ running: true, total: 0, completed: 0, failed: 0 })
    const { items } = await leadsApi.list(500, 0, { fitStatus: 'not_checked' })
    setState({ running: true, total: items.length, completed: 0, failed: 0 })

    let failed = 0
    for (const lead of items) {
      try {
        await outreachApi.fitCheck(lead.id)
      } catch {
        failed += 1
      }
      setState((prev) => ({ ...prev, completed: prev.completed + 1, failed }))
    }

    setState((prev) => ({ ...prev, running: false }))
    queryClient.invalidateQueries({ queryKey: ['leads', 'list'] })
  }

  return { ...state, run }
}
