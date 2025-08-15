import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { testingApi } from '../lib/testingApi'
import { Card, CardContent, CardHeader } from '../components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Dialog, DialogContent, DialogTrigger } from '../components/ui/dialog'
import { useState } from 'react'
import { toast } from 'sonner'

export default function TestingSuitesPage() {
  const qc = useQueryClient()
  const suites = useQuery({
    queryKey: ['testing:suites'],
    queryFn: async () => (await testingApi.get('/api/v1/suites')).data as Array<{ id: number; name: string; target_env?: string }>,
  })

  const [targetUrl, setTargetUrl] = useState('')
  const [suiteId, setSuiteId] = useState<number | null>(null)

  const run = useMutation({
    mutationFn: async (payload: { suite_id: number; target_api_url?: string; overrides?: Record<string, any> }) =>
      (await testingApi.post('/api/v1/runs', payload)).data as { run_id: number },
    onSuccess: (d) => {
      toast.success('Run started')
      window.location.href = `/testing/runs/${d.run_id}`
    },
    onError: (e: any) => toast.error(e?.message ?? 'Run failed'),
  })

  return (
    <div className="space-y-3 p-4">
      <Card>
        <CardHeader>Suites</CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Target</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(suites.data ?? []).map((s) => (
                <TableRow key={s.id}>
                  <TableCell>{s.name}</TableCell>
                  <TableCell>{s.target_env ?? '—'}</TableCell>
                  <TableCell>
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button onClick={() => setSuiteId(s.id)}>Run</Button>
                      </DialogTrigger>
                      <DialogContent>
                        <div className="space-y-2">
                          <div className="text-sm">TARGET_API_URL</div>
                          <Input value={targetUrl} onChange={(e) => setTargetUrl(e.target.value)} placeholder="https://forge1-staging.example.com" />
                          <div className="flex justify-end">
                            <Button onClick={() => suiteId && run.mutate({ suite_id: suiteId, target_api_url: targetUrl || undefined })}>Run</Button>
                          </div>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </TableCell>
                </TableRow>
              ))}
              {suites.isLoading ? (
                <TableRow><TableCell colSpan={3}>Loading…</TableCell></TableRow>
              ) : null}
              {suites.error ? (
                <TableRow><TableCell colSpan={3} className="text-red-600">Failed to load suites</TableCell></TableRow>
              ) : null}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
