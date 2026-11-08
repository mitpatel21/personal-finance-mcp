# Deploying to Render

This puts your finance server on the internet so you can use it from claude.ai
on the web and your phone. Access is locked to your GitHub account: anyone else
who finds the URL and signs in with GitHub gets rejected.

**Cost:** Render's Starter plan (about $7/month) plus a 1 GB disk (a few cents
a month). The free plan works, but it sleeps after 15 idle minutes (the first
request then takes 30 to 60 seconds and may time out in Claude) and forgets
logins on every restart. To use it anyway, set `plan: free` and delete the
`disk:` block in `render.yaml`.

## What protects your data

- **Login:** every request needs a GitHub sign-in (OAuth). The server checks
  the signed-in account against `ALLOWED_GITHUB_USERS` and rejects everyone
  else, including on tool listing.
- **Fails closed:** if auth isn't fully configured on Render, the server
  refuses to start instead of running unprotected.
- **Read-only:** no tool can move money or change anything at your banks.
- **Least privilege:** the GitHub login only asks to read your public profile.
- **Secrets stay in Render's environment settings,** never in the repo.

## 1. Pick your URL

Open `render.yaml` and set `name:` to something unique (it's already set to
`mitpatel21-finance-mcp`). Your server will live at:

```
https://<name>.onrender.com
```

If Render says the name is taken, it'll add a suffix. Use whatever URL Render
actually shows in the steps below.

## 2. Create a GitHub OAuth app

GitHub → **Settings → Developer settings → OAuth Apps → New OAuth App**:

| Field | Value |
| --- | --- |
| Application name | Personal Finance MCP |
| Homepage URL | `https://<name>.onrender.com` |
| Authorization callback URL | `https://<name>.onrender.com/auth/callback` |

Create it, then copy the **Client ID** and click **Generate a new client
secret**. Keep both handy.

## 3. Link your banks (on your Mac)

Bank linking runs locally only. Follow steps 1 to 3 in
[mac/README.md](../mac/README.md). You'll end up with lines like
`PLAID_TOKEN_CHASE=access-prod-...` in your local `.env`.

## 4. Deploy

1. In Render: **New → Blueprint**, connect your GitHub, and pick your fork.
2. Render reads `render.yaml` and asks for the secret values:
   - `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`: from step 2
   - `PLAID_CLIENT_ID`, `PLAID_SECRET`: from your Plaid dashboard
3. Click **Apply**.
4. In the new service: **Environment → Add Environment Variable**, and add
   each `PLAID_TOKEN_<BANK>` line from your local `.env`. Save (Render
   redeploys automatically).

Check that it's up: `https://<name>.onrender.com/health` should say `ok`, and
`https://<name>.onrender.com/mcp` should refuse you (401). That refusal is
the login doing its job.

## 5. Connect Claude

**claude.ai (web, desktop app, phone):** Settings → Connectors → **Add custom
connector**. Name it "Personal finance" and enter:

```
https://<name>.onrender.com/mcp
```

Click **Connect**. You'll see a consent page, then GitHub's sign-in. Approve,
and the connector shows as connected. Connectors you add on the web also show
up on your phone.

**Claude Code:**

```bash
claude mcp add --transport http personal-finance https://<name>.onrender.com/mcp
```

Ask "list my accounts" to confirm.

## Maintenance

- **Adding a bank:** link it locally (`uvicorn link_helper:app --port 8765`),
  then add its `PLAID_TOKEN_<BANK>` in Render's Environment tab.
- **Re-auth:** banks expire Plaid sessions now and then. Ask Claude to check
  institution status; re-link any bank that says `re_auth_required`.
- **Logs:** Render dashboard → your service → Logs. Rejected sign-ins show up as
  `Rejected GitHub user ...`.
- **Lock everything down fast:** delete the GitHub OAuth app's client secret
  (all logins stop working), or suspend the service in Render.
- **Rotate secrets** by regenerating them in GitHub/Plaid and updating Render's
  Environment tab.

## Troubleshooting

- **Service won't start, log says "Refusing to start on Render without auth"
  or "half-configured":** one of the GitHub variables is missing. Check the
  Environment tab.
- **GitHub says "redirect_uri is not associated with this application":** the
  callback URL in the GitHub app doesn't exactly match
  `https://<your-actual-url>/auth/callback`.
- **Claude connects but every call fails:** check that you signed in to GitHub
  as an account listed in `ALLOWED_GITHUB_USERS`.
- **Claude has to reconnect after every deploy:** the disk isn't attached
  (free plan), so login state isn't saved.
