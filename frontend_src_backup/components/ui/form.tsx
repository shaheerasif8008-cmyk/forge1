import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";
import {
  Controller,
  type FieldValues,
  type Path,
  type UseFormReturn,
  type ControllerRenderProps,
} from "react-hook-form";
import { cn } from "@/lib/utils";

const Label = LabelPrimitive.Root;

type FormProps<T extends FieldValues> = React.HTMLAttributes<HTMLFormElement> & {
  form: UseFormReturn<T>;
  onSubmit: (data: T) => void;
  children: React.ReactNode;
};

export function Form<T extends FieldValues>({ form, onSubmit, className, children, ...props }: FormProps<T>) {
  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      className={cn("space-y-4", className)}
      {...props}
    >
      {children}
    </form>
  );
}

type FormFieldProps<T extends FieldValues, TName extends Path<T> = Path<T>> = {
  form: UseFormReturn<T>;
  name: TName;
  label?: string;
  children: (field: ControllerRenderProps<T, TName>) => React.ReactNode;
};

export function FormField<T extends FieldValues, TName extends Path<T>>({
  form,
  name,
  label,
  children,
}: FormFieldProps<T, TName>) {
  return (
    <Controller
      control={form.control}
      name={name}
      render={({ field }) => (
        <div className="grid gap-2">
          {label ? (
            <Label htmlFor={name} className="text-sm font-medium">
              {label}
            </Label>
          ) : null}
          {children(field)}
          {(form.formState.errors as Record<string, { message?: string }>)[
            name as string
          ]?.message ? (
            <p className="text-sm text-destructive">
              {
                (form.formState.errors as Record<string, { message?: string }>)[
                  name as string
                ]?.message
              }
            </p>
          ) : null}
        </div>
      )}
    />
  );
}

export { Label };


