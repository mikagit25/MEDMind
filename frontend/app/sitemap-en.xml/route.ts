import { NextResponse } from "next/server";
import { buildLanguageSitemap, XML_HEADERS } from "@/lib/sitemap-builder";

export const revalidate = 3600;

export async function GET() {
  return new NextResponse(await buildLanguageSitemap("en"), { headers: XML_HEADERS });
}
