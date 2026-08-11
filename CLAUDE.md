# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`prime_shito` is a Frappe v16 app for **Prime Shito**, a Ghanaian manufacturer of shito (pepper
sauce). It is an online pre-order storefront: customers browse packs, order ahead of production, pay
online or on delivery, get SMS at each step, and look up their own order by tracking code. The
business owner works out of the Frappe Desk.

The app lives inside a bench at `/home/patoo/fb-16-2` alongside `frappe` and `erpnext`. Two halves:

- `prime_shito/` — the Python package Frappe loads.
- `prime/` — a Vue 3 + TypeScript + Vite SPA. **It is the site's home page**, not a sub-route.

Currency is **GHS** throughout. The business is **not VAT-registered**, so there are no tax lines.

## Commands

Backend commands run from the **bench root** (`/home/patoo/fb-16-2`); frontend from `prime/`.
The site is `local.16.2` (web 8002, socketio 9002) and `developer_mode` is on.

```bash
# bench root
bench --site local.16.2 migrate                 # sync doctype JSON -> DB
bench --site local.16.2 clear-website-cache     # after changing www/ or hooks
bench --site local.16.2 execute prime_shito.install.create_demo_data
bench --site local.16.2 run-tests --module prime_shito.prime_shito.doctype.shito_pack.test_shito_pack

# app root
cd prime && yarn build       # -> prime_shito/public/shop/ + prime_shito/www/shop.html
cd prime && yarn dev         # vite on :8080, proxied to the bench
cd prime && yarn type-check  # vue-tsc; catches real bugs, run before committing
cd prime && yarn screenshots # Playwright, 3 viewports; see Screenshots below

# lint (matches CI's pre-commit)
/home/patoo/fb-16-2/env/bin/python -m ruff check prime_shito/
/home/patoo/fb-16-2/env/bin/python -m ruff format prime_shito/
```

**`yarn build` needs Node 20+** (Vite 8's bundler imports `node:util`'s `styleText`). If the shell
defaults to Node 18 it dies with an unhelpful `SyntaxError`; run `nvm use 24` first.

**`bench build` is not needed for the SPA.** `sites/assets/prime_shito` is already a symlink to
`prime_shito/public/`, so `yarn build` output is served immediately. Only run it if you add
`public/js` esbuild bundles.

## Architecture

### The SPA is the website root

Four coupled pieces — changing one without the others breaks the site:

1. `prime/vite.config.ts` builds to `prime_shito/public/shop/` with base `/assets/prime_shito/shop/`.
2. `prime/package.json`'s `copy-html-entry` copies the built `index.html` to
   `prime_shito/www/shop.html`, making `shop` a Frappe website page.
3. `hooks.py` sets `home_page = "shop"` plus **explicit** `website_route_rules` for `/packs`,
   `/cart`, `/checkout`, `/track`, etc. Deliberately not a `/<path:app_path>` catch-all — that would
   shadow `/login`, `/me`, ERPNext's `/orders` portal and every future `www/` page, and would defeat
   Frappe's 404 caching. **Adding a client route means adding a rule here too.**
4. `prime_shito/www/shop.py` renders the boot payload and `context.metatags`.

`prime/src/router/index.ts` uses `createWebHistory('/')` to match.

### Built assets are committed

`prime_shito/public/shop/` and `prime_shito/www/shop.html` are in git on purpose: Frappe does not run
the app's `yarn build` during deploy, so without them a fresh clone serves a broken home page.
**After changing anything under `prime/src/`, run `yarn build` and commit the output**, or the
deployed site silently keeps the old bundle.

### Money has exactly one authority

`prime_shito/shito/pricing.py::compute()` is the only place a price is decided. Both `quote()` (what
the cart calls on every change) and order placement go through it, so the cart can never disagree
with what is charged.

It **never** reads a rate, amount, fee or total from a request — only `[{pack, qty}]`. Order
controllers call `pricing.apply_to_order()` unconditionally in `validate()`, including on staff saves
in Desk. Marking a field `read_only` in DocType JSON does *not* stop an API caller from setting it;
only recomputation does. Amounts destined for a payment gateway use `grand_total_pesewas`, an integer
in minor units.

### Guest API rules

Endpoints live in `prime_shito/api/`. Frappe guest sessions carry **no persisted CSRF token**, so
CSRF protects nothing here — rate limiting and server-side recomputation carry the whole load.

- `@frappe.whitelist(allow_guest=True, methods=[...])` with `@rate_limit(...)` stacked underneath.
  Note the import is `from frappe.rate_limiter import rate_limit`; there is no `frappe.rate_limit`.
- Return explicit projections, never a Document or `as_dict()` — `Shito Pack` carries stock counters
  and `Prime Shito Settings` carries API secrets.
- No new doctype gets a Guest or All role. Guests reach data only through whitelisted projections.
- Never whitelist anything that takes a doctype name, fieldname or filter dict from the caller.

### Orders: two transition paths that must not drift

