import { ButtonHTMLAttributes } from 'react'
import clsx from 'clsx'

type Variant = 'default' | 'outline' | 'destructive'

type Size = 'sm' | 'md' | 'lg'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
	variant?: Variant
	size?: Size
}

export function Button({ className, variant = 'default', size = 'md', ...props }: ButtonProps) {
	const base = 'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50'
	const variants: Record<Variant, string> = {
		default: 'bg-primary text-primary-foreground hover:opacity-90',
		outline: 'border bg-background hover:bg-accent',
		destructive: 'bg-destructive text-destructive-foreground hover:opacity-90',
	}
	const sizes: Record<Size, string> = {
		sm: 'h-8 px-3',
		md: 'h-9 px-4',
		lg: 'h-10 px-6',
	}
	return <button className={clsx(base, variants[variant], sizes[size], className)} {...props} />
}
