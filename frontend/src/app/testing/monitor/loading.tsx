import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
	return (
		<div className="space-y-6">
			<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
				{Array.from({ length: 3 }).map((_, i) => (
					<Card key={i} className="shadow-card"><CardContent className="p-4"><Skeleton className="h-10 w-24" /></CardContent></Card>
				))}
			</div>
			<Card className="shadow-card"><CardContent className="p-6"><Skeleton className="h-[40vh] w-full" /></CardContent></Card>
		</div>
	);
}