`Shito Order` is **not submittable**. It uses a Frappe Workflow purely for Desk
UX (action buttons, role gating); every state is `doc_status = 0`. The submittable
accounting artefact is the downstream ERPNext Sales Order.

State changes happen two ways, and they cannot share a mechanism:

- **Humans** click Approve/Dispatch/Complete in Desk → the Workflow, which checks
  `Workflow Transition.allowed` against `frappe.session.user`.
- **Machines** (payment callbacks, the expiry job) → `shito/state.py::transition()`,
  which validates against the `ALLOWED` dict and saves as Administrator, because a
  webhook running as Guest holds no workflow role.

`ALLOWED` mirrors the Workflow record, and `test_shito_order.py::TestWorkflowParity`
asserts they agree. **If you add a state or transition, change both.**

Two Frappe constraints worth knowing before editing the workflow:

- **The first state in `WORKFLOW_STATES` is where new orders start.** Frappe refuses
  on insert to set any other state, and that check ignores roles entirely — there is
  no flag or permission that bypasses it. `Awaiting Approval` must stay first.
- `install.py::create_workflow()` rebuilds an existing workflow rather than skipping
  it, so edits to those tables reach an installed site on the next migrate.

Payment progress lives in `payment_status` (Unpaid/Pending/Paid/…), not in the
workflow state. An unpaid online order is (Awaiting Approval, Pending).

### Naming from a field runs before validate()

`Shito Customer` uses `autoname: field:phone`, so the phone number *is* the primary
key and duplicates are impossible at the database level. That guarantee only holds
because normalisation happens in **`before_naming()`**, not `validate()` — Frappe
derives the name first, so validating later would name the record from whatever raw
string was typed ("024 111 2223" alongside "+233241112223" = two records, one person).
Any future `field:`-named doctype needs the same treatment.

### OTP is the main cost-attack surface

Each `request_otp` spends real money. The defences are layered because each is
individually defeatable: per-phone rate limit, per-IP rate limit, per-phone daily
cap, and a **global daily budget** in Redis — the last one is what stops a
distributed attack, which defeats both per-key limits by spreading requests.

Codes are stored as `sha256(salt + code)`, compared with `hmac.compare_digest`, and
the attempt counter increments *before* the comparison so a crash cannot buy free
guesses. Verification tokens are single-use and burnt by `place_order`.

With `developer_mode` on and `otp_echo_in_dev` set, `request_otp` returns the code
in its response so local testing burns no SMS credit.

### Order tracking must not leak

`track_order` requires the tracking code **and** the last 4 phone digits. Wrong
digits and an unknown code return an identical message *and* are padded to the same
duration (`LOOKUP_FLOOR_SECONDS`), so neither can be enumerated by response
differential. The response is a redacted projection: first name only, masked phone,
truncated address. Never widen it to return the document.

### SMS costs real money — keep messages GSM-7

`prime_shito/shito/gsm.py` exists because one character outside the GSM-7 alphabet drops an SMS from
160 characters per segment to 70, roughly doubling the cost of **every** message using it. The Ghana
cedi sign is the trap. **Always write `GHS 120.00`, never `₵`.**

This is enforced: `Prime Shito Settings.validate()` rejects non-GSM-7 characters in any `tpl_*`
template, `pricing.money()` avoids `frappe.utils.fmt_money` (which prefixes the symbol), and a test
asserts customer-facing error copy stays GSM-7. Any new customer-facing string must hold that line.

SMS goes through **Frappe's built-in SMS Settings** (Core > SMS Settings) pointed at Arkesel's HTTP
API — not a custom gateway. The built-in sender loops one HTTP request per recipient, which is fine
at this business's list sizes; Arkesel's bulk endpoint is the optimisation if campaigns reach
thousands.

### Marketing SMS is consent-gated, in SQL

`shito/campaigns.py` filters `marketing_opt_in = 1 AND is_blocked = 0` **inside the query**, never in
Python, so there is no code path that can forget the check. That includes the Manual List audience: a
hand-typed number that has unsubscribed stays unsubscribed, and a number never seen before gets
nothing, because it has given no consent at all. Consent is re-checked at send time as well as at
preview, since someone may opt out between the two.

Transactional order SMS is contractual and carries no opt-out footer. Marketing SMS always does, and
that footer is included when the message is priced because the customer pays for those characters
too. `unsubscribe()` is guest-accessible on purpose — an opt-out behind a login is not an opt-out —
and answers identically for known and unknown numbers so it cannot be used to probe who has ordered.

Campaigns never send on a single click: **Preview Recipients** resolves the audience and shows count,
segments and estimated cost, then sending needs `SEND` typed into a dialog. Sends commit per
recipient, so a job that dies halfway resumes without texting anyone twice.

### The doppio libs are vendored, not imported

`prime/src/lib/` holds our own `call.ts`, `socket.ts` and `boot.ts`. Do **not** reintroduce
`../../../doppio/` imports. Three reasons they were removed:

- doppio is not in the site's `installed_apps`; the imports only resolved because a sibling directory
  happened to exist in this bench, so any clean checkout failed to build.
