"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { SchemaForm } from "@/components/forms/SchemaForm";
import { z } from "zod";

const schema = z.object({ name: z.string().min(1) });

export default function SettingsPage() {
  const qc = useQueryClient();
  const tenant = useQuery({ queryKey: ["tenant"], queryFn: async () => (await api.get("/api/v1/tenant")).data });
  const save = useMutation({
    mutationFn: async (values: { name: string }) => (await api.patch("/api/v1/tenant", values)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tenant"] }),
  });

  return (
    <div className="max-w-md">
      <SchemaForm
        schema={schema}
        defaultValues={{ name: tenant.data?.name ?? "" }}
        onSubmit={(v) => save.mutate(v as { name: string })}
        fields={[{ name: "name", label: "Tenant Name" }]}
        submitLabel="Save"
      />
    </div>
  );
}


