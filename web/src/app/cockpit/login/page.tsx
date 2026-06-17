import { authenticate } from "@/lib/cockpit/auth-actions";

export const dynamic = "force-dynamic";
export const metadata = { robots: { index: false, follow: false }, title: "Cockpit — Sign in" };

export default async function CockpitLogin({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; next?: string }>;
}) {
  const { error, next } = await searchParams;

  return (
    <div className="flex min-h-screen items-center justify-center bg-mist/30 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-mist-deep bg-white p-8 shadow-sm">
        <div className="mb-6 flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-teal text-[11px] font-bold text-white">RDH</span>
          <span className="text-sm font-semibold tracking-tight text-teal">Operations cockpit</span>
        </div>
        <h1 className="text-lg font-semibold text-ink/85">Sign in</h1>
        <p className="mt-1 text-[13px] text-ink/55">Enter the shared team password to continue.</p>

        <form action={authenticate} className="mt-5 space-y-3">
          {next && <input type="hidden" name="next" value={next} />}
          <input
            type="password" name="password" autoFocus required placeholder="Team password"
            className="w-full rounded-lg border border-mist-deep px-3 py-2 text-sm outline-none focus:border-teal"
          />
          {error && <p className="text-[12px] text-warm">Incorrect password — try again.</p>}
          <button
            type="submit"
            className="w-full rounded-lg bg-teal px-3 py-2 text-sm font-semibold text-white hover:bg-teal/90"
          >
            Sign in
          </button>
        </form>

        <p className="mt-5 font-mono text-[10px] leading-relaxed text-ink/35">
          Private operator tool · real contact data. Access is limited to this team.
        </p>
      </div>
    </div>
  );
}
