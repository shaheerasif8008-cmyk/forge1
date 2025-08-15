import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import config from "../config";
import { useSession } from "../components/SessionManager";
import { useToast } from "../components/Toast";

const templates = [
  { key: 'sales_agent', name: 'Sales Agent', description: 'Outreach, follow-up, CRM hygiene', tools: ['api_caller', 'web_scraper'] },
  { key: 'research_assistant', name: 'Research Assistant', description: 'Summarize docs, extract insights', tools: ['document_summarizer', 'keyword_extractor'] },
  { key: 'customer_support', name: 'Customer Support', description: 'Answer questions, escalate issues', tools: ['api_caller', 'file_parser'] },
];

export default function EmployeeWizardPage() {
  const { token } = useSession();
  const { push } = useToast();
  const nav = useNavigate();
  const [step, setStep] = useState(1);
  const [selected, setSelected] = useState(templates[0]);
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const previewConfig = useMemo(()=> ({
    role: { name: selected.name, description: selected.description },
    tools: selected.tools,
    rag: { enabled: true, top_k: 5 },
    memory: { short_term: true, long_term: true },
  }), [selected]);

  const headers = useMemo(()=> ({ 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }), [token]);

  const onCreate = async () => {
    setSubmitting(true);
    try {
      const res = await fetch(`${config.apiUrl}/api/v1/employees/`, { method: 'POST', headers, body: JSON.stringify({ name, role_name: selected.name, description: selected.description, tools: selected.tools }) });
      if (!res.ok) throw new Error(`Create failed (${res.status})`);
      const created = await res.json() as { id: string };
      push('Employee created', 'success');
      nav(`/employees/${created.id}`);
    } catch (e: any) {
      push(e.message || 'Create failed', 'error');
    } finally { setSubmitting(false); }
  };

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-semibold">New Employee</h1>
      {step === 1 && (
        <div className="space-y-3">
          <div className="text-sm text-gray-600">Pick a template</div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {templates.map((t) => (
              <button key={t.key} onClick={()=> setSelected(t)} className={`border rounded p-3 text-left ${selected.key === t.key ? 'border-blue-600 ring-1 ring-blue-200' : ''}`}>
                <div className="font-medium">{t.name}</div>
                <div className="text-xs text-gray-600">{t.description}</div>
              </button>
            ))}
          </div>
          <div className="flex justify-end">
            <button onClick={()=> setStep(2)} className="px-4 py-2 bg-blue-600 text-white rounded">Next</button>
          </div>
        </div>
      )}
      {step === 2 && (
        <div className="space-y-3">
          <div className="text-sm text-gray-600">Name your employee</div>
          <input value={name} onChange={(e)=> setName(e.target.value)} placeholder="e.g., West Coast SDR" className="border rounded px-3 py-2 w-full" />
          <div className="flex justify-between">
            <button onClick={()=> setStep(1)} className="px-4 py-2 border rounded">Back</button>
            <button disabled={!name.trim()} onClick={()=> setStep(3)} className="px-4 py-2 bg-blue-600 text-white rounded disabled:bg-blue-300">Next</button>
          </div>
        </div>
      )}
      {step === 3 && (
        <div className="space-y-3">
          <div className="text-sm text-gray-600">Confirm configuration</div>
          <pre className="bg-gray-50 border rounded p-3 text-sm whitespace-pre-wrap">{JSON.stringify(previewConfig, null, 2)}</pre>
          <div className="flex justify-between">
            <button onClick={()=> setStep(2)} className="px-4 py-2 border rounded">Back</button>
            <button onClick={onCreate} disabled={submitting} className="px-4 py-2 bg-green-600 text-white rounded disabled:bg-green-300">{submitting ? 'Creating...' : 'Create'}</button>
          </div>
        </div>
      )}
    </div>
  );
}


