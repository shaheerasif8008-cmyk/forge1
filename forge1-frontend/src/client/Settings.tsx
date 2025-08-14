export function SettingsPage() {
	return (
		<div className="space-y-4">
			<h2 className="text-lg font-semibold">Settings</h2>
			<div className="p-4 border rounded-lg">
				<label className="flex items-center gap-2">
					<input type="checkbox" />
					<span>Dark mode (system)</span>
				</label>
			</div>
		</div>
	)
}