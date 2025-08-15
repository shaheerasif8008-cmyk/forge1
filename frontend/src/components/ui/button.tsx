"use client";

import * as React from "react";
import clsx from "clsx";

export type ButtonVariant = "default" | "secondary" | "outline" | "destructive" | "ghost" | "link";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
	variant?: ButtonVariant;
	size?: ButtonSize;
	isLoading?: boolean;
}

const baseClasses = "inline-flex items-center justify-center font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 disabled:pointer-events-none rounded-md";

const variantClasses: Record<ButtonVariant, string> = {
	default: "bg-primary text-white hover:bg-primary-dark",
	secondary: "bg-secondary text-foreground hover:bg-muted",
	outline: "border bg-transparent hover:bg-muted",
	destructive: "bg-danger text-white hover:opacity-90",
	ghost: "bg-transparent hover:bg-muted",
	link: "bg-transparent underline underline-offset-2 hover:text-primary",
};

const sizeClasses: Record<ButtonSize, string> = {
	sm: "h-8 px-3 text-sm",
	md: "h-10 px-4 text-sm",
	lg: "h-12 px-6 text-base",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
	({ className, variant = "default", size = "md", isLoading = false, children, ...props }, ref) => {
		return (
			<button
				ref={ref}
				className={clsx(baseClasses, variantClasses[variant], sizeClasses[size], className)}
				{...props}
				disabled={isLoading || props.disabled}
			>
				{children}
			</button>
		);
	}
);
Button.displayName = "Button";