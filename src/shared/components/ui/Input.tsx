import { InputHTMLAttributes, forwardRef } from 'react'
import clsx from 'clsx'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input({ className, ...props }, ref) {
	return (
		<input ref={ref} className={clsx('flex h-9 w-full rounded-md border bg-background px-3 py-2 text-sm', className)} {...props} />
	)
})