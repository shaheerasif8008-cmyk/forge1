"use client";

import { useAuth } from "@/lib/auth";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient, type EmployeeIn, type EmployeeOut } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import toast from "react-hot-toast";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";

const schema = z.object({
  name: z.string().min(1, "Required"),
  role_name: z.string().min(1, "Required"),
  description: z.string().min(1, "Required"),
});

type FormValues = z.infer<typeof schema>;

export default function EmployeesPage() {
  const { loading } = useAuth();
  const qc = useQueryClient();
  const { data: employees, isLoading } = useQuery({
    queryKey: ["employees"],
    queryFn: () => apiClient.listEmployees(),
    enabled: !loading,
  });

  const createMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const payload: EmployeeIn = { ...values, tools: [] };
      return apiClient.createEmployee(payload);
    },
    onSuccess: (emp) => {
      toast.success(`Created ${emp.name}`);
      qc.invalidateQueries({ queryKey: ["employees"] });
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail
        || (e as { message?: string }).message
        || "Create failed";
      toast.error(detail);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (employeeId: string) => apiClient.deleteEmployee(employeeId),
    onSuccess: () => {
      toast.success("Deleted");
      qc.invalidateQueries({ queryKey: ["employees"] });
    },
    onError: () => toast.error("Delete failed"),
  });

  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { name: "", role_name: "", description: "" } });

  const onSubmit = (values: FormValues) => {
    createMutation.mutate(values);
    form.reset();
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Employees</h1>
      </div>

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle>Create Employee</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={form.handleSubmit(onSubmit)} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="name">Name</Label>
              <Input id="name" {...form.register("name")} placeholder="Acme Agent" />
              {form.formState.errors.name && (
                <p className="text-danger text-xs mt-1">{form.formState.errors.name.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="role_name">Role</Label>
              <Input id="role_name" {...form.register("role_name")} placeholder="research_assistant" />
              {form.formState.errors.role_name && (
                <p className="text-danger text-xs mt-1">{form.formState.errors.role_name.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="description">Description</Label>
              <Input id="description" {...form.register("description")} placeholder="Helps with research" />
              {form.formState.errors.description && (
                <p className="text-danger text-xs mt-1">{form.formState.errors.description.message}</p>
              )}
            </div>
            <div className="md:col-span-3">
              <Button type="submit" disabled={createMutation.isPending}>Create</Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle>All Employees</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !employees?.length ? (
            <div className="text-sm text-muted-foreground">No employees yet</div>
          ) : (
            <div className="space-y-2">
              {employees.map((e: EmployeeOut) => (
                <div key={e.id} className="flex items-center justify-between border rounded-md p-3">
                  <div>
                    <div className="font-medium">
                      <Link href={`/employees/${e.id}`} className="underline hover:no-underline">{e.name}</Link>
                    </div>
                    <div className="text-xs text-muted-foreground">{e.id}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      onClick={() => navigator.clipboard.writeText(e.id).then(() => toast.success("Copied ID"))}
                    >Copy ID</Button>
                    <Button variant="destructive" onClick={() => deleteMutation.mutate(e.id)}>Delete</Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
