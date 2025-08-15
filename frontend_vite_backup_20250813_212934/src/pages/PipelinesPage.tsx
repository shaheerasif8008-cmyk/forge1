import { useEffect, useMemo, useState } from "react";
import config from "../config";
import { useSession } from "../components/SessionManager";
import { LoadingSpinner } from "../components/LoadingSpinner";

type Employee = { id: string; name: string };
type Step = { employee_id: string; order: number; input_map: Record<string, string>; output_key: string };
type Pipeline = { id: string; name: string; description?: string; steps: Step[] };

export default function PipelinesPage() {
  const { token } = useSession();
  const headers = useMemo(()=> ({ 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }), [token]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [runOutput, setRunOutput] = useState<any>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [emps, pips] = await Promise.all([
        fetch(`${config.apiUrl}/api/v1/employees`, { headers }).then(r=> r.json()),
        fetch(`${config.apiUrl}/api/v1/pipelines`, { headers }).then(r=> r.json()),
      ]);
      setEmployees(emps);
      setPipelines(pips);
    } finally {
      setLoading(false);
    }
  };

  useEffect(()=> { void load(); }, [headers]);

  const addStep = () => setSteps(s => [...s, { employee_id: employees[0]?.id || "", order: s.length, input_map: {}, output_key: `step${s.length+1}` }]);
  const savePipeline = async () => {
    if (!name.trim() || steps.length === 0) return;
    const res = await fetch(`${config.apiUrl}/api/v1/pipelines`, { method: 'POST', headers, body: JSON.stringify({ name, description: desc, steps }) });
    if (res.ok) { setName(""); setDesc(""); setSteps([]); await load(); }
  };
  const runPipeline = async (id: string) => {
    setRunningId(id); setRunOutput(null);
    const res = await fetch(`${config.apiUrl}/api/v1/pipelines/${id}/run`, { method: 'POST', headers, body: JSON.stringify({ task: 'Run pipeline demo' }) });
    const data = await res.json();
    setRunOutput(data);
    setRunningId(null);
  };

  if (loading) return <div className="p-6"><LoadingSpinner text="Loading..." /></div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Pipelines</h1>

      <div className="bg-white border rounded p-4 space-y-3">
        <div className="text-lg font-medium">Create Pipeline</div>
        <input className="border rounded px-3 py-2 w-full" placeholder="Name" value={name} onChange={(e)=>setName(e.target.value)} />
        <input className="border rounded px-3 py-2 w-full" placeholder="Description" value={desc} onChange={(e)=>setDesc(e.target.value)} />
        <div className="space-y-2">
          {steps.map((s, i) => (
            <div key={i} className="flex items-center gap-2">
              <select className="border rounded px-2 py-1" value={s.employee_id} onChange={(e)=>setSteps(st => st.map((x, idx)=> idx===i ? { ...x, employee_id: e.target.value } : x))}>
                {employees.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
              </select>
              <input className="border rounded px-2 py-1 w-24" type="number" min={0} value={s.order} onChange={(e)=>setSteps(st => st.map((x, idx)=> idx===i ? { ...x, order: Number(e.target.value) } : x))} />
              <input className="border rounded px-2 py-1" placeholder="output_key" value={s.output_key} onChange={(e)=>setSteps(st => st.map((x, idx)=> idx===i ? { ...x, output_key: e.target.value } : x))} />
              <input className="border rounded px-2 py-1 flex-1" placeholder="input_map (key=ctxKey, comma-separated)" value={Object.entries(s.input_map).map(([k,v])=> `${k}:${v}`).join(",")} onChange={(e)=>{
                const val = e.target.value;
                const im: Record<string,string> = {};
                val.split(",").map(x=>x.trim()).filter(Boolean).forEach(pair=>{ const [k,v] = pair.split(":" ); if(k && v) im[k.trim()] = v.trim(); });
                setSteps(st => st.map((x, idx)=> idx===i ? { ...x, input_map: im } : x));
              }} />
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={addStep} className="px-3 py-2 border rounded">Add Step</button>
          <button onClick={savePipeline} className="px-3 py-2 bg-blue-600 text-white rounded">Save</button>
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-lg font-medium">Existing Pipelines</div>
        {pipelines.map(p => (
          <div key={p.id} className="bg-white border rounded p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">{p.name}</div>
                <div className="text-xs text-gray-500">{p.description}</div>
              </div>
              <button disabled={runningId===p.id} onClick={()=>void runPipeline(p.id)} className="px-3 py-2 bg-emerald-600 text-white rounded disabled:opacity-50">{runningId===p.id ? 'Running…' : 'Run'}</button>
            </div>
            <div className="mt-2 text-xs text-gray-600">Steps: {p.steps.map(s=> s.output_key).join(' → ')}</div>
          </div>
        ))}
        {runOutput && (
          <div className="bg-gray-50 border rounded p-3 text-xs">
            <div className="font-medium mb-1">Last Run Output</div>
            <pre>{JSON.stringify(runOutput, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
}


