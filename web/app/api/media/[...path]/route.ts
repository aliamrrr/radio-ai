import { NextRequest, NextResponse } from "next/server";
import path from "path";
import fs from "fs";

const MEDIA_DIR = path.resolve(process.cwd(), "../media");

const CONTENT_TYPES: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
};

export async function GET(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const filePath = path.join(MEDIA_DIR, ...params.path);

  // Prevent path traversal
  if (!filePath.startsWith(MEDIA_DIR)) {
    return new NextResponse("Forbidden", { status: 403 });
  }

  if (!fs.existsSync(filePath)) {
    return new NextResponse("Not found", { status: 404 });
  }

  const ext = path.extname(filePath).toLowerCase();
  const contentType = CONTENT_TYPES[ext] ?? "application/octet-stream";

  const fileSize = fs.statSync(filePath).size;
  const rangeHeader = req.headers.get("range");

  if (rangeHeader) {
    const match = rangeHeader.match(/bytes=(\d*)-(\d*)/);
    if (match) {
      const start = match[1] ? parseInt(match[1], 10) : 0;
      const end = match[2] ? parseInt(match[2], 10) : fileSize - 1;

      if (start >= fileSize || end >= fileSize || start > end) {
        return new NextResponse("Range Not Satisfiable", {
          status: 416,
          headers: { "Content-Range": `bytes */${fileSize}` },
        });
      }

      const chunkSize = end - start + 1;
      const buffer = Buffer.alloc(chunkSize);
      const fd = fs.openSync(filePath, "r");
      fs.readSync(fd, buffer, 0, chunkSize, start);
      fs.closeSync(fd);

      return new NextResponse(buffer, {
        status: 206,
        headers: {
          "Content-Type": contentType,
          "Content-Range": `bytes ${start}-${end}/${fileSize}`,
          "Accept-Ranges": "bytes",
          "Content-Length": String(chunkSize),
          "Cache-Control": "public, max-age=3600",
        },
      });
    }
  }

  const buffer = fs.readFileSync(filePath);
  return new NextResponse(buffer, {
    headers: {
      "Content-Type": contentType,
      "Accept-Ranges": "bytes",
      "Content-Length": String(fileSize),
      "Cache-Control": "public, max-age=3600",
    },
  });
}
