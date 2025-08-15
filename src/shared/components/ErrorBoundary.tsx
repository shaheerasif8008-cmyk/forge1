import React from 'react'

interface ErrorBoundaryState { hasError: boolean; error?: any }

export class ErrorBoundary extends React.Component<React.PropsWithChildren<{}>, ErrorBoundaryState> {
	constructor(props: any) {
		super(props)
		this.state = { hasError: false }
	}

	static getDerivedStateFromError(error: any) {
		return { hasError: true, error }
	}

	componentDidCatch(error: any, errorInfo: any) {
		// Log to service if needed
		console.error('ErrorBoundary', error, errorInfo)
	}

	render() {
		if (this.state.hasError) {
			return (
				<div className="mx-auto max-w-lg p-6">
					<h2 className="text-xl font-semibold mb-2">Something went wrong.</h2>
					<pre className="text-xs text-muted-foreground overflow-auto bg-muted p-3 rounded">{String(this.state.error)}</pre>
				</div>
			)
		}
		return this.props.children
	}
}
