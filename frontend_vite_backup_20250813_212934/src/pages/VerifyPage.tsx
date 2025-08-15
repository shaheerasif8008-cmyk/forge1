import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import config from "../config";

export default function VerifyPage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [message, setMessage] = useState("Verifying...");

  useEffect(() => {
    const run = async () => {
      try {
        const resp = await fetch(`${config.apiUrl}/api/v1/auth/verify-email`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        if (resp.ok) setMessage("Email verified. You can close this tab and log in.");
        else setMessage("Invalid or expired link.");
      } catch {
        setMessage("Network error");
      }
    };
    if (token) void run();
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="bg-white p-6 rounded shadow">{message}</div>
    </div>
  );
}


