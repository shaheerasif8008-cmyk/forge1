import { useState } from "react";
import type { FormEvent } from "react";
import { useSession } from "../components/SessionManager";
import config from "../config";

async function loginRequest(
  email: string,
  password: string,
): Promise<string | null> {
  const params = new URLSearchParams();
  params.set("username", email); // Backend expects 'username' field
  params.set("password", password);

  try {
    const resp = await fetch(`${config.apiUrl}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: params.toString(),
    });
    if (!resp.ok) return null;
    const data = (await resp.json()) as { access_token: string };
    return data.access_token;
  } catch {
    return null;
  }
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useSession();

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const token = await loginRequest(email, password);
      if (!token) {
        setError("Invalid credentials");
        return;
      }
      login(token);
      // Navigation will be handled automatically by the router
    } catch (error) {
      setError("An unexpected error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm space-y-4 bg-white p-6 rounded shadow"
      >
        <h1 className="text-2xl font-semibold">Forge 1 Login</h1>
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <div className="space-y-1">
          <label className="block text-sm font-medium">Email</label>
          <input
            type="email"
            className="w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-500"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>
        <div className="space-y-1">
          <label className="block text-sm font-medium">Password</label>
          <input
            type="password"
            className="w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-500"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>
        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition"
        >
          {isLoading ? "Signing In..." : "Sign In"}
        </button>
        <p className="text-xs text-gray-500 text-center">
          Use any email with password: admin
        </p>
      </form>
    </div>
  );
}
