import { LineChart as RLineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

type Props<T extends Record<string, unknown>> = {
  data: T[];
  x: keyof T & string;
  y: keyof T & string;
  color?: string;
};

export function LineChart<T extends Record<string, unknown>>({ data, x, y, color = "#3b82f6" }: Props<T>) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RLineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={x} />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey={y} stroke={color} strokeWidth={2} />
        </RLineChart>
      </ResponsiveContainer>
    </div>
  );
}


