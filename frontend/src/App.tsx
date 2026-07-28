import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

function App() {
  return (
    <main className="mx-auto max-w-xl p-8">
      <h1 className="text-3xl font-bold text-foreground">Client Outreach Agent</h1>
      <p className="mt-2 text-muted-foreground">Tailwind + shadcn smoke test.</p>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Sample lead</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-3">
          <Badge>good_fit</Badge>
          <Button>Run fit-check</Button>
          <Button variant="outline">Secondary</Button>
        </CardContent>
      </Card>
    </main>
  )
}

export default App
