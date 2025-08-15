export default function DocsSite() {
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <section>
        <h1 className="text-3xl font-semibold mb-2">Forge 1</h1>
        <p className="text-gray-600">AI Orchestration Platform</p>
      </section>

      <section>
        <h2 className="text-2xl font-semibold mb-2">Overview</h2>
        <p className="text-gray-700">Modern FastAPI + React platform for building and operating AI employees. Multi-tenant, secure, and observable.</p>
      </section>

      <section>
        <h2 className="text-2xl font-semibold mb-2">Quickstart</h2>
        <div className="space-y-3">
          <div>
            <div className="text-sm font-medium mb-1">cURL</div>
            <pre className="bg-gray-900 text-gray-100 text-sm p-3 rounded overflow-auto"><code>{`curl -X POST "$API_URL/api/v1/auth/login" -d 'username=you@example.com&password=admin'
export TOKEN=... # from response
curl -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/employees/"`}</code></pre>
          </div>
          <div>
            <div className="text-sm font-medium mb-1">Node</div>
            <pre className="bg-gray-900 text-gray-100 text-sm p-3 rounded overflow-auto"><code>{`import fetch from 'node-fetch';
const res = await fetch(process.env.API_URL + '/api/v1/ai/execute', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + process.env.TOKEN },
  body: JSON.stringify({ task: 'Say hello' })
});
console.log(await res.json());`}</code></pre>
          </div>
          <div>
            <div className="text-sm font-medium mb-1">Python</div>
            <pre className="bg-gray-900 text-gray-100 text-sm p-3 rounded overflow-auto"><code>{`import os, requests
r = requests.post(os.environ['API_URL'] + '/api/v1/ai/execute',
  headers={'Authorization': 'Bearer ' + os.environ['TOKEN']},
  json={'task': 'Say hello'})
print(r.json())`}</code></pre>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-2xl font-semibold mb-2">Templates Catalog</h2>
        <ul className="list-disc ml-5 text-gray-700">
          <li>Sales Agent – outreach, follow-up, CRM hygiene</li>
          <li>Research Assistant – summarize docs, extract insights</li>
          <li>Customer Support – answer questions, escalate when needed</li>
        </ul>
      </section>

      <section>
        <h2 className="text-2xl font-semibold mb-2">EaaS API Reference</h2>
        <p className="text-gray-700 mb-2">Invoke an Employee using a one-time key:</p>
        <pre className="bg-gray-900 text-gray-100 text-sm p-3 rounded overflow-auto"><code>{`# Create a key (admin)
POST /api/v1/admin/keys/employees/{employee_id}/keys -> { prefix, secret_once, key_id }
# Invoke (no JWT):
POST /v1/employees/{employee_id}/invoke
Headers: Employee-Key: EK_<prefix>.<secret>
Body: { input: string, context?: object, tools?: string[], stream?: boolean }
# Response: { trace_id, output, tokens_used, latency_ms, model_used, tool_calls? }`}</code></pre>
      </section>

      <section>
        <h2 className="text-2xl font-semibold mb-2">Pricing</h2>
        <p className="text-gray-700">Starter, Team, Enterprise. Includes: employees, logs, metrics, export/BYOC. Contact us for pricing.</p>
      </section>

      <section>
        <h2 className="text-2xl font-semibold mb-2">Terms & Privacy</h2>
        <p className="text-gray-700 text-sm">By using Forge 1, you agree to reasonable terms. PII is processed according to our Privacy Policy. GDPR erase available via admin APIs.</p>
      </section>

      <section>
        <h2 className="text-2xl font-semibold mb-2">Runbook</h2>
        <ul className="list-disc ml-5 text-gray-700">
          <li>Deploy: docker compose prod profile or ACA deploy scripts.</li>
          <li>Rollback: POST /api/v1/admin/release/rollback (or runbook command).</li>
          <li>Key rotate: POST /api/v1/admin/keys/employees/{'{id}'}/keys then revoke old.</li>
          <li>Quota raise: PATCH /api/v1/admin/keys/employee/{'{id}'}/quota.</li>
          <li>Incident: capture trace_id, check /health/ready, logs, metrics, rollback if needed.</li>
        </ul>
      </section>
    </div>
  );
}


