export function BillingPage() {
	return (
		<div className="space-y-6">
			<h1 className="text-xl font-semibold tracking-tight">Billing & Subscription</h1>
			<div className="grid gap-4 md:grid-cols-3">
				{[
					{ name: 'Starter', price: '$49/mo', features: ['Up to 3 employees', 'Basic support'] },
					{ name: 'Pro', price: '$199/mo', features: ['Up to 25 employees', 'Priority support'] },
					{ name: 'Enterprise', price: 'Contact us', features: ['Unlimited', 'SLA & SSO'] },
				].map(p => (
					<div key={p.name} className="rounded-lg border p-4">
						<div className="text-sm text-muted-foreground">{p.name}</div>
						<div className="text-2xl font-semibold mt-2">{p.price}</div>
						<ul className="text-sm mt-3 space-y-1 list-disc pl-5">
							{p.features.map(f => <li key={f}>{f}</li>)}
						</ul>
						<button className="mt-4 w-full rounded-md border px-3 py-2 hover:bg-accent">Select</button>
					</div>
				))}
			</div>
			<div className="rounded-lg border p-4">
				<div className="text-sm text-muted-foreground mb-2">Stripe Customer Portal</div>
				<button className="rounded-md border px-3 py-2 hover:bg-accent">Manage Subscription</button>
			</div>
		</div>
	)
}
