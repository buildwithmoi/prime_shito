# UI/UX brief — paste this into Claude Code in this repo

You are working on `prime_shito`, the Prime Shito storefront. Read `CLAUDE.md`
first — especially **Frontend conventions** and the SPA build section. Every
path below is relative to `prime/src/`.

This is a **UI/UX** task. Nothing here asks for a new feature, a new API, or a
change to pricing, orders, OTP or SMS. If you find yourself editing anything
under `prime_shito/` (the Python package), you have misread it — with one
exception, called out explicitly in Part 4.

Work through it in order; the parts build on each other. Commit in small,
legible steps. Run `yarn type-check` before each commit and `yarn build` before
the last one.

---

## The one finding everything else follows from

`src/style.css` defines the design system. It contains **15 colour tokens, one
font token, and nothing else**:

```css
@theme {
	--color-chili-50 … --color-chili-800;   /* 8 */
	--color-cream-50 … --color-cream-200;   /* 3 */
	--color-char-400 … --color-char-900;    /* 4 */
	--font-sans: system-ui, …;
}
```

Colour is the only thing this app has ever *named*. And colour is the only
thing in the app that is consistent — every button is `bg-chili-600`, every
border is `border-cream-200`, the contrast ratios are documented in a comment
and they hold up.

Everything the system did not name got improvised at the point of use. That is
the whole audit, and it shows up in exactly two places:

**Iconography was never named, so it became emoji.** `StateBlock.vue` types an
icon as a string of text:

```ts
emptyIcon: { type: String, default: '🌶️' }
```

There are now **14 emoji doing an icon's job across 8 files**.

**Motion was never named, so it became the default.** There are **37
`transition` classes with no duration**, and exactly **one** that names its own
(`PackCard.vue:12`, `duration-300`). Bare `transition` in Tailwind means 150 ms
`cubic-bezier(0.4, 0, 0.2, 1)` — so a button hover, a border colour, a card
shadow and a whole cart row all move at the same speed, because no one ever
chose a speed. And there are **zero `<Transition>` components in the app**, so
nothing that appears or disappears is animated at all.

**Do not fix these one file at a time.** Name the missing things in `@theme`
first, then apply them. Parts 1 and 2 are in that order for a reason.

Two things make this much less risky than it sounds:

- **The correct icon pattern already exists in this repo.** `AppHeader.vue`'s
  cart is a proper inline `<svg>` with `stroke="currentColor"`, and
  `WhatsAppFab.vue` has another. This is not a missing capability, it is an
  inconsistency — you are propagating a pattern the app already chose, twice.
- **The foundation is good.** Contrast is documented and passes,
  `prefers-reduced-motion` is already handled in `style.css`, focus-visible is
  styled, `StateBlock` already forces every view to handle loading/error/empty.
  You are not rebuilding. You are finishing.

---

## Part 1 — Icons: name them, then kill the emoji

### Why emoji are wrong here, specifically

Not taste. Four concrete reasons, in the order that matters for this business:

1. **They are not your brand.** 🌶️ is drawn differently by Apple, Google,
   Samsung, and Microsoft. The single most repeated visual element on the
   storefront is currently whatever the customer's phone vendor decided it
   looks like. A Samsung customer and an iPhone customer are looking at
   different products.
2. **Five of them are standing in for the product photo.** In `PackCard.vue`,
   `Cart.vue`, `PackDetail.vue` and `Track.vue`, when `pack.image` is missing
   the slot fills with a cartoon chilli. On a shop that sells food, the fallback
   for "no photo of the food" should not be a cartoon of a different food.
3. **They cannot be styled.** An emoji ignores `currentColor`, so it cannot
   pick up hover, disabled or dark states. Every icon in the app is stuck at
   whatever colour its vendor drew it.
4. **They sit on the text baseline.** `🌶️` and `✉️` carry a variation
   selector (U+FE0F) and render at inconsistent optical sizes, which is why
   they are wrapped in `place-items-center` boxes to fight them into alignment.

### What to do

**1. Add the missing tokens to `style.css`:**

