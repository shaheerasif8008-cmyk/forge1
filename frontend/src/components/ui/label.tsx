"use client";

import * as React from "react";
import clsx from "clsx";

export type LabelProps = React.LabelHTMLAttributes<HTMLLabelElement>;

export const Label = React.forwardRef<HTMLLabelElement, LabelProps>(
	({ className, ...props }, ref) => (
		<label
			ref={ref}
			className={clsx("text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70", className)}
			{...props}
		/>
	)
);
Label.displayName = "Label";