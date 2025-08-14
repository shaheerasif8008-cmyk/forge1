import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import config from "../config";
import { useToast } from "../components/Toast";

export default function ResetPage() {
  const { push } = useToast();
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const resp = await fetch(`${config.apiUrl}/api/v1/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      if (resp.ok) push("Password reset successful. You can log in.", "success");
      else push("Reset failed", "error");
    } catch {
      push("Network error", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={onSubmit} className="bg-white p-6 rounded shadow w-full max-w-sm space-y-4">
        <h1 className="text-xl font-semibold">Reset password</h1>
        <input className="w-full border rounded px-3 py-2" placeholder="New password" type="password" value={password} onChange={(e)=>setPassword(e.target.value)} required />
        <button disabled={loading} className="bg-blue-600 text-white rounded py-2">{loading ? "Resetting..." : "Reset password"}</button>
      </form>
    </div>
  );
}


