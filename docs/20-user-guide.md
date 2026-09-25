# 20 — User guide: running your AI receptionist

This guide is for the people who use OpenFrontDesk day to day: a clinic, salon, agency or any small
business that wants every call and website chat answered. It walks through everything you can do once
you are signed in, in the order most people do it.

**Contents**

1. [Create your account](#1-create-your-account)
2. [Onboarding: five steps to a working receptionist](#2-onboarding-five-steps-to-a-working-receptionist)
3. [The dashboard at a glance](#3-the-dashboard-at-a-glance)
4. [Knowledge: teach it about your business](#4-knowledge-teach-it-about-your-business)
5. [Test: talk to it like a customer](#5-test-talk-to-it-like-a-customer)
6. [Deploy: put it where your customers are](#6-deploy-put-it-where-your-customers-are)
7. [Activity: calls, leads and bookings](#7-activity-calls-leads-and-bookings)
8. [Integrations: connect your other tools](#8-integrations-connect-your-other-tools)
9. [Settings: your business and your receptionist](#9-settings-your-business-and-your-receptionist)
10. [Custom solutions](#10-custom-solutions)
11. [Admin (platform operators only)](#11-admin-platform-operators-only)
12. [Plans, fair use and limits](#12-plans-fair-use-and-limits)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Create your account

1. Open the website and click **Start free** (or go to `/signup`).
2. Enter your name, your business name, your work email and a password of at least 8 characters.
3. Click **Create account**. You land straight in onboarding.

Your business name becomes your **workspace**. Everything you add (knowledge, settings, leads, bookings)
belongs to that workspace and is invisible to every other business on the platform.

To come back later, use **Sign in** (`/login`). You stay signed in on that browser until you sign out
from the account menu at the bottom of the sidebar.

## 2. Onboarding: five steps to a working receptionist

Onboarding takes about five minutes. The step you are on is part of the web address, so refreshing the
page keeps your place, and you can change every answer later in Settings.

| Step | What you do | Why it matters |
|---|---|---|
| **1. Your business** | Business name, type of business, time zone (detected from your browser) and opening hours. Use a preset such as "Weekdays 9 to 5", then adjust individual days | The receptionist only offers appointments inside these hours, in your time zone |
| **2. Your receptionist** | Name, voice, tone (Friendly, Reassuring, Efficient, Upbeat or Formal) and the greeting | The same personality answers the phone and the website chat |
| **3. What it knows** | Paste your FAQs and prices, add a web page, or upload a document | It answers only from these sources. You can skip and add them later |
| **4. Try it** | Chat with it exactly as a customer would | Confirms it answers correctly before anyone else sees it |
| **5. Go live** | Copy the one-line website snippet | Puts the chat bubble on your website |

Click **Go to my dashboard** to finish.

## 3. The dashboard at a glance

The left sidebar is grouped the way you work:

- **Overview**: your home screen.
- **Build**: Knowledge, Test, Deploy.
- **Activity**: Calls, Leads, Bookings.
- **Workspace**: Integrations, Settings.

On a phone, open the sidebar with the menu button at the top left. The sun and moon button switches
between light and dark mode.

**Overview** shows:

- **Finish setting up**: a four-step checklist (profile, knowledge, test, website) that disappears once
  everything is done. Each item links to the page that completes it.
- **Numbers**: calls answered, bookings made, leads captured and minutes handled.
- **Latest leads** and **Upcoming bookings**, with links to the full lists.

## 4. Knowledge: teach it about your business

Your receptionist never makes things up. It searches your knowledge for every factual question, and if
the answer is not there it offers to take a message instead of guessing. The better your knowledge,
the better it performs.

### Adding a source

Open **Knowledge** and choose one of three tabs:

- **Paste text**: the quickest option. Give it a title (for example "Prices and opening hours") and
  paste the content. Question-and-answer pairs work especially well.
- **Website**: enter the full address of a page (starting with `https://`). The page text is read once.
  Add each important page separately (services, prices, FAQ, contact).
- **Upload**: PDF, Word (DOCX) or text files up to 15 MB, such as price lists, policies or brochures.

After you add a source it shows **Pending**, then **Processing**, then **Ready**, usually within
seconds. It is live the moment it shows Ready. If a source shows **Failed**, the reason is displayed
under its title. Remove it and add it again, or paste the text directly.

### Managing sources

- **Re-index** (circular arrows): processes an existing source again.
- **Remove** (bin): the receptionist stops using it immediately.

### Check what it would read

The **Check what it would read** box shows exactly which passages the receptionist finds for a question,
with a match score and the source name. Use it when an answer seems wrong: if the right passage does not
appear, add or reword a source that covers it.

### Tips for good knowledge

- Write prices, durations and policies explicitly: "A routine cleaning costs $90 and takes 30 minutes."
- Include the questions customers really ask, in their words.
- Say what you do **not** offer ("We do not do home visits"), so it can answer "no" confidently.
- Keep one topic per source and give each a clear title. Titles are shown as the source of answers.

## 5. Test: talk to it like a customer

Open **Test**. There are two panels side by side.

### Chat test

This is the same brain your website visitors talk to. Type a question or click one of the suggestions.
Answers show the **source** they came from underneath. **Reset** starts a fresh conversation.

It can also book: ask for an appointment ("Can I come in this Sunday at 11?"), give a name and phone
number, and confirm. The booking is real and appears under Bookings. Messages it takes appear under
Leads.

### Voice test

1. Click **Start a test call** and allow microphone access when your browser asks.
2. Wait for **Live**, then speak normally. Headphones prevent echo.
3. The conversation appears as a live transcript. **Mute** pauses your microphone; **Hang up** ends
   the call.

If every voice line is busy you see **"You are number N in line"**. Keep the page open and the call starts
automatically when a line frees up. Text chat is never queued. Finished calls appear under **Calls** with
their transcript.

## 6. Deploy: put it where your customers are

### Website chat widget

1. Open **Deploy**.
2. Choose a **brand color** from the swatches, or pick your own with the last circle.
3. Click **Preview on this page** to see the real chat bubble in the corner, talking to your receptionist.
   Click **Hide preview** to remove it.
4. Click **Copy snippet** and paste it into your website just before the closing `</body>` tag, on every
   page where the chat should appear.

Where to paste it on common platforms (menu names change between versions, so look for "custom code" or "code injection"):

| Platform | Where |
|---|---|
| WordPress | A header and footer plugin (for example "WPCode"), in the footer section |
| Wix | Settings, Custom code, Add custom code, placed in Body end, on all pages |
| Squarespace | Settings, Advanced, Code injection, Footer |
| Shopify | Online Store, Themes, Edit code, `theme.liquid`, just before `</body>` |
| Plain HTML | Just before `</body>` in each page, or in your shared layout |

### Phone number

Connecting a real phone number (Telnyx or Twilio) is done at go-live. Until then, test voice in the
browser from the Test page.

### WhatsApp

A ready-made workflow answers WhatsApp messages with the same receptionist. It needs a WhatsApp Business
account from Meta. You can set it up yourself (see Integrations) or request it through **Get it set up**,
which opens the custom-solutions form.

## 7. Activity: calls, leads and bookings

- **Calls**: every voice call with its date, caller, outcome and length. Click a row to read the full
  transcript, a summary when available, and how fast the receptionist replied.
- **Leads**: everyone who left their details or a message, by phone, chat or your other tools. Search by
  name, phone, email or message. Click a phone number or email address to call or write back.
- **Bookings**: split into **Upcoming** and **Past**, with the customer, service and phone number. All
  bookings respect your opening hours and appointment length.

## 8. Integrations: connect your other tools

Only workspace owners and admins can manage integrations.

### Webhooks: send events to your tools

A webhook sends a message to another tool (n8n, Zapier, Make or your own system) the moment something
happens:

| Event | When |
|---|---|
| `lead.created` | Someone leaves their details or a message |
| `booking.created` | An appointment is booked |
| `call.completed` | A voice call ends, with its transcript |
| `knowledge.ready` | A knowledge source finishes indexing |

To add one:

1. Click **Add webhook**, paste the address your tool gives you, and optionally describe it.
2. Tick the events you want (none ticked means all events), then **Save webhook**.
3. Copy the **signing secret** from the window that appears. It is shown only once. Your tool uses it to
   confirm each message really came from OpenFrontDesk.

Each webhook has these buttons:

- **Test** sends a sample event now and shows the result.
- **Log** lists recent deliveries: time, result, HTTP status, attempts and any error.
- **Disable / Enable** pauses and resumes deliveries.
- **Rotate** creates a new secret (update your tool with it).
- **Delete** removes the webhook.

Failed deliveries are retried automatically. A webhook that keeps failing is disabled so it cannot pile
up errors; fix the address and click Enable.

### API keys: let your tools act on your workspace

API keys let a workflow ask your receptionist a question, log a lead, check availability, book an
appointment or read calls.

1. Enter a name (for example "n8n production") and click **Create key**.
2. Copy the key from the window that appears. It is shown only once and stored only in scrambled form.
3. In your tool, send it as the `X-API-Key` header. The **Quick start** box shows a ready-to-run example.

**Revoke** stops a key immediately. Create one key per tool, so you can revoke one without breaking the
others.

Ready-made n8n workflows (leads to Google Sheets and Slack, call transcripts by email, WhatsApp answered by
your receptionist) are in the project's `integrations/n8n` folder, with setup steps.

## 9. Settings: your business and your receptionist

Only workspace owners and admins can change settings.

**Business**

- **Business name** and **type of business**.
- **Time zone**: every date and time the receptionist uses is in this zone.
- **Opening hours**: switch each day on or off and set its hours, or apply a preset.

**Receptionist**

- **Name** and **voice**: several voices with US and UK accents. The voice applies to the next call.
- **Tone**: how it speaks, on the phone and in chat.
- **Greeting**: the first sentence callers and visitors hear.
- **Services it can book**: a comma-separated list, for example "Cleaning, Whitening, Check-up".
- **Appointment length**: from 15 to 90 minutes; available slots are offered in these steps.

Click **Save** under each section. Changes apply to the next conversation.

## 10. Custom solutions

For something built around your business (a WhatsApp assistant, an HR or internal helpdesk bot,
connections to your CRM or calendar, or custom workflows), open **Custom solutions** from the website
menu or the account menu. Describe what you need; when you are signed in, your name, email and business
are filled in for you.

You receive a confirmation email, and if the team has a booking page you can pick a call time straight
away. Someone replies personally within one business day.

## 11. Admin (platform operators only)

People whose email is listed in the platform's `ADMIN_EMAILS` setting see an extra **Admin** item in the
sidebar. It is for the team running the OpenFrontDesk service, not for individual businesses.

- **Custom-solution requests**: counts by status, a status filter and search. Open a request to see every
  detail, reply by email, set the status (new, contacted, scheduled, won, lost, spam), record a meeting time
  and link, keep internal notes, send a scheduling email with a personal note and a booking link filled in
  for the recipient, or delete the request.
- **Voice access**: live voice sessions against capacity, people waiting in the queue, and the **priority
  allowlist**. People on the allowlist skip the voice queue even when every line is busy.

## 12. Plans, fair use and limits

OpenFrontDesk is free. To keep it fair for everyone:

| What | Default |
|---|---|
| Accounts, knowledge, chat widget, dashboard | Unlimited |
| Simultaneous live voice calls across the platform | 3 lines, then a visible queue |
| When a voice line is freed | On hang-up or leaving the page; after about 6 minutes if the browser closes unexpectedly |
| Website chat messages | 60 per minute per workspace |
| Dashboard and API requests | 120 per minute per workspace |
| File uploads | 15 MB per file |

Self-hosted installations can change all of these in their configuration.

## 13. Troubleshooting

| Problem | What to do |
|---|---|
| It says it is not sure about something it should know | Use **Check what it would read** on the Knowledge page. If the right passage is missing, add or reword a source |
| A source stays on Pending or shows Failed | Wait a minute and refresh. If it failed, read the reason under its title, remove it and add it again, or paste the text instead |
| It offers the wrong times | Check the time zone, opening hours and appointment length in Settings |
| The voice test cannot hear me | Allow microphone access in the browser (the icon in the address bar), close other apps using the microphone, and try headphones |
| "You are number N in line" | All voice lines are busy. Keep the page open; the call starts automatically |
| The chat bubble does not appear on my website | Check the snippet is on the page and before `</body>`, then clear your site's cache. Use **Preview on this page** to confirm the widget itself works |
| A webhook shows failures in its Log | Check the address is reachable from the internet and the secret in your tool is current. Click **Test** after fixing it |
| "Can't reach the API" | The service is unavailable or your connection dropped. Try again in a moment |
| Integrations or Settings are read-only | Only workspace owners and admins can change them |
