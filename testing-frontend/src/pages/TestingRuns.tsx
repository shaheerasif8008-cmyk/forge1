import { useQuery } from '@tanstack/react-query'
import { testingApi } from '../lib/testingApi'
import { Card, CardContent, CardHeader } from '../components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table'

export default function TestingRunsPage() {
  const runs = useQuery({
    queryKey: ['testing:runs'],
    queryFn: async () => (await testingApi.get('/api/v1/runs')).data as Array<{ id: number; suite_id: number; status: string; started_at?: string; finished_at?: string }>,
  })
  return (
    <div className="space-y-3 p-4">
      <Card>
        <CardHeader>Runs</CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Suite</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>View</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(runs.data ?? []).map((r) => {
                const duration = r.started_at && r.finished_at ? `${Math.max(0, (new Date(r.finished_at).getTime() - new Date(r.started_at).getTime())/1000).toFixed(1)}s` : '—'
                return (
                  <TableRow key={r.id}>
                    <TableCell>{r.id}</TableCell>
                    <TableCell>{r.suite_id}</TableCell>
                    <TableCell>{r.status}</TableCell>
                    <TableCell>{r.started_at ?? '—'}</TableCell>
                    <TableCell>{duration}</TableCell>
                    <TableCell><a className="underline" href={`/testing/runs/${r.id}`}>View</a></TableCell>
                  </TableRow>
                )
              })}
              {runs.isLoading ? (<TableRow><TableCell colSpan={6}>Loading…</TableCell></TableRow>) : null}
              {runs.error ? (<TableRow><TableCell colSpan={6} className="text-red-600">Failed to load runs</TableCell></TableRow>) : null}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}


