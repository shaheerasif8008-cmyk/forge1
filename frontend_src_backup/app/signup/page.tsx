"use client";

import { z } from "zod";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SchemaForm } from "@/components/forms/SchemaForm";
import { useAuth } from "@/hooks/useAuth";
import Link from "next/link";
import { toast } from "sonner";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
});

export default function SignupPage() {
  const { signup } = useAuth();

  return (
    <div className="mx-auto mt-24 max-w-md">
      <Card>
        <CardHeader>
          <CardTitle>Create your account</CardTitle>
        </CardHeader>
        <CardContent>
          <SchemaForm
            schema={schema}
            onSubmit={async (values) => {
              try {
                const v = values as { email: string; password: string };
                await signup(v.email, v.password);
                toast.success("Account created. Please sign in.");
                window.location.href = "/login";
              } catch (e) {
                const msg = (e as { message?: string })?.message ?? "Signup failed";
                toast.error(msg);
              }
            }}
            fields={[
              { name: "email", label: "Email", placeholder: "you@example.com" },
              { name: "password", label: "Password", type: "password" },
            ]}
            submitLabel="Create account"
          />
          <div className="mt-4 text-sm">
            <Link href="/login" className="underline">Back to login</Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


