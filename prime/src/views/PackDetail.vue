<template>
	<div>
		<StateBlock
			v-if="loading || error || !pack"
			:loading="loading"
			:error="error"
			loading-text="Loading this pack…"
			empty-icon="🔍"
			empty-title="We could not find that pack"
			empty-text="It may have been renamed or is no longer sold."
		>
			<template #empty-action>
				<router-link
					to="/packs"
					class="mt-5 inline-flex h-11 items-center rounded-xl bg-chili-600 px-5 text-sm font-semibold text-white transition hover:bg-chili-700"
				>
					See all packs
				</router-link>
			</template>
		</StateBlock>

		<div v-else class="mx-auto max-w-5xl px-4 py-8 pb-28 sm:pb-8">
			<nav class="mb-6 text-sm text-char-400">
				<router-link to="/packs" class="hover:text-chili-700">Packs</router-link>
				<span class="mx-2" aria-hidden="true">/</span>
				<span class="text-char-700">{{ pack.pack_name }}</span>
			</nav>

			<div class="grid gap-8 md:grid-cols-2">
				<div class="space-y-3">
					<div class="aspect-square overflow-hidden rounded-2xl bg-cream-100">
						<img
							v-if="activeImage"
							:src="activeImage"
							:alt="pack.pack_name"
							class="h-full w-full object-cover"
							width="600"
							height="600"
						/>
						<div v-else class="grid h-full w-full place-items-center text-7xl" aria-hidden="true">🌶️</div>
					</div>

					<div v-if="images.length > 1" class="flex gap-3">
						<button
							v-for="img in images"
							:key="img"
							type="button"
							class="h-20 w-20 overflow-hidden rounded-xl border-2 transition"
							:class="activeImage === img ? 'border-chili-600' : 'border-cream-200'"
							@click="activeImage = img"
						>
							<img :src="img" alt="" class="h-full w-full object-cover" loading="lazy" />
						</button>
					</div>
				</div>

				<div>
					<h1 class="text-3xl font-bold tracking-tight text-char-900">{{ pack.pack_name }}</h1>

					<div class="mt-3 flex flex-wrap items-center gap-2">
						<span
							v-if="pack.flavour"
							class="rounded-full bg-cream-100 px-3 py-1 text-xs font-medium text-char-700"
						>
							{{ pack.flavour }}
						</span>
						<span
							v-if="pack.heat_level"
							class="rounded-full bg-chili-50 px-3 py-1 text-xs font-medium text-chili-700"
						>
							{{ pack.heat_level }}
						</span>
						<span
							v-if="pack.net_weight_g"
							class="rounded-full bg-cream-100 px-3 py-1 text-xs font-medium text-char-700"
						>
							{{ pack.net_weight_g }}g
						</span>
					</div>

					<div class="mt-5 flex items-baseline gap-3">
						<span class="text-3xl font-bold text-char-900">{{ money(pack.price) }}</span>
						<span v-if="hasDiscount" class="text-lg text-char-400 line-through">
							{{ money(pack.compare_at_price) }}
						</span>
					</div>

					<p v-if="pack.description" class="mt-4 text-char-500">{{ pack.description }}</p>
					<!-- eslint-disable-next-line vue/no-v-html -->
					<div
						v-if="pack.long_description"
						class="prose prose-sm mt-4 max-w-none text-char-500"
						v-html="pack.long_description"
					/>

					<p v-if="pack.sold_out" class="mt-6 rounded-xl bg-cream-100 px-4 py-3 text-sm text-char-700">
						This pack is sold out. We are making more.
					</p>

					<div v-else class="mt-7 hidden items-center gap-3 sm:flex">
						<QtyStepper v-model="qty" :min="minQty" :max="maxQty" :label="pack.pack_name" />
						<button
							type="button"
							class="h-12 flex-1 rounded-xl bg-chili-600 px-6 font-semibold text-white transition hover:bg-chili-700"
							@click="addToCart"
						>
							{{ added ? 'Added to cart' : `Add to cart — ${money(pack.price * qty)}` }}
						</button>
					</div>

					<p v-if="pack.min_order_qty > 1" class="mt-3 text-xs text-char-400">
						Sold in a minimum of {{ pack.min_order_qty }}.
					</p>
				</div>
			</div>
		</div>

		<!-- Mobile sticky action bar: the primary action stays reachable with a
		     thumb without scrolling back up. -->
		<div
			v-if="pack && !pack.sold_out"
			class="fixed inset-x-0 bottom-0 z-30 border-t border-cream-200 bg-white/95 p-3 backdrop-blur sm:hidden"
			style="padding-bottom: calc(0.75rem + env(safe-area-inset-bottom))"
		>
			<div class="flex items-center gap-3">
				<QtyStepper v-model="qty" :min="minQty" :max="maxQty" :label="pack.pack_name" />
				<button
					type="button"
					class="h-12 flex-1 rounded-xl bg-chili-600 px-4 font-semibold text-white transition hover:bg-chili-700"
					@click="addToCart"
				>
					{{ added ? 'Added' : `Add — ${money(pack.price * qty)}` }}
				</button>
			</div>
		</div>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import QtyStepper from '../components/QtyStepper.vue';
