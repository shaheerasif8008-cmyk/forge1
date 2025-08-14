import { useEffect, useState } from "react";
import { getRun } from "../api/testingApp";
import { useParams } from "react-router-dom";

export default function TestingLabRunDetailPage(){
  const { id } = useParams();
  const runId = Number(id);
  const [data, setData] = useState<any|null>(null);

  useEffect(()=>{
    let cancelled = false;
    async function load(){
      const d = await getRun(runId);
      if(!cancelled) setData(d);
    }
    load();
    const t = setInterval(load, 7000);
    return ()=>{ cancelled = true; clearInterval(t); }
  },[runId]);

  if(!data) return <div className="p-6">Loading…</div>
  const r = data.run;

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Run #{r.id}</h1>
        {data.report_html && (
          <a className="px-3 py-1.5 rounded bg-gray-100" href={data.report_html} target="_blank">Open report</a>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Tile label="Status" value={r.status} />
        <Tile label="Suite" value={String(r.suite_id)} />
        <Tile label="Started" value={r.started_at?.replace('T',' ').slice(0,19) || '—'} />
        <Tile label="Finished" value={r.finished_at?.replace('T',' ').slice(0,19) || '—'} />
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="text-sm font-medium mb-2">Findings</div>
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="p-2">Severity</th>
              <th className="p-2">Area</th>
              <th className="p-2">Message</th>
            </tr>
          </thead>
          <tbody>
            {(r.findings||[]).map((f:any)=> (
              <tr key={f.id} className="border-t">
                <td className="p-2">{f.severity}</td>
                <td className="p-2">{f.area}</td>
                <td className="p-2">{f.message}</td>
              </tr>
            ))}
            {!(r.findings||[]).length && <tr><td className="p-4 text-gray-500" colSpan={3}>No findings</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Tile({label, value}:{label:string; value:string}){
  return (
    <div className="bg-white rounded shadow p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-xl font-semibold">{value}</div>
    </div>
  );
}


