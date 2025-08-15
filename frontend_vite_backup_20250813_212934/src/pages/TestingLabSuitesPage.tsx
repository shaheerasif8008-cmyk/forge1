import { useEffect, useState } from "react";
import { createRun, createSuite, listSuites, seedBaseline } from "../api/testingApp";

export default function TestingLabSuitesPage(){
  const [suites, setSuites] = useState<any[]>([]);
  const [name, setName] = useState("baseline");
  const [target, setTarget] = useState("http://localhost:8000");
  const [busy, setBusy] = useState(false);

  async function refresh(){
    setSuites(await listSuites());
  }
  useEffect(()=>{ refresh(); },[]);

  async function onCreate(){
    setBusy(true);
    try{
      await createSuite({ name, target_env: 'staging', scenario_ids: [], load_profile: { tool: 'k6', vus: 1, duration: '1s', endpoints: ['/health'] } });
      await refresh();
    } finally { setBusy(false); }
  }
  async function onSeed(){
    setBusy(true);
    try{ await seedBaseline(); await refresh(); } finally { setBusy(false); }
  }
  async function onRun(id:number){
    setBusy(true);
    try{ await createRun(id, target); } finally { setBusy(false); }
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Suites</h1>
        <div className="space-x-2">
          <button onClick={onSeed} disabled={busy} className="px-3 py-1.5 rounded bg-gray-100">Seed baseline</button>
        </div>
      </div>

      <div className="bg-white rounded shadow p-4 space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <input className="border rounded px-2 py-1" placeholder="Suite name" value={name} onChange={e=>setName(e.target.value)} />
          <input className="border rounded px-2 py-1" placeholder="Target API URL" value={target} onChange={e=>setTarget(e.target.value)} />
          <button onClick={onCreate} disabled={busy} className="px-3 py-1.5 rounded bg-blue-600 text-white">Create</button>
        </div>
      </div>

      <div className="bg-white rounded shadow p-4">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="p-2">ID</th>
              <th className="p-2">Name</th>
              <th className="p-2">Env</th>
              <th className="p-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {suites.map(s => (
              <tr key={s.id} className="border-t">
                <td className="p-2">{s.id}</td>
                <td className="p-2">{s.name}</td>
                <td className="p-2">{s.target_env}</td>
                <td className="p-2">
                  <button onClick={()=>onRun(s.id)} disabled={busy} className="px-2 py-1 rounded bg-emerald-600 text-white">Run</button>
                </td>
              </tr>
            ))}
            {!suites.length && <tr><td className="p-4 text-gray-500" colSpan={4}>No suites</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}


