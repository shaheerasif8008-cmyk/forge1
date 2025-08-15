"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { SmartTable } from "@/components/tables/SmartTable";

export default function KeysPage() {
  const qc = useQueryClient();
  const keys = useQuery({ queryKey: ["keys"], queryFn: async () => (await api.get("/api/v1/keys")).data });

  const createKey = useMutation({
    mutationFn: async () => (await api.post("/api/v1/keys")).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["keys"] }),
  });
  const deleteKey = useMutation({
    mutationFn: async (id: string) => (await api.delete(`/api/v1/keys`, { data: { id } })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["keys"] }),
  });

  return (
    <div className="space-y-3">
      <div className="flex justify-end"><Button onClick={() => createKey.mutate()}>Create</Button></div>
      <SmartTable<{ id: string; created_at?: string }>
        data={keys.data as { id: string; created_at?: string }[]}
        loading={keys.isLoading}
        error={keys.error ? "Failed to load keys" : null}
        columns={[{ key: "id", header: "ID" }, { key: "created_at", header: "Created" }]}
        emptyText="No data"
        actions={(row: { id: string }) => (
          <Button variant="destructive" onClick={() => deleteKey.mutate(String(row.id))}>Delete</Button>
        )}
      />
    </div>
  );
}


