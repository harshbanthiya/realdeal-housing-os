# Cockpit multi-user access (you + director)

Goal: you and the director use the **same** cockpit and the **same** live data at the
same time — usually on the same WiFi, sometimes from elsewhere.

## The model

Only **one machine runs the stack** (your Mac): Docker Postgres + the Next.js app.
The director does **not** run Docker or a second copy — she just opens a browser to
your machine. Two copies would mean two separate databases that drift apart. One host,
one Postgres, many browser clients = everyone sees the same data.

```
  Your Mac (server)                         Director's laptop/phone
  ┌───────────────────────────┐             ┌──────────────────┐
  │ Docker Postgres (truth)    │             │  Browser         │
  │ Next.js cockpit :3000  ◄───┼──Tailscale──┼─►  /cockpit      │
  └───────────────────────────┘             └──────────────────┘
```

## One-time setup

1. **Install Tailscale** on both machines (free): https://tailscale.com/download
   Sign both into the same account → they join your private "tailnet". Note your Mac's
   Tailscale name/IP (`tailscale ip -4`, or MagicDNS name like `your-mac.tail-xxxx.ts.net`).
2. **Set the shared password** in `web/.env.local` (already created, never committed):
   ```
   COCKPIT_PASSWORD=<the password you share with the director>
   COCKPIT_AUTH_TOKEN=<long random secret — keep private>
   ```
   Change `COCKPIT_PASSWORD` any time; restart the server to apply.

## Running it (each session)

```bash
./start.sh              # Postgres (if not already up)
./scripts/serve_cockpit.sh
```

`serve_cockpit.sh` builds the app, prints the LAN / Bonjour / Tailscale URLs, and serves
on `0.0.0.0:3000` with `caffeinate` so the Mac won't sleep and drop the director.

The director opens the **Tailscale URL** (works on any network) or, on the same WiFi,
`http://<your-mac>.local:3000/cockpit`. First visit → she enters the shared password
once (30-day session cookie). "Sign out" is in the sidebar.

## Security notes

- The cockpit shows **real contact PII**. The password gate (Next.js middleware) protects
  every `/cockpit` route; Tailscale keeps it off the public internet and limits access to
  your tailnet. Don't expose port 3000 to the open internet or a public/guest WiFi.
- If `COCKPIT_AUTH_TOKEN` is unset, the gate is **open** — `serve_cockpit.sh` warns before
  starting. Always keep it set when exposing the app.
- All writes still go through the guarded Python scripts (dry-run by default); the DB layer
  is read-only. Two people using it at once is safe — Postgres handles concurrency and the
  in-transaction guards (daily cap, `send_enabled=false`) hold under races.

## Same-WiFi-only fallback (no Tailscale)

Run `serve_cockpit.sh`, allow incoming connections for Node in macOS Firewall, and have the
director use the printed **LAN** or **Bonjour** URL. A DHCP reservation in your router keeps
the LAN IP stable. This won't work when she's on a different network — that's what Tailscale
solves.
