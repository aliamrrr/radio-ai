export const THEMES: Record<string, {
  dot: string; bar: string; bg: string; text: string;
  border: string; digits: string; gradient: string;
}> = {
  "international news": { dot: "bg-blue-500",    bar: "bg-blue-400",    bg: "bg-blue-50",    text: "text-blue-700",    border: "border-blue-200",   digits: "text-blue-900",    gradient: "from-blue-600 to-blue-800"    },
  "tech & AI":          { dot: "bg-violet-500",  bar: "bg-violet-400",  bg: "bg-violet-50",  text: "text-violet-700",  border: "border-violet-200", digits: "text-violet-900",  gradient: "from-violet-600 to-purple-800" },
  "culture":            { dot: "bg-amber-500",   bar: "bg-amber-400",   bg: "bg-amber-50",   text: "text-amber-700",   border: "border-amber-200",  digits: "text-amber-900",   gradient: "from-amber-500 to-orange-700"  },
  "lifestyle":          { dot: "bg-emerald-500", bar: "bg-emerald-400", bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200",digits: "text-emerald-900", gradient: "from-emerald-500 to-teal-700"  },
  "sports":             { dot: "bg-orange-500",  bar: "bg-orange-400",  bg: "bg-orange-50",  text: "text-orange-700",  border: "border-orange-200", digits: "text-orange-900",  gradient: "from-orange-500 to-red-700"    },
};

export const THEME_FALLBACK = {
  dot: "bg-gray-400", bar: "bg-gray-400", bg: "bg-gray-50", text: "text-gray-600",
  border: "border-gray-200", digits: "text-gray-900", gradient: "from-gray-500 to-gray-700",
};

export function getTheme(thematique: string) {
  return THEMES[thematique] ?? THEME_FALLBACK;
}
