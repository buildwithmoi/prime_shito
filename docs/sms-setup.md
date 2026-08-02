# Turning on SMS

Prime Shito sends through **Frappe's built-in SMS Settings**, so there is no
custom gateway code to configure. Point SMS Settings at Arkesel and every order
notification, OTP and status update starts flowing.

Nothing is sent until you complete both steps below. Until then messages are
logged with their cost but not delivered, which is the safe default.

## 1. Frappe SMS Settings

Desk → search **SMS Settings** (Core).

| Field | Value |
|---|---|
| SMS Gateway URL | `https://sms.arkesel.com/sms/api` |
| Message Parameter | `sms` |
| Receiver Parameter | `to` |
| Use POST | unticked (Arkesel's v1 endpoint is GET) |

Then add these rows to the **Static Parameters** table:

| Parameter | Value | Header |
|---|---|---|
| `action` | `send-sms` | no |
| `api_key` | your Arkesel API key | no |
| `from` | your approved sender ID | no |

Frappe's sender loops **one HTTP request per recipient**. That is fine for order
notifications, which go to one person. Advertisement campaigns will need
Arkesel's bulk endpoint instead — that is a separate piece of work.

## 2. Prime Shito Settings

Desk → **Prime Shito Settings** → SMS tab.

- **Enable SMS** — on
- **Sender ID** — the same approved ID you put in `from` above
- **Sandbox Mode** — leave **on** until you have run the test below
- **Cost Per Segment** — roughly `0.03`, so the dashboard can price your usage
- **Daily Message Cap** — a ceiling that stops a runaway loop draining credit

## 3. Test before going live

1. With Sandbox on, place a test order. Check **Shito SMS Message** — you should
   see rows with status `Sandbox`, the message body, segment count and what it
   would have cost. Nothing was sent and nothing was billed.
2. Turn **Sandbox Mode** off.
3. Prime Shito Settings → **SMS → Send Test SMS**, to your own phone.
4. If it does not arrive, see below.

## When SMS does not arrive

**An unapproved sender ID is the usual cause, and it fails silently.** Arkesel
must approve the ID before it will deliver; until then messages are accepted by
the API and quietly dropped. Check the ID is approved in your Arkesel dashboard
and that it matches both `from` in SMS Settings and Sender ID here exactly.

Otherwise, in order:

- **Shito SMS Message** — a `Failed` row carries the gateway's own error.
- **Error Log** — search "Prime Shito".
- No rows at all → Enable SMS is off, or the number was suppressed (a blocked
  customer), or the daily cap was hit.
- Arkesel account balance.

## Keeping the bill down

One character outside the GSM-7 alphabet drops a message from 160 characters per
segment to 70, which roughly **doubles the cost of every message using it**. The
Ghana cedi sign is the trap, so templates write `GHS 120.00` rather than `₵120`.

This is enforced: Prime Shito Settings refuses to save a template containing such
a character. Use **SMS → Preview SMS Templates** to see each message rendered
against a real order with its exact segment count and cost before you send any of
it.

The dashboard carries **SMS Sent This Month** and **SMS Cost This Month**. Both
count only genuinely sent messages, so sandbox testing never inflates them.

## What gets sent, and when

| Trigger | Template |
|---|---|
| Phone verification at checkout | `tpl_otp` |
| Order placed | `tpl_order_received` |
| Staff clicks Approve | `tpl_order_approved` |
| Staff clicks Dispatch | `tpl_out_for_delivery` |
| Staff clicks Complete | `tpl_order_completed` |
| Order cancelled | `tpl_order_cancelled` |
| Any other state change | `tpl_status_update` |

Each is sent at most once per order, so a retried job or a repeated save cannot
text a customer twice about the same thing. Every message carries the tracking
code, which is what the customer needs to look the order up again.

Templates are Jinja fields on Prime Shito Settings, so wording can be changed
without a deploy.
