"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function BillingPage() {
  const usage = useQuery({ queryKey: ["billing:usage"], queryFn: async () => (await api.get("/api/v1/billing/usage")).data });
  const invoices = useQuery({ queryKey: ["billing:invoices"], queryFn: async () => (await api.get("/api/v1/billing/invoices")).data });

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader><CardTitle>Usage</CardTitle></CardHeader>
        <CardContent><pre className="text-xs">{JSON.stringify(usage.data ?? {}, null, 2)}</pre></CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Invoices</CardTitle></CardHeader>
        <CardContent><pre className="text-xs">{JSON.stringify(invoices.data ?? [], null, 2)}</pre></CardContent>
      </Card>
    </div>
  );
}