```css
@theme {
	/* existing colour + font tokens stay exactly as they are */

	--size-icon-sm: 1rem;
	--size-icon-md: 1.25rem;
	--size-icon-lg: 1.5rem;
	--stroke-icon: 1.8;   /* matches AppHeader's cart, the existing precedent */
}
```

**2. Create `src/components/icons/` with one small `.vue` file per icon**, each
a bare `<svg>` on a 24×24 viewBox, `fill="none"`, `stroke="currentColor"`,
`stroke-width="1.8"`, `stroke-linecap="round"`, `stroke-linejoin="round"`.
Copy the geometry conventions from `AppHeader.vue`'s cart, which already gets
this right.

You need exactly these, and no more:

| Replaces | Icon | Used by |
|---|---|---|
| 🛒 | `IconCart` | `Cart.vue:7`, `Checkout.vue:75` — and reuse in `AppHeader` |
| 😕 | `IconAlert` | `StateBlock.vue:15` |
| 🔍 | `IconSearch` | `PackDetail.vue:8` |
| 💬 | `IconWhatsApp` | `Contact.vue:16` — reuse `WhatsAppFab`'s existing path |
| 📞 | `IconPhone` | `Contact.vue:28` |
| ✉️ | `IconMail` | `Contact.vue:40` |
| ✓ | `IconCheck` | `Checkout.vue:65`, `Track.vue:83` |

**3. Change the `StateBlock` contract.** This is the root fix:

```ts
// was: emptyIcon: { type: String, default: '🌶️' }
emptyIcon: { type: [Object, Function] as PropType<Component>, default: undefined }
```

Render it with `<component :is="emptyIcon">`. A `String` prop is what invited a
text character in; once the type is a component, an emoji cannot be passed
without a type error, and `yarn type-check` enforces it from then on.

**4. Delete these outright — they are decoration, not information:**

- `NotFound.vue:3` — the 🌶️ above "Page not found". The heading already says it.
- `Checkout.vue:5` — the 🎉 above "Order received". The customer just spent
  money and is looking for their tracking code; a party popper is the app
  celebrating itself. Lead with the tracking code instead.
- `Contact.vue` — the three tinted 44 px emoji tiles. Replace with the icons
  above at `--size-icon-md`, in `text-char-500`, and **drop the coloured tile
  backgrounds**; three different pastel chips for three rows of the same kind
  is noise. See Part 3.

**5. Replace the product-image fallback (the 5 chillies) with a real empty
state.** Not another glyph. A `bg-cream-100` block with the pack name set in
`text-char-400` at small size, centred. It reads as "photo coming" rather than
"this product is a cartoon", and it degrades honestly at every size from the
80 px cart thumbnail to the full `PackDetail` square.

**Verify Part 1:** `grep -rP '[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]' src/`
returns nothing.

---

## Part 2 — Motion: name it, then use it

### Add the tokens first

```css
@theme {
	--ease-out-soft: cubic-bezier(0.2, 0, 0, 1);
	--duration-fast: 120ms;    /* colour, border, opacity on hover/press */
	--duration-base: 200ms;    /* things entering or leaving the page */
	--duration-slow: 320ms;    /* the one deliberate flourish per screen */
}
```

Three durations, not five. If a fourth becomes necessary, something else is
wrong.

### Then apply them, in this order of value

**1. Route transitions.** `App.vue` renders `<router-view v-slot>` with no
transition, so every navigation is a hard cut. Wrap it:

```vue
<router-view v-slot="{ Component }">
	<Transition name="page" mode="out-in">
		<component :is="Component" @catalog-loaded="onCatalogLoaded" />
	</Transition>
</router-view>
```

`page-enter-from` / `page-leave-to`: `opacity: 0` plus `translateY(4px)`, at
`--duration-base`. Four pixels, not twenty — this is a shop on a phone, not a
presentation. `mode="out-in"` matters: without it the old and new page overlap
and the footer jumps.

**2. Cart add/remove.** `Cart.vue`'s item list is the one place in the app
where the user destroys something, and right now a row vanishes instantly with
no acknowledgement. Wrap the list in `<TransitionGroup name="row">` with a
leave transition at `--duration-base` and `position: absolute` on
`row-leave-active` so the rows below slide up rather than snap.

