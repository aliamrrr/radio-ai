"use client";

const AVATAR_COLORS = [
  "#f97316",
  "#8b5cf6",
  "#3b82f6",
  "#10b981",
  "#f59e0b",
];

interface FilterBadgeAvatarProps {
  name: string;
  colorIndex?: number;
  className?: string;
}

export function FilterBadgeAvatar({ name, colorIndex = 0, className = "" }: FilterBadgeAvatarProps) {
  const bgColor = AVATAR_COLORS[colorIndex % AVATAR_COLORS.length];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full pl-0.5 pr-2.5 py-0.5 text-xs font-medium bg-white border-2 border-gray-300 shadow-sm text-gray-700 hover:bg-gray-50 transition-colors cursor-default ${className}`}
    >
      <span
        className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white shrink-0"
        style={{ backgroundColor: bgColor }}
      >
        {name.charAt(0).toUpperCase()}
      </span>
      {name}
    </span>
  );
}
