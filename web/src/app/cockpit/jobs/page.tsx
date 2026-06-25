import { isDbConfigured, readQuery } from "@/lib/db";
import { resumeIgrJob } from "@/lib/cockpit/actions";

export const dynamic = "force-dynamic";

interface IgrJob {
  id: string;
  building_id: string;
  village: string | null;
  property_number: string | null;
  job_status: string;
  attempted_at: string | null;
}

async function getIgrJobs(): Promise<IgrJob[]> {
  if (!isDbConfigured()) return [];
  return readQuery<IgrJob>(`
    SELECT id, building_id, village, property_number, job_status, attempted_at
    FROM igr_registration_search_jobs
    ORDER BY
      CASE job_status WHEN 'captcha_required' THEN 0 WHEN 'queued' THEN 1 WHEN 'running' THEN 2 ELSE 3 END,
      attempted_at DESC NULLS LAST
    LIMIT 50
  `);
}

export default async function JobsPage() {
  const jobs = await getIgrJobs();
  const paused = jobs.filter(j => j.job_status === "captcha_required");

  return (
    <div className="px-6 py-7 max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight text-teal mb-1">IGR Jobs</h1>
      <p className="text-sm text-ink/55 mb-6">
        {paused.length > 0
          ? `${paused.length} job(s) waiting for CAPTCHA — click Resume after solving in the browser.`
          : "No jobs waiting for CAPTCHA."}
      </p>

      {jobs.length === 0 && (
        <p className="text-sm text-ink/40">No jobs found (DB unavailable or empty).</p>
      )}

      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-left text-ink/50 border-b border-ink/10">
            <th className="pb-2 pr-4 font-medium">ID</th>
            <th className="pb-2 pr-4 font-medium">Village / Property</th>
            <th className="pb-2 pr-4 font-medium">Status</th>
            <th className="pb-2 font-medium">Last attempt</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map(job => (
            <tr key={job.id} className="border-b border-ink/5 hover:bg-ink/5">
              <td className="py-2 pr-4 font-mono text-xs text-ink/40">{job.id.slice(0, 8)}…</td>
              <td className="py-2 pr-4">{[job.village, job.property_number].filter(Boolean).join(" / ") || "—"}</td>
              <td className="py-2 pr-4">
                <span className={
                  job.job_status === "captcha_required" ? "text-amber-600 font-medium" :
                  job.job_status === "parsed" ? "text-teal" :
                  job.job_status === "error" ? "text-red-500" : "text-ink/70"
                }>
                  {job.job_status}
                </span>
              </td>
              <td className="py-2">
                {job.job_status === "captcha_required" ? (
                  <form action={async () => { "use server"; await resumeIgrJob({ jobId: job.id }); }}>
                    <button type="submit"
                      className="rounded px-3 py-1 text-xs bg-teal text-white hover:opacity-80 transition-opacity">
                      Resume
                    </button>
                  </form>
                ) : (
                  <span className="text-ink/40">{job.attempted_at ? new Date(job.attempted_at).toLocaleDateString("en-IN") : "—"}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
