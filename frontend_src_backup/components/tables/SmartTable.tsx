import { useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

type Column<T> = {
  key: keyof T & string;
  header: string;
  render?: (row: T) => React.ReactNode;
};

type SmartTableProps<T> = {
  data?: T[];
  loading?: boolean;
  error?: string | null;
  columns: Column<T>[];
  onSearch?: (q: string) => void;
  actions?: (row: T) => React.ReactNode;
  emptyText?: string;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
    onPageSizeChange?: (pageSize: number) => void;
  };
};

export function SmartTable<T extends Record<string, unknown>>({
  data,
  loading,
  error,
  columns,
  onSearch,
  actions,
  emptyText = "No data",
  pagination,
}: SmartTableProps<T>) {
  const rows = useMemo(() => data ?? [], [data]);

  return (
    <div className="space-y-3">
      {onSearch ? <Input placeholder="Search" onChange={(e) => onSearch(e.target.value)} /> : null}

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((c) => (
                <TableHead key={c.key}>{c.header}</TableHead>
              ))}
              {actions ? <TableHead className="w-[120px]">Actions</TableHead> : null}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {columns.map((c) => (
                    <TableCell key={c.key}>
                      <Skeleton className="h-5 w-full" />
                    </TableCell>
                  ))}
                  {actions ? (
                    <TableCell>
                      <Skeleton className="h-5 w-24" />
                    </TableCell>
                  ) : null}
                </TableRow>
              ))
            ) : error ? (
              <TableRow>
                <TableCell colSpan={columns.length + (actions ? 1 : 0)} className="text-sm text-destructive">
                  {error}
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length + (actions ? 1 : 0)} className="text-sm text-muted-foreground">
                  {emptyText}
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row, i) => (
                <TableRow key={i}>
                  {columns.map((c) => (
                    <TableCell key={c.key}>{c.render ? c.render(row) : String(row[c.key] ?? "")}</TableCell>
                  ))}
                  {actions ? <TableCell>{actions(row)}</TableCell> : null}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      {pagination ? (
        <div className="flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            Page {pagination.page} of {Math.max(1, Math.ceil(pagination.total / Math.max(1, pagination.pageSize)))}
          </div>
          <div className="flex items-center gap-2">
            <button
              className="rounded border px-2 py-1 text-sm"
              onClick={() => pagination.onPageChange(Math.max(1, pagination.page - 1))}
              disabled={pagination.page <= 1}
            >
              Prev
            </button>
            <button
              className="rounded border px-2 py-1 text-sm"
              onClick={() => pagination.onPageChange(pagination.page + 1)}
              disabled={pagination.page * pagination.pageSize >= pagination.total}
            >
              Next
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}


