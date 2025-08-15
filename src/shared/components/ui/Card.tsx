import { ReactNode } from 'react'
import clsx from 'clsx'

export function Card({ className, children }: { className?: string; children: ReactNode }) {
	return (
		<div className={clsx('rounded-lg border bg-card text-card-foreground shadow-sm', className)}>
			{children}
		</div>
	)
}

export function CardHeader({ className, children }: { className?: string; children: ReactNode }) {
	return <div className={clsx('flex flex-col space-y-1.5 p-4', className)}>{children}</div>
}

export function CardTitle({ className, children }: { className?: string; children: ReactNode }) {
	return <h3 className={clsx('text-lg font-semibold leading-none tracking-tight', className)}>{children}</h3>
}

export function CardContent({ className, children }: { className?: string; children: ReactNode }) {
	return <div className={clsx('p-4 pt-0', className)}>{children}</div>
}