- doppio's `call.js` redirects to `/login` on any 401/403. Its guard reads
  `router.currentRoute.name`, but on vue-router 4 `currentRoute` is a `Ref`, so `.name` is always
  `undefined` and the guard never fires — it bounced shoppers to a dead route. Ours throws instead.
- doppio's `socket.js` hardcodes port 9000; this bench uses 9002. Ours reads it from the boot payload.

### Frontend conventions

Options API with `defineComponent`, Tailwind v4 via `@tailwindcss/vite` (CSS-first `@theme` tokens in
`src/style.css`, no `tailwind.config.js`). Cart state is a module-level `reactive()` in
`src/stores/cart.ts`, not Pinia.

**The cart stores only `{pack, qty}` — never a price.** Displayed money comes from the last `quote()`.

Gotcha worth knowing: do not put the `cart` object into a component's `data()`. Vue's reactive proxy
auto-unwraps nested refs, so `cart.isEmpty` silently becomes a boolean while template code still
reads `.value` off it, yielding `undefined`. Expose it through `computed` instead. `vue-tsc` catches
this, which is why `yarn type-check` is worth running.

Mobile-first is a requirement, not polish: most customers are on phones with metered data. System
fonts only, route-level code splitting, `build.target: es2020`. Budget is **<150 KB gzipped JS** for
first paint (currently ~47 KB).

Everything the app varies is a token in `src/style.css` — colour, icon size, icon stroke, three
durations, one easing curve. Pick from that list rather than inventing a number. Icons are inline
SVGs in `src/components/icons/`; **never an emoji**, which renders as whatever the customer's phone
vendor drew and cannot take `currentColor`. `StateBlock`'s `emptyIcon` prop is typed as a Component
specifically so `yarn type-check` rejects a string.

Naming a `@utility` after a Tailwind namespace silently breaks it. `@utility stroke-icon` compiled to
`stroke: var(--stroke-icon)` — Tailwind owns `stroke-*` for stroke *colours* — which set the colour
to `1.8`, resolved to `stroke: none`, and rendered every icon blank. It is `icon-stroke` now.

### Screenshots

```bash
cd prime && yarn build && yarn screenshots
```

Drives the built bundle in Playwright at 375 / 768 / 1440 with the API stubbed from fixtures, so it
needs no running bench and gives identical output every run. Writes to `prime/screenshots/`
(gitignored) and fails loudly on console errors, horizontal overflow, text clipped inside an
`overflow-hidden` ancestor, and sub-32px tap targets.

The clipping check exists because a card with `overflow-hidden` silently cut a cart price to
"GHS 90.0" while the page still measured clean — document-level overflow cannot see that.

## Testing

Frappe test files must live next to a doctype. Order/pricing tests are in
`prime_shito/prime_shito/doctype/shito_pack/test_shito_pack.py`.

Every test module for a doctype with ERPNext links needs `IGNORE_TEST_RECORD_DEPENDENCIES`. Without
it, Frappe auto-generates test records for linked doctypes, which imports ERPNext's test modules —
and `erpnext/tests/utils.py` instantiates `BootStrapTestData()` at module scope, which tries to
recreate the `Standard Buying` price list in INR and crashes on any site that already has one.

The dependency walk is **recursive and reads the ignore list from each doctype's own test module**.
So listing a doctype in one file does not protect the doctypes it links to: `Shito Customer` needed
its own `test_shito_customer.py` with an ignore list purely because its `erp_customer` link would
otherwise drag ERPNext in. If a new suite fails with a `Standard Buying` duplicate-entry error, this
is why.

CI's "Find tests" step runs `grep -rn "def test"` and fails the whole job if the repo has no tests, so
never let the suite reach zero.

## ERPNext integration

ERPNext **is** fully set up on this bench: Company "Prime Shito" (`PS`), GHS, Ghana, `Standard
Selling` price list, warehouses `Finished Goods - PS` / `Stores - PS`, receivable
`1310 - Debtors - PS`, cost center `Main - PS`, Item Group `Products`, Territory `Ghana`.
`install.py` adds the missing "Mobile Money" and "Pay on Delivery" Modes of Payment.

The planned order sync is **fail-soft by design**: it is enqueued with `enqueue_after_commit=True`,
never raises into the order transaction, and records `sync_status = Skipped/Failed` instead. An order
must never fail because ERPNext posting failed. Packs sync as `is_stock_item = 0` by default so Sales
Order submission cannot fail on missing stock or valuation.

There is **no Email Account** configured, so the app is SMS-only; do not add email receipts without
setting one up first.

## Conventions

- **Python is tab-indented**, double-quoted, 110 columns, ruff-formatted, targeting py3.14.
- Phone numbers: always normalise through `prime_shito/shito/phone.py`, which is Ghana-only by
  design. Frappe's own `validate_phone_number_with_country_code` accepts international premium-rate
  numbers, which on an OTP endpoint is a way for an attacker to run up an SMS bill.
- Patches go in `prime_shito/patches.txt`.
