/**
 * Shared catalog loader.
 *
 * The storefront payload (config, packs, zones) is small and changes rarely, so
 * it is fetched once per page load and shared. Without this, navigating
 * Home -> Catalog -> Pack would issue three identical requests on a connection
 * where each one is expensive.
 */

import { reactive } from 'vue';
import call from './call';
import type { Pack, Storefront, Zone } from './types';

interface StorefrontState {
	loaded: boolean;
	loading: boolean;
	error: string | null;
	packs: Pack[];
	zones: Zone[];
}

export const state = reactive<StorefrontState>({
	loaded: false,
	loading: false,
	error: null,
	packs: [],
	zones: []
});

let inflight: Promise<void> | null = null;

export function loadStorefront(force = false): Promise<void> {
	if (state.loaded && !force) return Promise.resolve();
	if (inflight) return inflight;

	state.loading = true;
	state.error = null;

	inflight = call<Storefront>('prime_shito.api.catalog.get_storefront')
		.then((data) => {
			state.packs = data?.packs ?? [];
			state.zones = data?.zones ?? [];
			state.loaded = true;
		})
		.catch((err: Error) => {
			state.error = err.message || 'We could not load the shop.';
		})
		.finally(() => {
			state.loading = false;
			inflight = null;
		});

	return inflight;
}

export function packByRoute(route: string): Pack | undefined {
	return state.packs.find((p) => p.route === route || p.pack === route);
}

export function packByCode(code: string): Pack | undefined {
	return state.packs.find((p) => p.pack === code);
}
