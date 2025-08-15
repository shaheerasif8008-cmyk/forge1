import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
	return (
		<div className="space-y-6">
			<Card className="shadow-card"><CardContent className="p-6"><Skeleton className="h-8 w-64" /></CardContent></Card>
			<Card className="shadow-card"><CardContent className="p-6"><Skeleton className="h-[50vh] w-full" /></CardContent></Card>
		</div>
	);
}