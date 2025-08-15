import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
	return (
		<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
			{Array.from({ length: 4 }).map((_, i) => (
				<Card key={i} className="shadow-card">
					<CardContent className="p-4">
						<Skeleton className="h-6 w-40" />
						<Skeleton className="h-4 w-24 mt-2" />
					</CardContent>
				</Card>
			))}
		</div>
	);
}