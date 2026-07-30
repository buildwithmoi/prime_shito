/**
 * Server-rendered boot payload.
 *
 * `prime_shito/www/shop.py` renders this into the page as `window.__PRIME__`,
 * so the first paint already knows the business name, currency and whether the
 * store is open, with no round trip.
 */

export interface StoreConfig {
	business_name: string;
	tagline: string | null;
	about_text: string | null;
	logo: string | null;
	hero_image: string | null;
	meta_description: string | null;
	og_image: string | null;
	support_phone: string | null;
	support_email: string | null;
	whatsapp_number: string | null;
	currency: string;
	is_store_open: number;
	store_closed_message: string | null;
	min_order_amount: number;
	max_qty_per_line: number;
	allow_online_payment: number;
	allow_pay_on_delivery: number;
	delivery_lead_days: number;
	paystack_public_key: string | null;
}

export interface Boot {
	csrf_token?: string;
	site_name?: string;
	socketio_port?: number | null;
	read_only_mode?: boolean;
	store: StoreConfig;
}

const FALLBACK_STORE: StoreConfig = {
	business_name: 'Prime Shito',
	tagline: null,
	about_text: null,
	logo: null,
	hero_image: null,
	meta_description: null,
	og_image: null,
	support_phone: null,
	support_email: null,
	whatsapp_number: null,
	currency: 'GHS',
	is_store_open: 1,
	store_closed_message: null,
	min_order_amount: 0,
	max_qty_per_line: 50,
	allow_online_payment: 0,
	allow_pay_on_delivery: 1,
	delivery_lead_days: 2,
	paystack_public_key: null
};

const injected = (window as any).__PRIME__ as Boot | undefined;

// The dev server serves index.html directly, without Jinja, so the payload is
// absent there. Falling back keeps `yarn dev` usable; get_storefront() then
// supplies the real values.
export const boot: Boot = injected?.store
	? injected
	: { store: FALLBACK_STORE, socketio_port: null };

export const store = boot.store;
