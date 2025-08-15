export const dynamic = "force-static";
export const dynamicParams = false;
export function generateStaticParams() { return []; }

import TraceClient from "./trace-client";

export default function TraceDetailPage(props: any) {
  return <TraceClient id={props?.params?.id as string} />;
}


