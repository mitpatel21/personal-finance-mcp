# Running on a Mac

This fork runs the server on your Mac only. It listens on `127.0.0.1`, so it is
never reachable from your network or the internet.

## 1. Plaid account (one time)

1. Sign up at https://dashboard.plaid.com/signup and pick the free **Trial** plan (up to 10 banks).
2. **Team Settings → Products**: enable **Transactions**, **Liabilities**, **Investments**.
3. **Team Settings → API**: copy your `client_id` and **production** secret.
4. Big banks that use OAuth (Chase, Bank of America, Amex and others) may need
   per-bank registration in the dashboard first. See `docs/TROUBLESHOOTING.md`.

## 2. Install

```bash
brew install python@3.12          # needs Python 3.11 or newer
git clone https://github.com/<your-username>/personal-finance-mcp.git ~/personal-finance-mcp
cd ~/personal-finance-mcp
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # fill in PLAID_CLIENT_ID and PLAID_SECRET
chmod 600 .env                    # only your user can read your bank tokens
pytest -q                         # sanity check
```

## 3. Link your banks

```bash
uvicorn link_helper:app --port 8765
```

Open http://localhost:8765, click **Link a bank**, and sign in. The terminal
prints a line like `PLAID_TOKEN_CHASE=access-prod-...`. Paste it into `.env`,
then repeat for each bank. Stop the helper with Ctrl+C when you're done.

## 4. Keep the server running

Try it once in the foreground:

```bash
python server.py                  # http://127.0.0.1:8000/mcp
```

Then install it as a background service that starts at login:

```bash
./mac/install-launch-agent.sh               # install and start
./mac/install-launch-agent.sh --uninstall   # remove
tail -f ~/Library/Logs/personal-finance-mcp/server.log
```

After editing `.env` (for example, after linking a new bank), run the install
script again to restart the server.

## 5. Connect Claude

**Claude Code:**

```bash
claude mcp add --transport http personal-finance http://127.0.0.1:8000/mcp
```

**Claude Desktop:** add this to
`~/Library/Application Support/Claude/claude_desktop_config.json` (requires
Node.js, `brew install node`), then restart Claude Desktop:

```json
{
  "mcpServers": {
    "personal-finance": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://127.0.0.1:8000/mcp"]
    }
  }
}
```

Ask "list my accounts" to confirm it works.

**claude.ai on the web or phone:** these connect from Anthropic's servers,
so they can't reach `127.0.0.1` on your Mac. For that, deploy to Render
instead: see [docs/RENDER.md](../docs/RENDER.md).

## Security notes

- `.env` holds live bank access tokens. It is gitignored. Never commit it, and
  check with `git status` before every push.
- Every tool is read-only. Nothing here can move money.
- Check `get_institutions_status` every few weeks. Banks expire Plaid sessions
  and need re-linking.
