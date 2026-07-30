/**
 * Cart state.
 *
 * A module-level reactive object rather than Pinia: the app has exactly one
 * piece of shared state, the components already use `inject` for everything
 * else, and Pinia is pure bundle weight for customers on metered data.
 *
 * The cart stores ONLY { pack, qty }. It never stores a price. Every amount
 * shown to the customer comes from the server's `quote()` response, and
 * `place_order` recomputes from scratch, so a tampered localStorage entry
 * changes nothing about what is charged.
 */

import { reactive, computed } from 'vue';

const STORAGE_KEY = 'prime_shito_cart_v1';

export interface CartLine {
	pack: string;
	qty: number;
}

interface CartState {
	lines: CartLine[];
	zone: string | null;
	fulfilmentType: 'Delivery' | 'Pickup';
}

function load(): CartState {
	const empty: CartState = { lines: [], zone: null, fulfilmentType: 'Delivery' };
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return empty;
		const parsed = JSON.parse(raw);
		if (!parsed || !Array.isArray(parsed.lines)) return empty;
		return {
			lines: parsed.lines
				.filter((l: any) => l && typeof l.pack === 'string' && Number(l.qty) > 0)
				.map((l: any) => ({ pack: l.pack, qty: Math.floor(Number(l.qty)) })),
			zone: typeof parsed.zone === 'string' ? parsed.zone : null,
			fulfilmentType: parsed.fulfilmentType === 'Pickup' ? 'Pickup' : 'Delivery'
		};
	} catch {
		// A corrupt or stale-schema cart must never break the storefront.
		return empty;
	}
}

const state = reactive<CartState>(load());

function persist() {
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
	} catch {
		/* private browsing / quota — the cart still works for this session */
	}
}

export const cart = {
	state,

	count: computed(() => state.lines.reduce((sum, l) => sum + l.qty, 0)),
	isEmpty: computed(() => state.lines.length === 0),

	qtyOf(pack: string): number {
		return state.lines.find((l) => l.pack === pack)?.qty ?? 0;
	},

	add(pack: string, qty = 1) {
		const existing = state.lines.find((l) => l.pack === pack);
		if (existing) {
			existing.qty += qty;
		} else {
			state.lines.push({ pack, qty });
		}
		persist();
	},

	setQty(pack: string, qty: number) {
		const next = Math.floor(Number(qty) || 0);
		const idx = state.lines.findIndex((l) => l.pack === pack);
		if (idx === -1) {
			if (next > 0) state.lines.push({ pack, qty: next });
		} else if (next <= 0) {
			state.lines.splice(idx, 1);
		} else {
			state.lines[idx].qty = next;
		}
		persist();
	},

	remove(pack: string) {
		const idx = state.lines.findIndex((l) => l.pack === pack);
		if (idx !== -1) state.lines.splice(idx, 1);
		persist();
	},

	setZone(zone: string | null) {
		state.zone = zone;
		persist();
	},

	setFulfilmentType(type: 'Delivery' | 'Pickup') {
		state.fulfilmentType = type;
		persist();
	},

	clear() {
		state.lines.splice(0, state.lines.length);
		persist();
	},

	/** Payload shape for quote() and place_order(). */
	payload(): CartLine[] {
		return state.lines.map((l) => ({ pack: l.pack, qty: l.qty }));
	}
};

export default cart;
