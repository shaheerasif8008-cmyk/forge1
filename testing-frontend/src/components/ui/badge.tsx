import * as React from 'react'
import { cn } from './utils'

export function Badge({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('inline-flex items-center rounded-md border bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700', className)} {...props} />
}


