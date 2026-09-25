# n8n templates for OpenFrontDesk

Three ready-to-import workflows. In n8n: **Workflows, Import from File**, then follow the steps for the
template. With the bundled container you can also import all three from the command line; they appear in
the workflow list, unpublished, until you connect your accounts:

```bash
for f in lead-to-sheets-and-slack call-summary-email whatsapp-ai-receptionist; do
  docker compose --profile automation cp "integrations/n8n/$f.json" "n8n:/tmp/$f.json"
  docker compose --profile automation exec n8n n8n import:workflow --input=/tmp/$f.json
done
```

Each template has a fixed workflow `id`, so importing it again updates it instead of creating a copy.
On Windows Git Bash, run `export MSYS_NO_PATHCONV=1` first so `/tmp/...` paths are passed unchanged.

The event format, signature scheme and `/v1` API are documented in
[docs/17-automations.md](../../docs/17-automations.md).

## Prerequisites

- n8n 1.x or 2.x (verified on 2.40). The bundled container: `docker compose --profile automation up -d n8n`.
- Self-hosted n8n must allow the `crypto` module in Code nodes: `NODE_FUNCTION_ALLOW_BUILTIN=crypto`
  (the bundled container already sets it).
- n8n must be reachable from OpenFrontDesk. If both run in the same Docker network, use
  `http://n8n:5678/webhook/...` and set `WEBHOOK_ALLOW_PRIVATE=true` in OpenFrontDesk's `.env`.

## 1. New lead to Google Sheets and Slack

`lead-to-sheets-and-slack.json`

1. Import, open the **OpenFrontDesk event** node and copy its **Production URL**.
2. In OpenFrontDesk, **Integrations, Add a webhook**: paste the URL, select `lead.created`, save, and
   copy the signing secret (shown once).
3. In **Verify signature**, replace `whsec_REPLACE_ME` with that secret.
4. **Append to Google Sheet**: connect Google credentials, pick the spreadsheet; the sheet needs the
   columns `Received, Name, Phone, Email, Intent, Message`.
5. **Notify Slack**: connect Slack and set the channel.
6. Publish (activate) the workflow, then press **Test** on the webhook in OpenFrontDesk. The test event
   is verified and stops at the "Is a new lead" check; take a message through the widget to see a real
   row appear.

## 2. Email every call transcript

`call-summary-email.json`

Same steps as above, subscribing the webhook to `call.completed`. Configure SMTP credentials and the
from/to addresses in **Email the transcript**. Swap the node for Gmail or Outlook if you prefer.

## 3. Answer WhatsApp with your AI receptionist

`whatsapp-ai-receptionist.json`

Uses the same trained agent (knowledge base, booking, lead capture) on WhatsApp, through the `/v1` API.

1. In OpenFrontDesk, **Integrations, Create an API key** and copy it (shown once).
2. In n8n, create a **Header Auth** credential: name `X-API-Key`, value the key. Select it in
   **Ask OpenFrontDesk** and replace `YOUR-OPENFRONTDESK-HOST` in the URL.
3. Connect **WhatsApp Trigger** and **WhatsApp Business Cloud** credentials from your Meta developer
   app (Meta requires a public HTTPS URL for the trigger).
4. Publish. Incoming text messages are answered by the agent; leads and bookings it creates appear in
   the dashboard and fire their own webhooks.

The template is stateless (each message is answered on its own). To keep conversation context, store
recent turns per sender (for example in n8n's Redis or Postgres nodes) and pass them as `history`.

## Signature check used by the templates

The webhook nodes enable **Raw Body** so the Code node can HMAC the exact bytes OpenFrontDesk signed:

```js
const expected = 'sha256=' + crypto.createHmac('sha256', SECRET)
  .update(`${ts}.`).update(raw).digest('hex');
```

It compares in constant time and rejects timestamps older than five minutes. Events failing either
check stop the workflow with an error, visible in n8n's execution list.
