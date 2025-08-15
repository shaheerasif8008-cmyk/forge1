import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ResponsiveContainer, AreaChart, Area } from "recharts";

type KpiCardProps = {
  title: string;
  value?: string | number;
  loading?: boolean;
  data?: Array<{ x: number | string; y: number }>;
};

export function KpiCard({ title, value, loading, data = [] }: KpiCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-6 w-28" />
        ) : (
          <div className="text-2xl font-semibold">{value}</div>
        )}
        <div className="mt-3 h-16">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ left: 0, right: 0, top: 0, bottom: 0 }}>
              <Area type="monotone" dataKey="y" stroke="#3b82f6" fill="#3b82f633" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}


