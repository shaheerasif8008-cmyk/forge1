import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader } from '../components/ui/card'

export default function TestingReportsPage() {
  // Reports are served from artifacts; simple list of the last N runs' report links could be provided by backend; placeholder with static pattern
  const reports = useQuery({
    queryKey: ['testing:reports'],
    queryFn: async () => Array.from({ length: 10 }).map((_, i) => ({ id: i + 1, url: `/artifacts/run_${i + 1}/report.html`, date: new Date().toISOString() })),
  })
  return (
    <div className="space-y-3 p-4">
      <Card>
        <CardHeader>Signed Reports</CardHeader>
        <CardContent>
          <ul className="list-disc space-y-1 pl-4 text-sm">
            {(reports.data ?? []).map((r) => (
              <li key={r.id}><a className="underline" href={r.url} target="_blank" rel="noreferrer">Run {r.id} — {r.date}</a></li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}


