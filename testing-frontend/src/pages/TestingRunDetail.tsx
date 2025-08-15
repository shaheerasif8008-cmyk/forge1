import { useEffect, useState } from 'react'
import { testingApi } from '../lib/testingApi'
import { Card, CardContent, CardHeader } from '../components/ui/card'
import { LineChart as RLineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

type RunDoc = { id: number; suite_id: number; status: string; started_at?: string; finished_at?: string; stats?: any }

export default function TestingRunDetailPage() {
  const runId = Number(window.location.pathname.split('/').pop())
  const [data, setData] = useState<{ run: RunDoc; signed_report_url?: string } | null>(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let timer: number | undefined
    async function fetchRun() {
      try {
        const res = await testingApi.get(`/api/v1/runs/${runId}`)
        setData({ run: res.data.run, signed_report_url: res.data.signed_report_url })
        if (res.data.run.status === 'running') {
          timer = window.setTimeout(() => setTick((t) => t + 1), 3000)
        }
      } catch (e) {
        // ignore transient
      }
    }
    fetchRun()
    return () => { if (timer) window.clearTimeout(timer) }
  }, [runId, tick])

  const points = Array.from({ length: 10 }).map((_, i) => ({ x: i, rps: Math.round(Math.random()*10)+10, p95: Math.round(Math.random()*100)+200, err: Math.random() }))

  return (
    <div className="space-y-3 p-4">
      <Card>
        <CardHeader>Run #{runId}</CardHeader>
        <CardContent>
          <div className="mb-2 text-sm">Status: <span className="rounded-md border px-2 py-0.5">{data?.run.status ?? '—'}</span></div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <RLineChart data={points}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="x" /><YAxis /><Tooltip /><Line dataKey="rps" stroke="#3b82f6" /></RLineChart>
              </ResponsiveContainer>
            </div>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <RLineChart data={points}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="x" /><YAxis /><Tooltip /><Line dataKey="p95" stroke="#10b981" /></RLineChart>
              </ResponsiveContainer>
            </div>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <RLineChart data={points}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="x" /><YAxis /><Tooltip /><Line dataKey="err" stroke="#ef4444" /></RLineChart>
              </ResponsiveContainer>
            </div>
          </div>
          {data?.signed_report_url ? (
            <div className="mt-4 text-sm"><a className="underline" href={data.signed_report_url} target="_blank" rel="noreferrer">View signed report</a></div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}


