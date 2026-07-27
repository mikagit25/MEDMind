import type { Metadata } from "next";
import Link from "next/link";

// Server-side fetch: prefer internal Docker network URL so SSR works inside the container.
// NEXT_PUBLIC_API_URL is the public domain (medmind.pro) which is unreachable from within Docker.
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: { code: string };
}): Promise<Metadata> {
  return {
    title: `Certificate Verification — MedMind AI`,
    description: "Verify a MedMind AI completion certificate.",
    robots: { index: false, follow: false },
  };
}

async function fetchVerification(code: string): Promise<{
  valid: boolean;
  name: string | null;
  module_title: string;
  issued_at: string | null;
  score: number | null;
  duration_hours: number;
} | null> {
  try {
    const r = await fetch(`${API_URL}/certificates/verify/${code.toUpperCase()}`, {
      cache: "no-store",
    });
    if (!r.ok) return null;
    return r.json();
  } catch {
    return null;
  }
}

export default async function VerifyPage({ params }: { params: { code: string } }) {
  const data = await fetchVerification(params.code);

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      {/* Minimal header */}
      <header className="border-b border-border px-6 py-4">
        <Link href="/" className="font-syne font-black text-lg text-ink-1">
          MedMind AI
        </Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="max-w-lg w-full">
          {data ? (
            /* Valid certificate */
            <div className="border border-green/30 rounded-xl p-8 bg-green-light/30 space-y-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-green flex items-center justify-center shrink-0">
                  <svg viewBox="0 0 20 20" fill="white" className="w-5 h-5">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                  </svg>
                </div>
                <div>
                  <p className="font-syne font-black text-green text-lg">Certificate Valid</p>
                  <p className="font-serif text-xs text-green/70">Verified by MedMind AI</p>
                </div>
              </div>

              <div className="border-t border-green/20 pt-5 space-y-3">
                {data.name && (
                  <div>
                    <p className="text-xs font-serif text-ink-4 uppercase tracking-wide">Issued to</p>
                    <p className="font-syne font-bold text-ink-1 text-lg mt-0.5">{data.name}</p>
                  </div>
                )}
                <div>
                  <p className="text-xs font-serif text-ink-4 uppercase tracking-wide">Module completed</p>
                  <p className="font-syne font-bold text-ink-1 mt-0.5">{data.module_title}</p>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-xs font-serif text-ink-4 uppercase tracking-wide">Date</p>
                    <p className="font-syne font-bold text-ink-2 text-sm mt-0.5">
                      {data.issued_at
                        ? new Date(data.issued_at).toLocaleDateString("en-US", {
                            year: "numeric", month: "short", day: "numeric",
                          })
                        : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-serif text-ink-4 uppercase tracking-wide">Duration</p>
                    <p className="font-syne font-bold text-ink-2 text-sm mt-0.5">
                      {data.duration_hours ? `${data.duration_hours}h` : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-serif text-ink-4 uppercase tracking-wide">Score</p>
                    <p className="font-syne font-bold text-ink-2 text-sm mt-0.5">
                      {data.score !== null ? `${Math.round(data.score)}%` : "—"}
                    </p>
                  </div>
                </div>
              </div>

              <div className="border-t border-green/20 pt-4">
                <p className="text-[10px] font-serif text-ink-4 break-all">
                  Verification code: {params.code.toUpperCase()}
                </p>
                <p className="text-[10px] font-serif text-ink-4 mt-1">
                  This certificate is for educational purposes only and does not constitute a medical licence.
                </p>
              </div>
            </div>
          ) : (
            /* Invalid / not found */
            <div className="border border-red/30 rounded-xl p-8 bg-red/5 space-y-4 text-center">
              <div className="w-12 h-12 rounded-full bg-red/10 flex items-center justify-center mx-auto">
                <svg viewBox="0 0 20 20" fill="currentColor" className="w-6 h-6 text-red">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"/>
                </svg>
              </div>
              <p className="font-syne font-black text-red text-lg">Certificate Not Found</p>
              <p className="font-serif text-sm text-ink-3">
                The code <span className="font-mono font-bold">{params.code.toUpperCase()}</span> does not match any certificate in our records.
              </p>
              <p className="text-xs font-serif text-ink-4">
                Please check the code and try again. Codes are 24 characters and case-insensitive.
              </p>
            </div>
          )}

          <p className="text-center font-serif text-xs text-ink-4 mt-8">
            Issued by{" "}
            <Link href="/" className="underline hover:text-ink-2">
              MedMind AI
            </Link>{" "}
            — Medical Education Platform
          </p>
        </div>
      </main>
    </div>
  );
}
