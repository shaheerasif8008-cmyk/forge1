import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useSession } from '../components/SessionManager';
import config from '../config';

type Employee = { id: string; name: string; tenant_id: string; owner_user_id?: number; config: any };
type ModelInfo = { name: string; capabilities: string[]; available: boolean };
type TaskResult = {
  success: boolean; output: string; model_used: string; execution_time: number; metadata: Record<string, any>; error?: string | null
};

export default function EmployeeChatPage() {
  const { employeeId: routeEmployeeId } = useParams();
  const { token } = useSession();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [employeeId, setEmployeeId] = useState<string>(routeEmployeeId || '');
  const [, setEmployee] = useState<Employee | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [modelName, setModelName] = useState<string>('');
  const [tools, setTools] = useState<string[]>([]);
  const [enabledTools, setEnabledTools] = useState<Record<string, boolean>>({});
  const [messages, setMessages] = useState<Array<{ role: 'user'|'assistant'; text: string; result?: TaskResult }>>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  const headers = useMemo(() => ({
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }), [token]);

  useEffect(()=>{ endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  useEffect(() => {
    if (!token) return;
    // Load employees and models
    void (async () => {
      try {
        const [empRes, modRes] = await Promise.all([
          fetch(`${config.apiUrl}/api/v1/employees/`, { headers }),
          fetch(`${config.apiUrl}/api/v1/ai/models`, { headers }),
        ]);
        if (empRes.ok) {
          const emps = await empRes.json() as Employee[];
          setEmployees(emps);
          const eid = routeEmployeeId || emps[0]?.id || '';
          setEmployeeId(eid);
        }
        if (modRes.ok) {
          const modelsList = await modRes.json() as ModelInfo[];
          setModels(modelsList);
          if (modelsList.length && !modelName) setModelName(modelsList[0].name);
        }
      } catch (e: any) {
        setError(e.message || 'Failed to load initial data');
      }
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (!employeeId || !token) return;
    // Load employee config to populate tools
    void (async () => {
      try {
        const res = await fetch(`${config.apiUrl}/api/v1/employees/${employeeId}`, { headers });
        if (res.ok) {
          const emp = await res.json() as Employee;
          setEmployee(emp);
          const toolList = Array.isArray(emp.config?.tools) ? emp.config.tools.map((t: any)=> typeof t === 'string' ? t : (t.name || '')) : [];
          setTools(toolList);
          const initial: Record<string, boolean> = {};
          for (const t of toolList) initial[t] = true;
          setEnabledTools(initial);
        }
      } catch (e: any) {
        setError(e.message || 'Failed to load employee');
      }
    })();
  }, [employeeId, token, headers]);

  const sendMessage = async () => {
    if (!input.trim() || !employeeId) return;
    const userMsg = { role: 'user' as const, text: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    setError(null);
    try {
      // Build context deltas
      const toolsEnabled = Object.entries(enabledTools).filter(([,v])=>v).map(([k])=>k);
      const payload = {
        task: input.trim(),
        iterations: 1,
        context: {
          model_name: modelName,
          tools_enabled: toolsEnabled,
        },
      };
      const res = await fetch(`${config.apiUrl}/api/v1/employees/${employeeId}/run`, {
        method: 'POST', headers, body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(`Run failed (${res.status})`);
      const data = await res.json() as { results: TaskResult[] };
      const first = data.results?.[0];
      setMessages(prev => [...prev, { role: 'assistant', text: first?.output || '', result: first }]);
    } catch (e: any) {
      setError(e.message || 'Failed to send');
    } finally {
      setLoading(false);
    }
  };

  const onVoiceStub = () => {
    setError('Voice input is a stub; enable Whisper/ElevenLabs keys to activate.');
  };

  return (
    <div className="flex h-[calc(100vh-2rem)] gap-4 p-4">
      <div className="flex-1 flex flex-col border rounded">
        <div className="flex items-center gap-3 p-3 border-b bg-gray-50">
          <select className="border rounded px-2 py-1" value={employeeId} onChange={(e)=>setEmployeeId(e.target.value)}>
            {employees.map(emp => (<option key={emp.id} value={emp.id}>{emp.name}</option>))}
          </select>
          <select className="border rounded px-2 py-1" value={modelName} onChange={(e)=>setModelName(e.target.value)}>
            {models.map(m => (<option key={m.name} value={m.name}>{m.name}</option>))}
          </select>
          <div className="flex items-center gap-2 ml-4">
            {tools.map(t => (
              <label key={t} className="flex items-center gap-1 text-sm">
                <input type="checkbox" checked={!!enabledTools[t]} onChange={(e)=>setEnabledTools(prev=>({...prev, [t]: e.target.checked}))} />
                {t}
              </label>
            ))}
          </div>
          <button onClick={onVoiceStub} className="ml-auto px-2 py-1 border rounded">🎤 Voice (stub)</button>
        </div>
        <div className="flex-1 overflow-auto p-4 space-y-3">
          {messages.map((m, idx) => (
            <div key={idx} className={`max-w-3xl ${m.role==='user' ? 'ml-auto text-right' : ''}`}>
              <div className={`inline-block rounded px-3 py-2 ${m.role==='user' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>
                <div className="whitespace-pre-wrap">{m.text || m.result?.output}</div>
                {m.result && (
                  <div className="text-xs mt-1 opacity-80">
                    <span>tokens: {m.result.metadata?.tokens_used ?? 0}</span>
                    <span className="mx-2">•</span>
                    <span>latency: {Math.round((m.result.execution_time || 0) * 1000)} ms</span>
                    {m.result.metadata?.rag_used ? (<><span className="mx-2">•</span><span>RAG</span></>) : null}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
        {error && <div className="px-4 py-2 text-sm text-white bg-red-600">{error}</div>}
        <div className="p-3 border-t flex gap-2">
          <input className="flex-1 border rounded px-3 py-2" value={input} onChange={(e)=>setInput(e.target.value)} placeholder="Type a message..." />
          <button onClick={sendMessage} disabled={loading || !employeeId} className="px-3 py-2 rounded bg-blue-600 text-white disabled:bg-blue-400">
            {loading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>

      {/* Right rail timeline */}
      <div className="w-80 border rounded p-3 flex flex-col">
        <h3 className="font-semibold mb-2">Actions timeline</h3>
        <div className="flex-1 overflow-auto space-y-2 text-sm">
          {messages.filter(m=>m.result).map((m, idx) => (
            <div key={idx} className="border rounded p-2">
              <div className="font-medium">{m.result?.model_used || 'model'}</div>
              <div>tokens: {m.result?.metadata?.tokens_used ?? 0}</div>
              <div>latency: {Math.round((m.result?.execution_time || 0) * 1000)} ms</div>
              <div>rag: {m.result?.metadata?.rag_used ? 'yes' : 'no'}</div>
              <div>errors: {m.result?.error ? 'yes' : 'no'}</div>
              {/* Supervisor decisions, retries could be surfaced via future API hooks */}
            </div>
          ))}
          {!messages.some(m=>m.result) && <div className="text-gray-500">No actions yet</div>}
        </div>
      </div>
    </div>
  );
}


