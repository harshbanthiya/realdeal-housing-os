/**
 * Read-only Postgres access for the cockpit.
 *
 * Connects to the local Real Deal OS database using DATABASE_URL (set in
 * web/.env.local - never committed). Every query runs inside a READ ONLY
 * transaction, so the cockpit can never mutate Postgres - mutations stay with
 * the guarded apply/revert scripts. If DATABASE_URL is unset, callers fall back
 * to seed data so the shell still renders.
 *
 * Server-only: importing this into a Client Component will fail the build
 * (the `pg` driver is Node-only), which is the intended guard.
 */
import { Pool } from "pg";

let pool: Pool | null = null;

export function isDbConfigured(): boolean {
  return Boolean(process.env.DATABASE_URL);
}

function getPool(): Pool | null {
  if (!process.env.DATABASE_URL) return null;
  if (!pool) {
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      max: 4,
      idleTimeoutMillis: 10_000,
      connectionTimeoutMillis: 4_000,
      statement_timeout: 5_000,
    });
  }
  return pool;
}

/** Run a read-only SELECT. Returns [] if the DB isn't configured or errors. */
export async function readQuery<T = Record<string, unknown>>(
  sql: string,
  params: unknown[] = []
): Promise<T[]> {
  const p = getPool();
  if (!p) return [];
  const client = await p.connect();
  try {
    await client.query("BEGIN TRANSACTION READ ONLY");
    const res = await client.query(sql, params);
    await client.query("COMMIT");
    return res.rows as T[];
  } catch {
    try { await client.query("ROLLBACK"); } catch {}
    return [];
  } finally {
    client.release();
  }
}
