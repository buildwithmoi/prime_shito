/**
 * Storefront screenshots across the three viewports customers actually use.
 *
 *   yarn build && yarn screenshots
 *
 * Serves the real built bundle from prime_shito/public/shop/ and fulfils the
 * API from fixtures inside the browser, so no bench has to be running and the
 * data is identical on every run. Screenshots land in prime/screenshots/.
 *
 * It also reports console errors, horizontal overflow and small tap targets.
 * Overflow matters most at 375px: a body wider than the viewport is the most
 * common phone layout bug and it is invisible on a desktop monitor.
 */

import { chromium, devices } from 'playwright';
import { mkdir, rm, readFile } from 'node:fs/promises';
import path from 'node:path';
import { existsSync } from 'node:fs';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const DIST = path.join(ROOT, 'prime_shito', 'public', 'shop');
const SHELL = path.join(ROOT, 'prime_shito', 'www', 'shop.html');
const OUT = path.resolve(import.meta.dirname, '..', 'screenshots');

const ORIGIN = 'http://shop.test';

if (!existsSync(DIST)) {
	console.error(`No build found at ${DIST}. Run \`yarn build\` first.`);
	process.exit(1);
}

// Mirrors prime_shito/www/shop.py's storefront_context().
const STORE = {
	business_name: 'Prime Shito',
	tagline: "Ghana's finest shito, made fresh in small batches",
	about_text:
		'We make shito the slow way, in small batches, using dried fish and prawns from Ghanaian markets. Order ahead and we make yours fresh.',
	logo: null,
	hero_image: null,
	meta_description: 'Order Prime Shito online.',
	og_image: null,
	support_phone: '+233244000111',
	support_email: 'hello@primeshito.com',
	whatsapp_number: '233244000111',
	currency: 'GHS',
	is_store_open: 1,
	store_closed_message: null,
	min_order_amount: 45,
	max_qty_per_line: 50,
	allow_online_payment: 0,
	allow_pay_on_delivery: 1,
	delivery_lead_days: 2,
	paystack_public_key: null
};

const PACKS = [
	{
		pack: 'SHITO-CLASSIC-250',
		pack_name: 'Classic Shito 250g',
		route: 'classic-shito-250g',
		description: 'Our original recipe. Deep, smoky and properly hot.',
		long_description: null,
		// Deliberately no image: this is the fallback that used to be a chilli
		// emoji, and it needs to be visible in the screenshots.
		image: null,
		image_alt: null,
		flavour: 'Classic',
		heat_level: 'Hot',
		net_weight_g: 250,
		price: 45,
		compare_at_price: 0,
		min_order_qty: 1,
		max_order_qty: 0,
		is_featured: 1,
		sold_out: false
	},
	{
		pack: 'SHITO-BEEF-250',
		pack_name: 'Beef Shito 250g',
		route: 'beef-shito-250g',
		description: 'Slow-fried with shredded beef. Rich and filling.',
		long_description: null,
		image: null,
		image_alt: null,
		flavour: 'Beef',
		heat_level: 'Medium',
		net_weight_g: 250,
		price: 65,
		compare_at_price: 0,
		min_order_qty: 1,
		max_order_qty: 0,
		is_featured: 1,
		sold_out: false
	},
	{
		pack: 'SHITO-FISH-500',
		pack_name: 'Dried Fish Shito 500g',
		route: 'dried-fish-shito-500g',
		description: 'Loaded with dried herring and prawns. The family jar.',
		long_description: null,
		image: null,
		image_alt: null,
		flavour: 'Dried Fish',
		heat_level: 'Extra Hot',
		net_weight_g: 500,
		price: 110,
		compare_at_price: 130,
		min_order_qty: 1,
		max_order_qty: 0,
		is_featured: 0,
		sold_out: false
	}
];

const ZONES = [
	{
		zone: 'Accra Central',
		zone_name: 'Accra Central',
		region: 'Greater Accra',
		delivery_fee: 20,
		free_delivery_over: 200,
		min_order_amount: 0,
		estimated_days: 1,
		delivery_days: 'Monday to Saturday'
	},
	{
		zone: 'Greater Accra (Outskirts)',
		zone_name: 'Greater Accra (Outskirts)',
		region: 'Greater Accra',
		delivery_fee: 35,
		free_delivery_over: 300,
		min_order_amount: 0,
		estimated_days: 2,
		delivery_days: 'Monday to Saturday'
	},
	{
		zone: 'Kumasi',
		zone_name: 'Kumasi',
		region: 'Ashanti',
		delivery_fee: 50,
		free_delivery_over: 0,
		min_order_amount: 100,
		estimated_days: 3,
		delivery_days: 'Saturdays only'
	}
];