**3. The checkout step change.** `Checkout.vue` uses `v-show` on all four
fieldsets, which keeps every step mounted and makes a transition impossible —
`v-show` toggles `display`, and `display` cannot animate. Switch the four
fieldsets to `v-if` and wrap them in a `<Transition mode="out-in">`.

Read this one carefully before you do it: **`v-if` unmounts, so any state held
in a step's DOM is lost on the way back.** The form model lives in
`data().form`, so the values survive — but confirm `form.otp` and the
`resendIn` countdown still behave when moving 2 → 1 → 2 via "Change number".
If they do not, keep `v-show` and animate a wrapper instead. Working beats
animated.

**4. The one flourish.** `PackCard.vue` already has
`group-hover:scale-105 duration-300` on the image. Keep it, give it
`--ease-out-soft`, and leave it as the only scale transform in the app. One
signature move that appears everywhere beats five different ones.

**5. Sweep the 37 bare `transition`s.** Replace each with an explicit property
and duration — `transition-colors duration-[--duration-fast]` on hovers,
`transition-[border-color,box-shadow] duration-[--duration-fast]` on cards.
Bare `transition` animates a long property list including `transform` and
`filter`, which is wasted work on a low-end Android.

### Motion rules, non-negotiable

- **No animation library.** The JS budget is <150 KB gzipped and the app is at
  ~43 KB. Vue's built-in `<Transition>` and CSS cover everything above and cost
  nothing. Adding `@vueuse/motion`, GSAP or Framer would spend a quarter of the
  remaining budget on decoration for customers on metered data.
- **Only animate `transform` and `opacity`** for anything that moves. Animating
  `height`, `top` or `width` forces layout on every frame.
- **Nothing above 320 ms**, and nothing animates on first paint — a storefront
  that makes you wait to read it is slower than one that does not, no matter
  what the frame counter says.
- **`prefers-reduced-motion` is already handled** globally in `style.css` and
  that block is load-bearing. Do not remove it, and do not add motion that
  routes around it (e.g. JS-driven animation that ignores the media query).

---

## Part 3 — Simplify

Each of these removes something. None adds a screen.

**1. `Contact.vue` — three cards become one list.** Three rounded-2xl bordered
cards, each with its own coloured chip (`#25D366/10`, `bg-chili-50`,
`bg-cream-100`), for three items of identical importance. Three accent colours
in one viewport with no meaning attached to the difference. Make it one bordered
card with three rows, one icon treatment, `divide-y divide-cream-200`.

**2. `Checkout.vue` is 532 lines and holds four steps, a stepper, a summary
panel and all the submit logic.** Do not redesign the flow — the four steps are
correct and the OTP genuinely has to sit between details and payment. But
extract the order-summary `<section>` (lines ~266–285) into
`components/OrderSummary.vue`; `Cart.vue` renders the same totals with its own
copy of the markup, and the two are already drifting.

**3. `Checkout.vue`'s stepper labels are `hidden sm:inline`.** On a phone the
stepper is four numbered circles with no words — it says "4 steps" and nothing
about what they are, which raises abandonment rather than lowering it. Either
show the current step's label under the row on mobile, or drop the stepper on
mobile and show "Step 2 of 4 · Verify your number" as a single line.

**4. Buttons repeat one long class string ~15 times.** `h-12 … rounded-xl
bg-chili-600 … hover:bg-chili-700 disabled:…` appears in `Home`, `Cart`,
`Checkout`, `PackDetail`, `Track`, `About`, `NotFound`, `StateBlock`. Extract
`@utility btn-primary` / `btn-secondary` in `style.css` (Tailwind v4 supports
this — no config file needed). One definition also means the Part 2 duration
tokens land everywhere at once instead of 15 times by hand.

**5. Delete `views/About.vue`'s duplicate CTA if it repeats Home's.** Check
first; if the copy differs meaningfully, leave it.

---

## Part 4 — Two navigation holes

These are the only findings that are not cosmetic, and one of them costs orders.