import StateBlock from '../components/StateBlock.vue';
import cart from '../stores/cart';
import call from '../lib/call';
import { money } from '../lib/money';
import { store } from '../lib/boot';
import { state as sf, loadStorefront, packByRoute } from '../lib/storefront';
import type { Pack } from '../lib/types';

export default defineComponent({
	name: 'PackDetailView',
	components: { QtyStepper, StateBlock },
	props: {
		route: { type: String, required: true }
	},
	emits: ['catalog-loaded'],
	data() {
		return {
			pack: null as Pack | null,
			activeImage: null as string | null,
			qty: 1,
			loading: true,
			error: null as string | null,
			added: false,
			timer: 0 as unknown as ReturnType<typeof setTimeout>
		};
	},
	computed: {
		images(): string[] {
			if (!this.pack) return [];
			return [this.pack.image, this.pack.image_alt].filter((i): i is string => Boolean(i));
		},
		hasDiscount(): boolean {
			return Number(this.pack?.compare_at_price) > Number(this.pack?.price);
		},
		minQty(): number {
			return Math.max(this.pack?.min_order_qty || 1, 1);
		},
		maxQty(): number {
			const perLine = store.max_qty_per_line || 50;
			const perPack = this.pack?.max_order_qty || 0;
			return perPack > 0 ? Math.min(perLine, perPack) : perLine;
		}
	},
	watch: {
		route: {
			immediate: true,
			handler() {
				this.fetch();
			}
		}
	},
	methods: {
		money,
		async fetch() {
			this.loading = true;
			this.error = null;

			// Prefer the already-loaded catalog; fall back to a direct lookup so a
			// deep link shared on WhatsApp still resolves.
			await loadStorefront();
			if (sf.packs.length) this.$emit('catalog-loaded', sf.packs);

			let found = packByRoute(this.route);

			if (!found) {
				try {
					found = await call<Pack>('prime_shito.api.catalog.get_pack', { pack: this.route });
				} catch (err) {
					this.error = null; // treated as "not found" rather than an error state
				}
			}

			this.pack = found ?? null;
			this.activeImage = found?.image ?? null;
			this.qty = this.minQty;
			this.loading = false;
		},
		addToCart() {
			if (!this.pack) return;
			cart.setQty(this.pack.pack, cart.qtyOf(this.pack.pack) + this.qty);
			this.added = true;
			clearTimeout(this.timer);
			this.timer = setTimeout(() => (this.added = false), 1600);
		}
	},
	beforeUnmount() {
		clearTimeout(this.timer);
	}
});
</script>
