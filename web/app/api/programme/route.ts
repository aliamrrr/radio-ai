import { NextResponse } from "next/server";
import path from "path";
import fs from "fs";

const PROGRAMME_PATH = path.resolve(process.cwd(), "../programme.json");

let cache: { data: unknown; at: number } | null = null;
const CACHE_TTL_MS = 5_000;

export async function GET() {
  const now = Date.now();
  if (cache && now - cache.at < CACHE_TTL_MS) {
    return NextResponse.json(cache.data);
  }

  try {
    const raw = fs.readFileSync(PROGRAMME_PATH, "utf-8");
    const data = JSON.parse(raw);
    cache = { data, at: now };
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "programme.json not found" }, { status: 404 });
  }
}
