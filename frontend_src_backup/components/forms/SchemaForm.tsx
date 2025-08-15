/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, type UseFormReturn } from "react-hook-form";
import { z } from "zod";
import { Form, FormField } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

type SchemaFormProps = {
  schema: z.ZodTypeAny;
  defaultValues?: Record<string, any>;
  onSubmit: (values: Record<string, any>) => void | Promise<void>;
  fields: Array<{ name: string; label: string; placeholder?: string; type?: string }>;
  submitLabel?: string;
};

export function SchemaForm({ schema, defaultValues, onSubmit, fields, submitLabel = "Submit" }: SchemaFormProps) {
  const form = useForm<any>({ resolver: zodResolver(schema as any), defaultValues }) as UseFormReturn<any>;

  return (
    <Form form={form} onSubmit={onSubmit}>
      {fields.map((f) => (
        <FormField key={f.name} form={form} name={f.name} label={f.label}>
          {(field) => <Input {...field} id={f.name} placeholder={f.placeholder} type={f.type ?? "text"} />}
        </FormField>
      ))}
      <Button type="submit">{submitLabel}</Button>
    </Form>
  );
}


