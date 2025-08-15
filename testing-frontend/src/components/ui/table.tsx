import * as React from 'react'

export const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>((props, ref) => (
  <div className='overflow-auto'><table ref={ref} className='w-full text-sm' {...props} /></div>
))
Table.displayName = 'Table'

export const TableHeader = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>((props, ref) => (
  <thead ref={ref} className='[&_tr]:border-b' {...props} />
))
TableHeader.displayName = 'TableHeader'

export const TableBody = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>((props, ref) => (
  <tbody ref={ref} className='[&_tr:last-child]:border-0' {...props} />
))
TableBody.displayName = 'TableBody'

export const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>((props, ref) => (
  <tr ref={ref} className='border-b hover:bg-gray-50' {...props} />
))
TableRow.displayName = 'TableRow'

export const TableHead = React.forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>((props, ref) => (
  <th ref={ref} className='h-10 px-2 text-left align-middle font-medium text-gray-600' {...props} />
))
TableHead.displayName = 'TableHead'

export const TableCell = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>((props, ref) => (
  <td ref={ref} className='p-2 align-middle' {...props} />
))
TableCell.displayName = 'TableCell'


