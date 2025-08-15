"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

export default function TestingLayout({ children }: { children: React.ReactNode }) {
	const pathname = usePathname();
	const tabs = [
		{ href: "/testing/suites", label: "Suites" },
		{ href: "/testing/monitor", label: "Live Monitor" },
		{ href: "/testing/history", label: "History" },
		{ href: "/testing/artifacts", label: "Artifacts" },
	];
	return (
		<div className="min-h-screen">
			<div className="sticky top-0 z-30 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
				<div className="mx-auto max-w-7xl px-6 py-3 flex items-center justify-between">
					<h2 className="text-xl font-semibold">Testing</h2>
					<nav className="flex items-center gap-4">
						{tabs.map((t) => (
							<Link key={t.href} href={t.href} className={clsx("px-2 py-1 rounded-md text-sm", pathname?.startsWith(t.href) ? "bg-primary text-white" : "text-muted-foreground hover:text-foreground hover:bg-muted")}>{t.label}</Link>
						))}
					</nav>
				</div>
			</div>
			<div className="mx-auto max-w-7xl px-6 py-6">{children}</div>
		</div>
	);
}