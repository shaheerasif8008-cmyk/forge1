import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import config from "../config";
import { useSession } from "../components/SessionManager";

type Template = { key: string; name: string; description: string };
// type Tool = { name: string; enabled: boolean };

export default function OnboardingWizardPage() {
  const { token } = useSession();
  const nav = useNavigate();
  const [step, setStep] = useState(1);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selected, setSelected] = useState<Template | null>(null);
  const [tools, setTools] = useState<Record<string, boolean>>({});
  const [docsUrl, setDocsUrl] = useState("");
  const [empName, setEmpName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const headers = useMemo(
    () => ({ "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) }),
    [token],
  );

  const loadTemplates = async () => {
    const r = await fetch(`${config.apiUrl}/api/v1/marketplace/templates`, { headers });
    if (r.ok) setTemplates(await r.json());
  };

  const loadTools = async () => {
    // Admin list is admin-only; for onboarding, present common tools as toggles
    setTools({ api_caller: true, web_scraper: true, csv_reader: false, slack_notifier: false });
  };

  const next = async () => {
    if (step === 1 && !templates.length) await loadTemplates();
    if (step === 2) await loadTools();
    setStep(step + 1);
  };

  const back = () => setStep(step - 1);

  const submit = async () => {
    setSubmitting(true);
    try {
      if (!selected) return;
      // Deploy template
      const deploy = await fetch(`${config.apiUrl}/api/v1/marketplace/templates/${selected.key}/deploy`, {
        method: "POST",
        headers,
        body: JSON.stringify({ name: empName || undefined }),
      });
      if (!deploy.ok) throw new Error("deploy_failed");
      const created = (await deploy.json()) as { id: string };
      // Connect tools: best-effort; in this scope, assume defaults
      // Upload docs
      if (docsUrl.trim()) {
        await fetch(`${config.apiUrl}/api/v1/rag/upload`, {
          method: "POST",
          headers,
          body: JSON.stringify({ items: [{ type: "url", url: docsUrl }] }),
        }).catch(() => {});
      }
      nav(`/employees/${created.id}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Onboarding</h1>
      {step === 1 && (
        <div className="space-y-3">
          <div className="text-sm text-gray-600">Choose a template</div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {templates.map((t) => (
              <button key={t.key} onClick={() => setSelected(t)} className={`border rounded p-3 text-left ${selected?.key === t.key ? "border-blue-600 ring-1 ring-blue-200" : ""}`}>
                <div className="font-medium">{t.name}</div>
                <div className="text-xs text-gray-600">{t.description}</div>
              </button>
            ))}
          </div>
          <div className="flex justify-end">
            <button onClick={next} className="px-4 py-2 bg-blue-600 text-white rounded">Next</button>
          </div>
        </div>
      )}
      {step === 2 && (
        <div className="space-y-3">
          <div className="text-sm text-gray-600">Connect tools</div>
          <div className="grid grid-cols-2 gap-3">
            {Object.keys(tools).map((k) => (
              <label key={k} className="flex items-center gap-2 border rounded p-2">
                <input type="checkbox" checked={!!tools[k]} onChange={(e) => setTools({ ...tools, [k]: e.target.checked })} />
                <span className="text-sm">{k}</span>
              </label>
            ))}
          </div>
          <div className="flex justify-between">
            <button onClick={back} className="px-4 py-2 border rounded">Back</button>
            <button onClick={next} className="px-4 py-2 bg-blue-600 text-white rounded">Next</button>
          </div>
        </div>
      )}
      {step === 3 && (
        <div className="space-y-3">
          <div className="text-sm text-gray-600">Upload docs (optional URL)</div>
          <input value={docsUrl} onChange={(e) => setDocsUrl(e.target.value)} placeholder="https://..." className="border rounded px-3 py-2 w-full" />
          <div className="flex justify-between">
            <button onClick={back} className="px-4 py-2 border rounded">Back</button>
            <button onClick={next} className="px-4 py-2 bg-blue-600 text-white rounded">Next</button>
          </div>
        </div>
      )}
      {step === 4 && (
        <div className="space-y-3">
          <div className="text-sm text-gray-600">Name your employee</div>
          <input value={empName} onChange={(e) => setEmpName(e.target.value)} placeholder="e.g., West Coast SDR" className="border rounded px-3 py-2 w-full" />
          <div className="flex justify-between">
            <button onClick={back} className="px-4 py-2 border rounded">Back</button>
            <button onClick={next} disabled={!empName.trim()} className="px-4 py-2 bg-blue-600 text-white rounded disabled:bg-blue-300">Next</button>
          </div>
        </div>
      )}
      {step === 5 && (
        <div className="space-y-3">
          <div className="text-sm text-gray-600">Test run (optional)</div>
          <div className="text-xs text-gray-500">We will validate connectivity during deployment.</div>
          <div className="flex justify-between">
            <button onClick={back} className="px-4 py-2 border rounded">Back</button>
            <button onClick={submit} disabled={submitting || !selected} className="px-4 py-2 bg-green-600 text-white rounded disabled:bg-green-300">{submitting ? "Deploying…" : "Go live"}</button>
          </div>
        </div>
      )}
    </div>
  );
}


