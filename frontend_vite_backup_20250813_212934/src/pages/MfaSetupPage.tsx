import { useEffect, useState } from "react";
import config from "../config";
import { useSession } from "../components/SessionManager";
import { useToast } from "../components/Toast";

export default function MfaSetupPage() {
  const { token } = useSession();
  const { push } = useToast();
  const [secret, setSecret] = useState("");
  const [otpauth, setOtpauth] = useState("");
  const [codes, setCodes] = useState<string[]>([]);
  const [code, setCode] = useState("");

  useEffect(() => {
    const run = async () => {
      const resp = await fetch(`${config.apiUrl}/api/v1/auth/mfa/setup`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) return;
      const data = (await resp.json()) as { secret: string; otpauth_url: string; recovery_codes: string[] };
      setSecret(data.secret);
      setOtpauth(data.otpauth_url);
      setCodes(data.recovery_codes);
    };
    if (token) void run();
  }, [token]);

  const verify = async (e: React.FormEvent) => {
    e.preventDefault();
    const resp = await fetch(`${config.apiUrl}/api/v1/auth/mfa/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ code }),
    });
    if (resp.ok) push("MFA enabled", "success"); else push("Invalid code", "error");
  };

  return (
    <div className="p-6 space-y-4 max-w-xl">
      <h1 className="text-xl font-semibold">Set up MFA</h1>
      <p className="text-sm">Secret: <code>{secret}</code></p>
      <p className="text-sm break-all">OTPAuth URL: <code>{otpauth}</code></p>
      <div>
        <h2 className="font-medium">Recovery codes</h2>
        <ul className="list-disc ml-6 text-sm">
          {codes.map((c)=> <li key={c}><code>{c}</code></li>)}
        </ul>
      </div>
      <form onSubmit={verify} className="space-x-2">
        <input className="border rounded px-3 py-2" placeholder="Enter 6-digit code" value={code} onChange={(e)=>setCode(e.target.value)} />
        <button className="bg-blue-600 text-white rounded px-3 py-2">Verify</button>
      </form>
    </div>
  );
}