**1. There is no navigation on mobile at all.** `AppHeader.vue:25` is
`hidden … sm:flex`, and there is no hamburger, drawer or bottom bar anywhere in
the app — `grep -rn "sm:hidden" src/` returns exactly one hit, and it is
`PackDetail`'s sticky buy bar. So on a phone the header is a logo and a cart
icon, and **Shop / About / Contact are unreachable from every page**. `CLAUDE.md`
says "Mobile-first is a requirement, not polish: most customers are on phones."

Fix it with the smallest thing that works. Given three links, a slide-over
drawer is overkill — put the three as a scrollable inline row under the header
bar on mobile, or add a bottom tab bar. Prefer the option that does not
introduce an open/close state.

**2. `/track` is reachable from nowhere.** It is a real route with a real view
and its own SMS integration, and it appears in neither the header links array
(`AppHeader.vue:66–70`) nor the footer (`AppFooter.vue:13–15`). A customer who
wants to check their order has to type the URL. Add **Track order** to the
footer's first list, and to the mobile nav from item 1.

While you are there, the footer lists "All packs / Your cart / About us" but
omits **Contact**, which the header has. Add it — the two menus should not
disagree about what the site contains.

**This is the one place you may touch Python.** If adding a nav link needs a new
client route, `CLAUDE.md` is explicit that `hooks.py` needs a matching
`website_route_rules` entry — there is deliberately no catch-all. The four
routes above all already exist, so you most likely need no backend change at
all. Do not add one speculatively.

---

## Leave these alone — they look wrong and are not

Checked during the audit; each has a reason:

- **`Checkout.vue:292`, `v-if="step > 1 && step !== 2"` on the Back button.**
  Back is deliberately hidden on the OTP step because that step has its own
  **"Change number"** button (line 133) which does the same job with a clearer
  label. Adding Back there gives two controls for one action.
- **Emoji wrapped in `aria-hidden="true"`.** Whoever added them handled screen
  readers correctly. You are removing the emoji, not fixing an a11y bug — do
  not "improve" the aria while you are in there.
- **`prime_shito/public/shop/` and `www/shop.html` committed to git.** Build
  artefacts in version control is normally a smell; here it is required, because
  Frappe does not run `yarn build` on deploy. See `CLAUDE.md`.
- **`StateBlock`'s three-state structure.** Loading / error / empty with a retry
  is right, and every view using it is right. Only the icon prop's *type*
  changes.
- **System fonts.** `--font-sans` is system-only on purpose: one web font weight
  is ~30 KB on a metered Ghanaian mobile plan. Do not add a display face for
  headings, however much better the hero would look.

---

## Verification

Run all of these before saying it is done:

```bash
cd prime
yarn type-check                       # must be clean; it enforces the icon prop type
grep -rP '[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]' src/   # must return nothing

# Bare transitions. Returns 37 today; should be near zero when Part 2 is done.
grep -ro 'transition\b[^"]*' --include="*.vue" src/ | grep -v duration- | wc -l
yarn build                            # then COMMIT the output — see CLAUDE.md
```

Then check the gzipped bundle has not regressed past **~50 KB** (budget is
150 KB; it was ~43 KB before this work). If icons pushed it up more than a few
KB, you have added too many.

By hand, at 375 px wide with the network throttled:

1. Every nav destination reachable from a phone, on every page.
2. Home → Packs → Pack → Cart → Checkout with no hard cuts between pages.
3. Remove a cart row: the rows below slide up, they do not snap.
4. Turn on "Reduce motion" in the OS and repeat 2 and 3 — everything must still
   work, just instantly.
5. A pack with no image, in all four places it appears — card, cart row, detail,
   tracking. None of them shows a chilli.

---

## What "done" looks like

Not "the app has animations". Done is:

- `style.css` names every dimension the app varies — colour, icon size, stroke,
  duration, easing — so the *next* change picks from a list instead of inventing
  a number.
- No customer sees a glyph the shop did not draw.
- A customer on a phone can reach every part of the shop, including their own
  order.
- Motion is invisible. If someone notices the animation, it is too slow.
