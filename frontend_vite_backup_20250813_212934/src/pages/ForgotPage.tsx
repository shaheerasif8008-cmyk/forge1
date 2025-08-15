import { useState } from "react";
import config from "../config";
import { useToast } from "../components/Toast";

export default function ForgotPage() {
  const { push } = useToast();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const resp = await fetch(`${config.apiUrl}/api/v1/auth/request-password-reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (resp.ok) push("Check your email for a reset link", "success");
      else push("Failed to request reset", "error");
    } catch {
      push("Network error", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={onSubmit} className="bg-white p-6 rounded shadow w-full max-w-sm space-y-4">
        <h1 className="text-xl font-semibold">Forgot password</h1>
        <input className="w-full border rounded px-3 py-2" placeholder="Email" type="email" value={email} onChange={(e)=>setEmail(e.target.value)} required />
        <button disabled={loading} className="bg-blue-600 text-white rounded py-2">{loading ? "Sending..." : "Send reset link"}</button>
      </form>
    </div>
  );
}


