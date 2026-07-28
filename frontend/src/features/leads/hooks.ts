import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { leadsApi } from '@/api/leads'
import type { LeadManualIn } from '@/api/types'

export const leadsKeys = {
  list: (limit: number) => ['leads', 'list', limit] as const,
}

export function useLeads(limit = 50) {
  return useQuery({
    queryKey: leadsKeys.list(limit),
    queryFn: () => leadsApi.list(limit),
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
