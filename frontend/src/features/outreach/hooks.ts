import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '@/api/client'
import { outreachApi } from '@/api/outreach'
import type { CloseStatus, OutreachDetailOut } from '@/api/types'

export const outreachKeys = {
  detail: (id: number) => ['outreach', id] as const,
  byLead: (leadId: number) => ['outreach', 'by-lead', leadId] as const,
  needsNextMessage: (minDaysOverride?: number) => ['outreach', 'needs-next-message', minDaysOverride] as const,
}

export function useOutreach(id: number) {
  return useQuery({
    queryKey: outreachKeys.detail(id),
    queryFn: () => outreachApi.get(id),
    enabled: id > 0,
  })
}

export function useOutreachByLead(leadId: number) {
  return useQuery({
    queryKey: outreachKeys.byLead(leadId),
    queryFn: async (): Promise<OutreachDetailOut | null> => {
      try {
        return await outreachApi.getByLead(leadId)
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null
        throw e
      }
    },
    enabled: leadId > 0,
  })
}

export function useNeedsNextMessage(minDaysOverride?: number) {
  return useQuery({
    queryKey: outreachKeys.needsNextMessage(minDaysOverride),
    queryFn: () => outreachApi.needsNextMessage(minDaysOverride),
  })
}

export function useFitCheck() {
  return useMutation({
    mutationFn: ({ leadId, force }: { leadId: number; force?: boolean }) => outreachApi.fitCheck(leadId, force),
  })
}

export function useConnect() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ leadId, force }: { leadId: number; force?: boolean }) => outreachApi.connect(leadId, force),
    onSuccess: (data) => {
      queryClient.setQueryData(outreachKeys.detail(data.id), data)
      queryClient.setQueryData(outreachKeys.byLead(data.lead_id), data)
    },
  })
}

export function usePassOnLead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (leadId: number) => outreachApi.pass(leadId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: outreachKeys.detail(data.id) })
      queryClient.invalidateQueries({ queryKey: outreachKeys.byLead(data.lead_id) })
    },
  })
}

export function useMarkConnectionSent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => outreachApi.markConnectionSent(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: outreachKeys.detail(data.id) })
      queryClient.invalidateQueries({ queryKey: outreachKeys.byLead(data.lead_id) })
    },
  })
}

export function useConnectionResponse() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: 'accepted' | 'declined' | 'no_response' }) =>
      outreachApi.connectionResponse(id, status),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: outreachKeys.detail(data.id) })
      queryClient.invalidateQueries({ queryKey: outreachKeys.byLead(data.lead_id) })
    },
  })
}

export function useNextMessage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => outreachApi.nextMessage(id),
    onSuccess: (data) => {
      queryClient.setQueryData(outreachKeys.detail(data.id), data)
      queryClient.setQueryData(outreachKeys.byLead(data.lead_id), data)
    },
  })
}

export function useMarkSent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => outreachApi.markSent(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: outreachKeys.detail(data.id) })
      queryClient.invalidateQueries({ queryKey: outreachKeys.byLead(data.lead_id) })
    },
  })
}

export function useReply() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: string }) => outreachApi.reply(id, body),
    onSuccess: (data) => {
      queryClient.setQueryData(outreachKeys.detail(data.id), data)
      queryClient.setQueryData(outreachKeys.byLead(data.lead_id), data)
    },
  })
}

export function useMarkReplySent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => outreachApi.markReplySent(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: outreachKeys.detail(data.id) })
      queryClient.invalidateQueries({ queryKey: outreachKeys.byLead(data.lead_id) })
    },
  })
}

export function useCloseOutreach() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: CloseStatus }) => outreachApi.close(id, status),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: outreachKeys.detail(data.id) })
      queryClient.invalidateQueries({ queryKey: outreachKeys.byLead(data.lead_id) })
    },
  })
}
