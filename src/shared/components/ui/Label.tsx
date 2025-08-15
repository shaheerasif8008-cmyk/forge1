import { LabelHTMLAttributes } from 'react'
import clsx from 'clsx'

export function Label({ className, ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
	return <label className={clsx('text-sm font-medium leading-none', className)} {...props} />
}