function quoteFor(items, zone) {
	const lines = (items || []).map((i) => {
		const pack = PACKS.find((p) => p.pack === i.pack);
		return {
			pack: i.pack,
			pack_name: pack?.pack_name ?? i.pack,
			image: pack?.image ?? null,
			qty: i.qty,
			rate: pack?.price ?? 0,
			amount: (pack?.price ?? 0) * i.qty,
			net_weight_g: pack?.net_weight_g ?? 0
		};
	});
	const items_total = lines.reduce((s, l) => s + l.amount, 0);
	const z = ZONES.find((x) => x.zone === zone);
	const free = z && z.free_delivery_over > 0 && items_total >= z.free_delivery_over;
	const delivery_fee = !z || free ? 0 : z.delivery_fee;
	return {
		lines,
		items_total,
		delivery_fee,
		discount_amount: 0,
		grand_total: items_total + delivery_fee,
		grand_total_pesewas: Math.round((items_total + delivery_fee) * 100),
		total_qty: lines.reduce((s, l) => s + l.qty, 0),
		currency: 'GHS',
		free_delivery_applied: Boolean(free),
		warnings: [],
		blocking_errors: [],
		is_orderable: lines.length > 0
	};
}

const TRACKED_ORDER = {
	tracking_code: 'PS-7K2M-9XQD',
	status: 'Out for Delivery',
	status_note: 'On the way to you today.',
	payment_status: 'Unpaid',
	payment_method: 'Pay on Delivery',
	placed_on: '2026-07-30 09:12:00',
	currency: 'GHS',
	items_total: 155,
	delivery_fee: 20,
	grand_total: 175,
	amount_paid: 0,
	amount_due: 175,
	fulfilment_type: 'Delivery',
	delivery_zone: 'Accra Central',
	preferred_delivery_date: null,
	customer_first_name: 'Ama',
	masked_phone: '+233 24 *** **56',
	address_preview: '12 Oxford Street, …',
	items: [
		{ pack_name: 'Classic Shito 250g', qty: 2, rate: 45, amount: 90, image: null },
		{ pack_name: 'Beef Shito 250g', qty: 1, rate: 65, amount: 65, image: null }
	],
	timeline: [
		{ label: 'Order placed', at: '2026-07-30 09:12:00', done: true },
		{ label: 'Approved', at: '2026-07-30 10:02:00', done: true },
		{ label: 'Out for delivery', at: '2026-07-30 11:40:00', done: true },
		{ label: 'Delivered', at: null, done: false }
	],
	is_open: true
};

const VIEWPORTS = [
	{ name: 'mobile', width: 375, height: 812, isMobile: true },
	{ name: 'tablet', width: 768, height: 1024, isMobile: false },
	{ name: 'desktop', width: 1440, height: 900, isMobile: false }
];

const SCENES = [
	{ path: '/', name: 'home' },
	{ path: '/packs', name: 'catalog' },
	{ path: '/packs/classic-shito-250g', name: 'pack-detail' },
	{ path: '/cart', name: 'cart-empty' },
	{ path: '/cart', name: 'cart-filled', cart: true },
	{ path: '/checkout', name: 'checkout-step1', cart: true },
	{ path: '/checkout', name: 'checkout-step3', cart: true, step: 3 },
	{ path: '/track', name: 'track-empty' },
	{ path: '/track', name: 'track-result', track: true },
	{ path: '/about', name: 'about' },
	{ path: '/contact', name: 'contact' },
	{ path: '/this-page-does-not-exist', name: 'not-found' }
];

const problems = [];
const note = (kind, where, detail) => problems.push({ kind, where, detail });

const MIME = {
	'.js': 'text/javascript',
	'.css': 'text/css',
	'.png': 'image/png',
	'.svg': 'image/svg+xml',
	'.woff2': 'font/woff2',
	'.json': 'application/json'
};

