import { BarChart as RBarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

type Props<T extends Record<string, unknown>> = {
  data: T[];
  x: keyof T & string;
  y: keyof T & string;
  color?: string;
};

export function BarChart<T extends Record<string, unknown>>({ data, x, y, color = "#10b981" }: Props<T>) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RBarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={x} />
          <YAxis />
          <Tooltip />
          <Bar dataKey={y} fill={color} />
        </RBarChart>
      </ResponsiveContainer>
    </div>
  );
}


