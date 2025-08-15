"use client";

import { z } from "zod";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { SchemaForm } from "@/components/forms/SchemaForm";
import { useAuth } from "@/hooks/useAuth";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

export default function LoginPage() {
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);

  return (
    <div className="mx-auto mt-24 max-w-md">
      <Card>
        <CardHeader>
          <CardTitle>Welcome back to Forge1</CardTitle>
          <CardDescription>Sign in to deploy, monitor, and evolve your AI workforce.</CardDescription>
        </CardHeader>
        <CardContent>
          <SchemaForm
            schema={schema}
            onSubmit={async (values) => {
              try {
                setLoading(true);
                const v = values as { email: string; password: string };
                await login(v.email, v.password);
                window.location.href = "/dashboard";
              } catch (e) {
                const msg = (e as { message?: string })?.message ?? "Login failed";
                toast.error(msg);
              } finally {
                setLoading(false);
              }
            }}
            fields={[
              { name: "email", label: "Email", placeholder: "you@example.com" },
              { name: "password", label: "Password", type: "password" },
            ]}
            submitLabel={loading ? "Signing in…" : "Sign in"}
          />
          <div className="mt-4 flex justify-between text-sm">
            <Link href="/signup" className="underline">Create an account</Link>
            <Link href="/forgot" className="underline">Forgot password?</Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


