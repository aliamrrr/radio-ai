import { NextRequest, NextResponse } from "next/server";
import path from "path";
import fs from "fs";
import { checkRateLimit } from "@/lib/rateLimit";

const MEDIA_DIR = path.resolve(
  process.env.MEDIA_DIR ?? path.join(process.cwd(), "../media"),
);

const ALLOWED_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".mp3", ".wav"]);

const CONTENT_TYPES: Record<string, string> = {
  ".png":  "image/png",
  ".jpg":  "image/jpeg",
  ".jpeg": "image/jpeg",
  ".mp3":  "audio/mpeg",
  ".wav":  "audio/wav",
};

const SECURITY_HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "Cache-Control": "public, max-age=3600",
};

/** Ensure the resolved path stays inside MEDIA_DIR (prevents path traversal). */
function isPathSafe(filePath: string): boolean {
  const resolved = path.resolve(filePath);
  const base = path.resolve(MEDIA_DIR);
  // Must start with base + separator (prevents base/../../etc attacks)
  return resolved.startsWith(base + path.sep) || resolved === base;
}

function getClientIp(req: NextRequest): string {
  return (
    req.headers.get("x-forwarded-for")?.split(",")[0].trim() ??
    req.headers.get("x-real-ip") ??
    "unknown"
  );
}

export async function GET(
  req: NextRequest,
  { params }: { params: { path: string[] } },
) {
  const ip = getClientIp(req);

  // Rate limit: 120 requests per minute per IP
  if (!checkRateLimit(ip, 120, 60_000)) {
    return new NextResponse("Too Many Requests", { status: 429 });
  }

  // Decode each segment to handle URL-encoded characters
  const segments = params.path.map((seg) => decodeURIComponent(seg));
  const filePath = path.join(MEDIA_DIR, ...segments);

  if (!isPathSafe(filePath)) {
    console.warn(`[media] Path traversal attempt from ${ip}: ${params.path.join("/")}`);
    return new NextResponse("Forbidden", { status: 403 });
  }

  const ext = path.extname(filePath).toLowerCase();

  // Whitelist allowed extensions
  if (!ALLOWED_EXTENSIONS.has(ext)) {
    return new NextResponse("Forbidden", { status: 403 });
  }

  if (!fs.existsSync(filePath)) {
    return new NextResponse("Not found", { status: 404 });
  }

  const contentType = CONTENT_TYPES[ext] ?? "application/octet-stream";
  const fileSize = fs.statSync(filePath).size;
  const rangeHeader = req.headers.get("range");

  if (rangeHeader) {
    const match = rangeHeader.match(/bytes=(\d*)-(\d*)/);
    if (match) {
      const start = match[1] ? parseInt(match[1], 10) : 0;
      const end   = match[2] ? parseInt(match[2], 10) : fileSize - 1;

      if (start >= fileSize || end >= fileSize || start > end) {
        return new NextResponse("Range Not Satisfiable", {
          status: 416,
          headers: { "Content-Range": `bytes */${fileSize}` },
        });
      }

      const chunkSize = end - start + 1;
      const stream = fs.createReadStream(filePath, { start, end });
      const readable = new ReadableStream({
        start(controller) {
          stream.on("data", (chunk) =>
            controller.enqueue(typeof chunk === "string" ? Buffer.from(chunk) : chunk),
          );
          stream.on("end",   () => controller.close());
          stream.on("error", (e) => controller.error(e));
        },
        cancel() { stream.destroy(); },
      });

      return new NextResponse(readable, {
        status: 206,
        headers: {
          ...SECURITY_HEADERS,
          "Content-Type":   contentType,
          "Content-Range":  `bytes ${start}-${end}/${fileSize}`,
          "Accept-Ranges":  "bytes",
          "Content-Length": String(chunkSize),
        },
      });
    }
  }

  // Full file — stream to avoid loading large audio into memory
  const stream = fs.createReadStream(filePath);
  const readable = new ReadableStream({
    start(controller) {
      stream.on("data", (chunk) =>
        controller.enqueue(typeof chunk === "string" ? Buffer.from(chunk) : chunk),
      );
      stream.on("end",   () => controller.close());
      stream.on("error", (e) => controller.error(e));
    },
    cancel() { stream.destroy(); },
  });

  return new NextResponse(readable, {
    headers: {
      ...SECURITY_HEADERS,
      "Content-Type":   contentType,
      "Accept-Ranges":  "bytes",
      "Content-Length": String(fileSize),
    },
  });
}
