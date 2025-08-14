import { useState } from "react";
import config from "../config";
import { useSession } from "../components/SessionManager";
import { useToast } from "../components/Toast";

export default function MfaVerifyPage() {
  const { token } = useSession();
  const { push } = useToast();
  const [code, setCode] = useState("");

  const verify = async (e: React.FormEvent) => {
    e.preventDefault();
    const resp = await fetch(`${config.apiUrl}/api/v1/auth/mfa/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ code }),
    });
    if (resp.ok) push("MFA verified", "success"); else push("Invalid code", "error");
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={verify} className="bg-white p-6 rounded shadow w-full max-w-sm space-y-4">
        <h1 className="text-xl font-semibold">Verify MFA</h1>
        <input className="w-full border rounded px-3 py-2" placeholder="Code" value={code} onChange={(e)=>setCode(e.target.value)} />
        <button className="bg-blue-600 text-white rounded py-2">Verify</button>
      </form>
    </div>
  );
}


