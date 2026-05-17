import { NextRequest, NextResponse } from "next/server";
import path from "path";
import fs from "fs";
import { validateProgramme } from "@/lib/validate";
import { checkRateLimit } from "@/lib/rateLimit";

/**
 * In production (Vercel): set PROGRAMME_URL to your R2 public URL
 *   e.g. https://pub-xxx.r2.dev/programme.json
 * In development: leave unset — reads from local ../programme.json
 */
const PROGRAMME_URL = process.env.PROGRAMME_URL ?? "";
const PROGRAMME_LOCAL = path.resolve(
  process.env.PROGRAMME_PATH ?? path.join(process.cwd(), "../programme.json"),
);

let cache: { data: unknown; at: number } | null = null;
const CACHE_TTL_MS = 30_000;

function getClientIp(req: NextRequest): string {
  return (
    req.headers.get("x-forwarded-for")?.split(",")[0].trim() ??
    req.headers.get("x-real-ip") ??
    "unknown"
  );
}

async function fetchProgramme(): Promise<unknown> {
  if (PROGRAMME_URL) {
    // Production: fetch from Cloudflare R2 CDN
    const res = await fetch(PROGRAMME_URL, {
      next: { revalidate: 30 },
      headers: { "Cache-Control": "no-cache" },
    });
    if (!res.ok) throw new Error(`R2 fetch failed: ${res.status}`);
    return res.json();
  }
  // Development: read from local filesystem
  const raw = fs.readFileSync(PROGRAMME_LOCAL, "utf-8");
  return JSON.parse(raw);
}

export async function GET(req: NextRequest) {
  if (!checkRateLimit(getClientIp(req), 30, 60_000)) {
    return NextResponse.json({ error: "Too many requests" }, { status: 429 });
  }

  const now = Date.now();
  if (cache && now - cache.at < CACHE_TTL_MS) {
    return NextResponse.json(cache.data, {
      headers: { "Cache-Control": "public, max-age=30, stale-while-revalidate=60" },
    });
  }

  try {
    const parsed = await fetchProgramme();
    const data = validateProgramme(parsed);
    cache = { data, at: now };
    return NextResponse.json(data, {
      headers: { "Cache-Control": "public, max-age=30, stale-while-revalidate=60" },
    });
  } catch {
    return NextResponse.json({ error: "Schedule unavailable" }, { status: 503 });
  }
}
