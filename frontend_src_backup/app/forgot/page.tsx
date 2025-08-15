"use client";

import { z } from "zod";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SchemaForm } from "@/components/forms/SchemaForm";
import { useAuth } from "@/hooks/useAuth";
import Link from "next/link";
import { toast } from "sonner";

const schema = z.object({
  email: z.string().email(),
});

export default function ForgotPage() {
  const { forgot } = useAuth();

  return (
    <div className="mx-auto mt-24 max-w-md">
      <Card>
        <CardHeader>
          <CardTitle>Reset password</CardTitle>
        </CardHeader>
        <CardContent>
          <SchemaForm
            schema={schema}
            onSubmit={async (values) => {
              try {
                await forgot((values as { email: string }).email);
                toast.success("If your email exists, you will receive instructions.");
              } catch (e) {
                const msg = (e as { message?: string })?.message ?? "Request failed";
                toast.error(msg);
              }
            }}
            fields={[{ name: "email", label: "Email", placeholder: "you@example.com" }]}
            submitLabel="Send reset instructions"
          />
          <div className="mt-4 text-sm">
            <Link href="/login" className="underline">Back to login</Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


