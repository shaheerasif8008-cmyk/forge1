import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
	return (
		<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{Array.from({ length: 6 }).map((_, i) => (
				<Card key={i} className="shadow-card">
					<CardHeader>
						<Skeleton className="h-5 w-32" />
						<Skeleton className="h-4 w-48" />
					</CardHeader>
					<CardContent>
						<Skeleton className="h-10 w-full" />
					</CardContent>
				</Card>
			))}
		</div>
	);
}