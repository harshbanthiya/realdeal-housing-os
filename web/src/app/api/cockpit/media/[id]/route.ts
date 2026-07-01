/**
 * Serves local media assets by ID for the cockpit /media page.
 * Looks up the file path from the DB (never exposes paths to the client).
 * Local-only: the cockpit itself is localhost/Tailscale-only.
 */
import { readFile } from "node:fs/promises";
import { extname } from "node:path";
import { NextResponse } from "next/server";
import { readQuery } from "@/lib/db";

const MIME: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".gif": "image/gif",
};

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  if (!/^[0-9a-f-]{36}$/i.test(id)) {
    return new NextResponse("not found", { status: 404 });
  }

  const rows = await readQuery<{ file_path: string }>(
    "SELECT file_path FROM media_assets WHERE id = $1 LIMIT 1",
    [id]
  );
  if (!rows[0]) return new NextResponse("not found", { status: 404 });

  const filePath = rows[0].file_path;
  const ext = extname(filePath).toLowerCase();
  const mime = MIME[ext] ?? "application/octet-stream";

  try {
    const buf = await readFile(filePath);
    return new NextResponse(buf, {
      headers: {
        "Content-Type": mime,
        "Cache-Control": "private, max-age=3600",
      },
    });
  } catch {
    return new NextResponse("not found", { status: 404 });
  }
}