async function buildShell() {
	// The committed shop.html carries Jinja that Frappe would render; substitute
	// the same payload shop.py provides so the app boots identically.
	let html = await readFile(SHELL, 'utf8');
	const boot = { csrf_token: 'test', site_name: 'shop.test', socketio_port: null, store: STORE };
	html = html.replace(
		/\{%\s*if boot is defined\s*%\}[\s\S]*?\{%\s*endif\s*%\}/,
		`<script>window.csrf_token="test";window.__PRIME__=${JSON.stringify(boot)};</script>`
	);
	return html;
}

async function main() {
	const shell = await buildShell();
	const browser = await chromium.launch();
	await rm(OUT, { recursive: true, force: true });

	for (const viewport of VIEWPORTS) {
		const context = await browser.newContext({
			viewport: { width: viewport.width, height: viewport.height },
			deviceScaleFactor: 2,
			isMobile: viewport.isMobile,
			hasTouch: viewport.isMobile,
			userAgent: viewport.isMobile ? devices['iPhone 13'].userAgent : undefined
		});

		await context.route('**/*', async (route) => {
			const url = new URL(route.request().url());

			if (url.pathname.startsWith('/api/method/')) {
				const method = url.pathname.replace('/api/method/', '');
				let message = {};

				if (method.endsWith('get_storefront')) {
					message = { store: STORE, packs: PACKS, zones: ZONES };
				} else if (method.endsWith('get_pack')) {
					message = PACKS[0];
				} else if (method.endsWith('quote')) {
					const body = route.request().postDataJSON() || {};
					const items = typeof body.items === 'string' ? JSON.parse(body.items) : body.items;
					message = quoteFor(items, body.delivery_zone);
				} else if (method.endsWith('track_order')) {
					message = TRACKED_ORDER;
				} else if (method.endsWith('request_otp')) {
					message = { ok: true, expires_in: 300, resend_in: 60, masked_phone: '+233 24 *** **56' };
				} else if (method.endsWith('verify_otp')) {
					message = { ok: true, verification_token: 'tok', expires_in: 900 };
				}

				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ message })
				});
			}

			if (url.pathname.startsWith('/assets/prime_shito/shop/')) {
				const rel = url.pathname.replace('/assets/prime_shito/shop/', '');
				const file = path.join(DIST, rel);
				try {
					return route.fulfill({
						status: 200,
						contentType: MIME[path.extname(file)] || 'application/octet-stream',
						body: await readFile(file)
					});
				} catch {
					note('missing-asset', viewport.name, url.pathname);
					return route.fulfill({ status: 404, body: '' });
				}
			}

			// Every other path is an SPA route: serve the shell, as Frappe does.
			return route.fulfill({ status: 200, contentType: 'text/html', body: shell });
		});

		const dir = path.join(OUT, viewport.name);
		await mkdir(dir, { recursive: true });

		for (const scene of SCENES) {
			const page = await context.newPage();
			const where = `${viewport.name} ${scene.name}`;

			page.on('console', (m) => {
				if (m.type() === 'error') note('console', where, m.text().slice(0, 180));
			});
			page.on('pageerror', (e) => note('pageerror', where, String(e).slice(0, 180)));

			if (scene.cart) {
				await page.addInitScript(() => {
					localStorage.setItem(
						'prime_shito_cart_v1',
						JSON.stringify({
							lines: [
								{ pack: 'SHITO-CLASSIC-250', qty: 2 },
								{ pack: 'SHITO-BEEF-250', qty: 1 }
							],
							zone: 'Accra Central',
							fulfilmentType: 'Delivery'
						})
					);
				});
			}

			try {
				await page.goto(`${ORIGIN}${scene.path}`, { waitUntil: 'networkidle', timeout: 20000 });
			} catch (err) {
				note('navigation', where, String(err).slice(0, 140));
				await page.close();
				continue;
			}

			if (scene.track) {
				await page.fill('#code', 'PS-7K2M-9XQD');
				await page.fill('#last4', '4456');
				await page.click('button[type=submit]');
				await page.waitForTimeout(600);
			}

			if (scene.step === 3) {
				// Walk the real flow rather than poking internals, so the screenshot
				// reflects what a customer would actually see.
				await page.fill('#name', 'Ama Mensah');
				await page.fill('input[type=tel]', '241234567');
				await page.click('button[type=submit]');
				await page.waitForTimeout(500);
				await page.fill('input[autocomplete="one-time-code"]', '123456');
				await page.waitForTimeout(700);
			}

			await page.waitForTimeout(400);

			const overflow = await page.evaluate(() => {
				const doc = document.documentElement;
				const widest = [...document.querySelectorAll('body *')]
					.map((el) => {
						const r = el.getBoundingClientRect();
						return {
							right: Math.round(r.right),
							tag: el.tagName,
							cls: String(el.className || '').slice(0, 70)
						};
					})
					.filter((e) => e.right > doc.clientWidth + 1)
					.sort((a, b) => b.right - a.right)[0];
				return { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth, widest };
			});

			if (overflow.scrollWidth > overflow.clientWidth + 1) {
				note(
					'overflow',
					where,
					`${overflow.scrollWidth}px > ${overflow.clientWidth}px` +
						(overflow.widest ? ` — <${overflow.widest.tag}> .${overflow.widest.cls}` : '')
				);
			}

			// Text clipped inside an overflow-hidden ancestor. The document-level
			// overflow check above cannot see this: a card with `overflow-hidden`
			// silently cuts its contents while the page still measures clean. That
			// is exactly how a cart price rendered as "GHS 90.0".
			const clipped = await page.evaluate(() => {
				return [...document.querySelectorAll('span, p, h1, h2, h3, dd, dt, button, a')]
					.filter((el) => {
						if (!el.textContent?.trim()) return false;
						if (el.children.length) return false;
						// Horizontal clipping only; vertical is usually line-clamp by design.
						return el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0;
					})
					.map((el) => `"${el.textContent.trim().slice(0, 28)}" ${el.scrollWidth}>${el.clientWidth}px`)
					.slice(0, 5);
			});
			if (clipped.length) note('clipped-text', where, clipped.join(', '));

			if (viewport.isMobile) {
				// WCAG 2.5.8 (AA) sets 24x24 CSS px and explicitly exempts links
				// inline in a sentence, where enlarging the target would break the
				// text. 32px is used here as a stricter working floor for standalone
				// controls; inline prose links are skipped rather than reported as
				// noise nobody can act on.
				const small = await page.evaluate(() => {
					const isInlineInProse = (el) => {
						const parent = el.parentElement;
						if (!parent) return false;
						const own = (el.textContent || '').trim();
						const around = (parent.textContent || '').trim();
						// Parent carries text besides the link itself, or the link sits
						// inside a heading/paragraph as part of its content.
						return around.length > own.length + 2 || /^(P|H1|H2|H3|SPAN)$/.test(parent.tagName);
					};
					return [...document.querySelectorAll('a, button, select, input[type=submit]')]
						.filter((el) => {
							const r = el.getBoundingClientRect();
							return r.width > 0 && r.height > 0 && r.height < 32 && !isInlineInProse(el);
						})
						.map(
							(el) =>
								`<${el.tagName.toLowerCase()}>"${(el.textContent || '').trim().slice(0, 20)}" ${Math.round(
									el.getBoundingClientRect().height
								)}px`
						)
						.slice(0, 8);
				});
				if (small.length) note('tap-target', where, small.join(', '));
			}

			await page.screenshot({ path: path.join(dir, `${scene.name}.png`), fullPage: true });
			await page.close();
		}

		await context.close();
		console.log(`${viewport.name.padEnd(8)} ${SCENES.length} screens`);
	}

	await browser.close();

	console.log('\n' + '='.repeat(64));
	if (!problems.length) {
		console.log('Clean: no console errors, overflow, missing assets or small tap targets.');
	} else {
		const byKind = {};
		for (const p of problems) (byKind[p.kind] ||= []).push(p);
		for (const [kind, list] of Object.entries(byKind)) {
			console.log(`\n${kind.toUpperCase()} (${list.length})`);
			const seen = new Set();
			for (const p of list) {
				if (seen.has(p.detail)) continue;
				seen.add(p.detail);
				console.log(`  ${p.where}\n    ${p.detail}`);
			}
		}
	}
	console.log(`\nScreenshots: ${OUT}`);
}

await main();
