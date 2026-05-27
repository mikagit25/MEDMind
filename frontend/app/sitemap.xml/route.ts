import { NextResponse } from "next/server";
import { buildSitemapIndex, XML_HEADERS } from "@/lib/sitemap-builder";

export const revalidate = 3600;

export async function GET() {
  return new NextResponse(buildSitemapIndex(), { headers: XML_HEADERS });
}
