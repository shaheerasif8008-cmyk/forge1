"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { SmartTable } from "@/components/tables/SmartTable";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

export default function EmployeesPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  // selection reserved for future edit modal
  const [selected, setSelected] = useState<null | { id: string }>(null);

  type Employee = { id: string; name: string; status?: string };
  type Page<T> = { items: T[]; total: number; page: number; page_size: number };
  const employees = useQuery({
    queryKey: ["employees", q, page, pageSize],
    queryFn: async () => {
      const res = await api.get<Page<Employee>>("/api/v1/employees", { params: { q, page, page_size: pageSize } });
      return res.data;
    },
  });

  const runMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/api/v1/employees/${id}/run`);
    },
    onSuccess: () => {
      toast.success("Run triggered");
      qc.invalidateQueries({ queryKey: ["employees"] });
    },
  });

  const items = useMemo(() => employees.data?.items ?? [], [employees.data]);
  const total = employees.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Input placeholder="Search employees" onChange={(e) => setQ(e.target.value)} className="max-w-sm" />
        <div className="flex gap-2">
          <Button>Open Marketplace</Button>
          <Button>Create Employee</Button>
        </div>
      </div>

      <SmartTable
        data={items}
        loading={employees.isLoading}
        error={employees.error ? "Failed to load employees" : null}
        columns={[
          { key: "id", header: "ID" },
          { key: "name", header: "Name" },
          { key: "status", header: "Status" },
        ]}
        emptyText="No employees yet. Hire your first AI now."
        actions={(row) => (
          <div className="flex gap-2">
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="secondary">Run</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Run Employee</DialogTitle>
                </DialogHeader>
                <div className="flex justify-end">
                  <Button onClick={() => runMutation.mutate(String((row as Employee).id))}>
                    Run Now
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
            <Button variant="outline">Pause</Button>
            <Button variant="outline">Edit</Button>
          </div>
        )}
        pagination={{
          page,
          pageSize,
          total,
          onPageChange: (p: number) => setPage(p),
          onPageSizeChange: (ps: number) => { setPageSize(ps); setPage(1); },
        }}
      />
    </div>
  );
}


