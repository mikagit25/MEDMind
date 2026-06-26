import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-bg px-4">
      <div className="text-center space-y-6 max-w-md w-full">
        <Link href="/" className="inline-block font-syne font-extrabold text-3xl tracking-tight">
          Med<span className="text-red">Mind</span>
        </Link>

        <div className="font-syne font-black text-[8rem] leading-none text-border select-none">
          404
        </div>

        <h1 className="font-syne font-bold text-xl text-ink">
          Page not found
        </h1>
        <p className="font-serif text-ink-3 text-sm">
          The page you're looking for doesn't exist or has been moved.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
          <Link
            href="/dashboard"
            className="px-6 py-3 bg-ink text-white rounded-lg font-syne font-semibold text-sm hover:bg-red transition-colors"
          >
            Dashboard →
          </Link>
          <Link
            href="/modules"
            className="px-6 py-3 border border-border rounded-lg font-syne font-semibold text-sm hover:bg-bg-2 transition-colors text-ink"
          >
            Modules
          </Link>
          <Link
            href="/articles"
            className="px-6 py-3 border border-border rounded-lg font-syne font-semibold text-sm hover:bg-bg-2 transition-colors text-ink"
          >
            Articles
          </Link>
        </div>
      </div>
    </div>
  );
}
