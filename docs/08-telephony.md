# 08 — Telephony & Transport

Two ways audio reaches the agent: **browser mic** (free, for testing) and **phone/PSTN** (go-live).
Both terminate in a LiveKit room the agent worker joins. Telephony vendors sit behind `ofd.telephony`.

## 1. Browser testing (FREE — the key to $0 demos)
- Dashboard test console requests a LiveKit token from `GET /livekit/token` (scoped to a test room).
- Browser connects via WebRTC; the agent joins the same room. **No phone number, no PSTN cost.**
- This is how onboarding "Talk to your agent" works and how the whole demo is shown for free.

## 2. Going live with a real number
Options, in order of client-friendliness:
1. **Forward existing line** — client sets call-forwarding from their current business number to the
   OpenFrontDesk number. Zero porting, keeps their number. Recommended default.
2. **Buy a new number** — provision via Telnyx/Twilio, use directly or forward.
3. **Port the number** — later; more involved.

## 3. Inbound routing
```
PSTN call → SIP trunk (Telnyx/Twilio) → LiveKit SIP → LiveKit room (metadata: dialed number)
         → agent worker resolves dialed number → phone_number row → tenant + agent config
```
- `phone_number.e164` is the routing key → tenant/agent. Unknown number → safe default/decline.

## 4. Provider abstraction (`ofd.telephony`)
```python
class TelephonyProvider(Protocol):
    async def provision_number(self, area_code) -> NumberInfo: ...
    async def configure_sip(self, number, livekit_sip_uri) -> None: ...
class SMSProvider(Protocol):
    async def send_sms(self, to, body, *, from_=None) -> SMSResult: ...
```
Selected by `TELEPHONY_PROVIDER` / `SMS_PROVIDER`. `none` (default) disables — testing still works.

## 5. Cost (see [12-costing](12-costing.md))
- Telnyx inbound ≈ **$0.002/min** + ~$1/mo/number (cheapest). Twilio ≈ $0.0085/min.
- LiveKit Build free tier: 1,000 agent-min + 5,000 WebRTC-min/mo, no card.

## 6. SMS
- Post-call confirmations/follow-ups via `SMSProvider`, sent from a background job (never blocks the call).
- Opt-out handling + rate limits per tenant.

## 7. Consent & recording
- Optional per-tenant recording; a consent line can be played at call start (region-configurable).
- Consent state stored on the call. See [13](13-security-compliance.md).
