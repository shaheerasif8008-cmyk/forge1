import { useState } from "react";
import config from "../config";
import { useToast } from "../components/Toast";

export default function RegisterPage() {
  const { push } = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const resp = await fetch(`${config.apiUrl}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, tenant_name: tenantName || null }),
      });
      if (resp.ok) {
        push("Registration successful. Check your email to verify.", "success");
      } else {
        const data = await resp.json().catch(() => ({}));
        push(data.detail || "Registration failed", "error");
      }
    } catch {
      push("Network error", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen">
      <form onSubmit={onSubmit} className="w-full max-w-sm space-y-4 bg-white p-6 rounded shadow">
        <h1 className="text-2xl font-semibold">Create your account</h1>
        <div className="space-y-1">
          <label className="block text-sm font-medium">Email</label>
          <input type="email" className="w-full border rounded px-3 py-2" value={email} onChange={(e)=>setEmail(e.target.value)} required />
        </div>
        <div className="space-y-1">
          <label className="block text-sm font-medium">Password</label>
          <input type="password" className="w-full border rounded px-3 py-2" value={password} onChange={(e)=>setPassword(e.target.value)} required />
          <p className="text-xs text-gray-500">Use at least 12 chars with a mix of cases, digits, symbols.</p>
        </div>
        <div className="space-y-1">
          <label className="block text-sm font-medium">Tenant (optional)</label>
          <input type="text" className="w-full border rounded px-3 py-2" value={tenantName} onChange={(e)=>setTenantName(e.target.value)} placeholder="Your org name" />
        </div>
        <button type="submit" disabled={loading} className="w-full bg-blue-600 text-white py-2 rounded">
          {loading ? "Creating..." : "Create account"}
        </button>
      </form>
    </div>
  );
}


