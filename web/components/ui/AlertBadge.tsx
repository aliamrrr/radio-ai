"use client";

import { cva, type VariantProps } from "class-variance-authority";

const alertBadgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-2 ring-inset",
  {
    variants: {
      color: {
        red:   "bg-red-50 text-red-700 ring-red-600/20",
        amber: "bg-amber-50 text-amber-700 ring-amber-600/20",
        green: "bg-green-50 text-green-700 ring-green-600/20",
        blue:  "bg-blue-50 text-blue-700 ring-blue-600/20",
        gray:  "bg-gray-50 text-gray-600 ring-gray-500/20",
        white: "bg-white text-gray-700 ring-gray-200 shadow-sm",
      },
    },
    defaultVariants: { color: "gray" },
  }
);

const DOT_COLORS: Record<string, string> = {
  red:   "bg-red-500",
  amber: "bg-amber-500",
  green: "bg-green-500",
  blue:  "bg-blue-500",
  gray:  "bg-gray-400",
  white: "bg-gray-400",
};

interface AlertBadgeProps extends VariantProps<typeof alertBadgeVariants> {
  label: string;
  pulse?: boolean;
  className?: string;
}

export function AlertBadge({ label, color = "gray", pulse, className = "" }: AlertBadgeProps) {
  const dotColor = DOT_COLORS[color as string] ?? "bg-gray-400";
  return (
    <span className={`${alertBadgeVariants({ color })} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColor}${pulse ? " animate-pulse" : ""}`} />
      {label}
    </span>
  );
}
