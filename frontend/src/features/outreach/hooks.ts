import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { outreachApi } from '@/api/outreach'

export const outreachKeys = {
  detail: (id: number) => ['outreach', id] as const,
  needsNextMessage: (minDaysOverride?: number) => ['outreach', 'needs-next-message', minDaysOverride] as const,
}

export function useOutreach(id: number) {
  return useQuery({
    queryKey: outreachKeys.detail(id),
    queryFn: () => outreachApi.get(id),
    enabled: id > 0,
  })
}

export function useNeedsNextMessage(minDaysOverride?: number) {
  return useQuery({
    queryKey: outreachKeys.needsNextMessage(minDaysOverride),
    queryFn: () => outreachApi.needsNextMessage(minDaysOverride),
  })
}

// Fit-check and connect are idempotent server-side (see app/api/v1/outreach.py) -- re-running
// without force just returns the existing result, so these mutations are safe to fire freely.
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
    },
  })
}

export function useMarkConnectionSent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => outreachApi.markConnectionSent(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: outreachKeys.detail(data.id) })
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
    },
  })
}

export function useNextMessage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => outreachApi.nextMessage(id),
    onSuccess: (data) => {
      queryClient.setQueryData(outreachKeys.detail(data.id), data)
    },
  })
}

export function useMarkSent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => outreachApi.markSent(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: outreachKeys.detail(data.id) })
    },
  })
}

export function useReply() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: string }) => outreachApi.reply(id, body),
    onSuccess: (data) => {
      queryClient.setQueryData(outreachKeys.detail(data.id), data)
    },
  })
}

export function useCloseOutreach() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: 'closed_won' | 'closed_declined' | 'closed_no_response' }) =>
      outreachApi.close(id, status),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: outreachKeys.detail(data.id) })
    },
  })
}
