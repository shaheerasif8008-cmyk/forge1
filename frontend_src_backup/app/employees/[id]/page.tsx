export const dynamic = "force-static";
export const dynamicParams = false;
export function generateStaticParams() { return []; }

import EmployeeClient from "./employee-client";

export default function EmployeeDetailPage(props: any) {
  return <EmployeeClient id={props?.params?.id as string} />;
}


