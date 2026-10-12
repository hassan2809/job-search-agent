import { useCheckStats } from '../hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

// Human-readable names for the stable rule codes in app/services/message_checks.py.
const RULE_LABELS: Record<string, string> = {
  dash: 'Dash used as punctuation',
  too_long: 'Over the word limit',
  repo_link: 'Linked a repository',
  banned_phrase: 'Used a banned phrase',
  repeated_project: 'Re-used a project from earlier in the thread',
  invented_employer: 'Invented an employer for a project',
  wrong_employer: 'Attributed a project to the wrong employer',
  soft_close_question: 'Soft close asked a question',
  soft_close_project: 'Soft close named a project',
  note_too_long: 'Connection note over 300 characters',
}

export function DraftQualityPanel() {
  const { data } = useCheckStats()
  // Nothing drafted since checks existed -- an empty panel would just be noise.
  if (!data || data.drafts === 0) return null

  const cleanRate = Math.round((data.clean_first_time / data.drafts) * 100)

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="text-sm">Draft quality</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm text-muted-foreground">
          {data.drafts} draft{data.drafts === 1 ? '' : 's'} checked. {cleanRate}% were clean first time.
          {data.retried > 0 && ` ${data.retry_fixed_all} of ${data.retried} retries fixed every problem.`}
          {data.still_broken > 0 && ` ${data.still_broken} still need editing.`}
        </p>

        {data.by_rule.length > 0 && (
          <div className="flex flex-col gap-1">
            <p className="text-xs text-muted-foreground">
              Rules broken on the first attempt. A high count means the prompt isn't landing; an
              unresolved count means the retry can't fix it either.
            </p>
            <table className="text-xs">
              <thead className="text-muted-foreground">
                <tr>
                  <th className="text-left font-normal">Rule</th>
                  <th className="w-20 text-right font-normal">First try</th>
                  <th className="w-20 text-right font-normal">Unresolved</th>
                </tr>
              </thead>
              <tbody>
                {data.by_rule.map((rule) => (
                  <tr key={rule.code}>
                    <td className="py-0.5">{RULE_LABELS[rule.code] ?? rule.code}</td>
                    <td className="text-right tabular-nums">{rule.first_attempt}</td>
                    <td
                      className={`text-right tabular-nums ${rule.unresolved > 0 ? 'text-destructive' : 'text-muted-foreground'}`}
                    >
                      {rule.unresolved}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
