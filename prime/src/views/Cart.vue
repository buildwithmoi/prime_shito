<template>
	<div class="mx-auto max-w-3xl px-4 py-8">
		<h1 class="text-3xl font-bold tracking-tight text-char-900">Your cart</h1>

		<StateBlock
			v-if="isEmpty"
			:empty-icon="IconCart"
			empty-title="Your cart is empty"
			empty-text="Add a pack and it will show up here."
		>
			<template #empty-action>
				<router-link
					to="/packs"
					class="btn-primary mt-5 h-11 px-5 text-sm"
				>
					Browse packs
				</router-link>
			</template>
		</StateBlock>

		<div v-else class="mt-6 space-y-6">
			<!-- Removing a row is the one destructive action in the shop, so it is
			     acknowledged: the row fades out and the ones below slide up rather
			     than snapping. `relative` gives the absolutely-positioned leaving
			     row something to anchor to. -->
			<TransitionGroup
				tag="ul"
				name="row"
				class="relative divide-y divide-cream-200 overflow-hidden rounded-2xl border border-cream-200 bg-white"
			>
				<li v-for="line in displayLines" :key="line.pack" class="flex gap-4 p-4">
					<div class="h-20 w-20 shrink-0 overflow-hidden rounded-xl bg-cream-100">
						<PackImage :src="line.image" :alt="line.pack_name" />
					</div>

					<div class="min-w-0 flex-1">
						<div class="flex items-start justify-between gap-3">
							<h2 class="font-semibold leading-tight text-char-900">{{ line.pack_name }}</h2>
							<!-- Negative margin keeps the label visually where it was while
							     giving the control a 44px hit area. Removing a line is
							     destructive; it should not need a precise tap. -->
							<button
								type="button"
								class="-my-2 -mr-2 flex min-h-11 shrink-0 items-center px-2 text-sm text-char-400 transition-colors duration-(--duration-fast) hover:text-chili-700"
								:aria-label="`Remove ${line.pack_name}`"
								@click="remove(line.pack)"
							>
								Remove
							</button>
						</div>

						<p class="mt-0.5 text-sm text-char-400">{{ money(line.rate) }} each</p>

						<!--
							flex-wrap, not nowrap alone: at 375px the 136px stepper and the
							amount cannot share a 215px row, so the amount either broke
							mid-figure ("GHS" / "90.00") or got clipped by the card's
							overflow-hidden. Wrapping drops it to its own right-aligned line
							on the narrowest phones and keeps it inline everywhere else.
						-->
						<div class="mt-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
							<QtyStepper
								:model-value="line.qty"
								:min="1"
								:max="maxQty"
								:label="line.pack_name"
								@update:model-value="(q: number) => setQty(line.pack, q)"
							/>
							<span class="ml-auto font-semibold whitespace-nowrap text-char-900">
								{{ money(line.amount) }}
							</span>
						</div>
					</div>
				</li>
			</TransitionGroup>

			<!-- Delivery -->
			<section class="rounded-2xl border border-cream-200 bg-white p-4">
				<h2 class="font-semibold text-char-900">Delivery</h2>

				<div class="mt-3 flex gap-2">
					<button
						v-for="type in ['Delivery', 'Pickup']"
						:key="type"
						type="button"
						class="h-11 flex-1 rounded-xl text-sm font-medium transition-colors duration-(--duration-fast)"
						:class="
							fulfilmentType === type
								? 'bg-chili-600 text-white'
								: 'border border-cream-200 text-char-700 hover:border-chili-200'
						"
						@click="setFulfilment(type as 'Delivery' | 'Pickup')"
					>
						{{ type }}
					</button>
				</div>

				<div v-if="fulfilmentType === 'Delivery'" class="mt-4">
					<label for="zone" class="block text-sm font-medium text-char-700">Where are we delivering?</label>
					<select
						id="zone"
						class="mt-1.5 h-12 w-full rounded-xl border border-cream-200 bg-white px-3 text-char-900 focus:border-chili-600 focus:outline-none"
						:value="zone ?? ''"
						@change="onZoneChange"
					>
						<option value="">Select your area…</option>
						<option v-for="zone in sf.zones" :key="zone.zone" :value="zone.zone">
							{{ zone.zone_name }} — {{ money(zone.delivery_fee) }}
						</option>
					</select>

					<p v-if="selectedZone" class="mt-2 text-xs text-char-400">
						<template v-if="selectedZone.delivery_days">
							{{ selectedZone.delivery_days }}.
						</template>
						Usually {{ selectedZone.estimated_days }}
						{{ selectedZone.estimated_days === 1 ? 'day' : 'days' }}.
						<template v-if="selectedZone.free_delivery_over > 0">
							Free delivery over {{ money(selectedZone.free_delivery_over) }}.
						</template>
					</p>
				</div>
			</section>

			<!-- Messages from the server's pricing engine -->
			<div
				v-if="quote && quote.warnings.length"
				class="rounded-xl border border-cream-200 bg-cream-100 px-4 py-3 text-sm text-char-700"
				role="status"
			>
				<p v-for="w in quote.warnings" :key="w">{{ w }}</p>
			</div>

			<div
				v-if="quoteError || (quote && quote.blocking_errors.length)"
				class="rounded-xl border border-chili-200 bg-chili-50 px-4 py-3 text-sm text-chili-800"
				role="alert"
			>
				<p v-if="quoteError">{{ quoteError }}</p>
				<p v-for="e in quote?.blocking_errors ?? []" :key="e">{{ e }}</p>
			</div>

			<!-- Totals -->
			<OrderSummary :quote="quote" :awaiting-zone="!zone && fulfilmentType === 'Delivery'">
				<button
					type="button"
					class="btn-primary mt-5 h-12 w-full"
					:disabled="!canCheckout"
					@click="checkout"
				>
					<span v-if="loading">Updating…</span>
					<span v-else-if="!store.is_store_open">Store is closed</span>
					<span v-else>Continue to checkout</span>
				</button>

				<p class="mt-3 text-center text-xs text-char-400">
					Prices are confirmed by our server, never by your browser.
				</p>
			</OrderSummary>
		</div>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import QtyStepper from '../components/QtyStepper.vue';
import StateBlock from '../components/StateBlock.vue';
import PackImage from '../components/PackImage.vue';
import OrderSummary from '../components/OrderSummary.vue';
import IconCart from '../components/icons/IconCart.vue';
import cart from '../stores/cart';
import call from '../lib/call';
import { money } from '../lib/money';
import { store } from '../lib/boot';
import { state as sf, loadStorefront, packByCode } from '../lib/storefront';
import type { Quote, QuoteLine, Zone } from '../lib/types';

export default defineComponent({
	name: 'CartView',
	components: { QtyStepper, StateBlock, PackImage, OrderSummary },
	emits: ['catalog-loaded'],
	data() {
		return {
			IconCart,
			sf,
			store,
			quote: null as Quote | null,
			loading: false,
			quoteError: null as string | null,
			// Guards against an older in-flight quote overwriting a newer one when
			// the customer taps + several times quickly.
			requestId: 0
		};
	},
	computed: {
		// The cart is exposed through computeds rather than placed in data(). Vue
		// makes data reactive, and a reactive proxy auto-unwraps nested refs, so
		// `cart.isEmpty` would silently become a boolean while the template still
		// read `.value` off it -- yielding undefined, and an empty-cart state that
		// never rendered.
		isEmpty(): boolean {
			return cart.isEmpty.value;
		},
		zone(): string | null {
			return cart.state.zone;
		},
		fulfilmentType(): 'Delivery' | 'Pickup' {
			return cart.state.fulfilmentType;
		},
		lines() {
			return cart.state.lines;
		},
		maxQty(): number {
			return store.max_qty_per_line || 50;
		},
		selectedZone(): Zone | undefined {
			return sf.zones.find((z) => z.zone === cart.state.zone);
		},
		/**
		 * Prefer the server's priced lines. Before the first quote returns, fall
		 * back to local catalog data so the cart is never blank on a slow link.
		 */
		displayLines(): QuoteLine[] {
			if (this.quote?.lines.length) return this.quote.lines;
			return cart.state.lines.map((l) => {
				const pack = packByCode(l.pack);
				return {
					pack: l.pack,
					pack_name: pack?.pack_name ?? l.pack,
					image: pack?.image ?? null,
					qty: l.qty,
					rate: pack?.price ?? 0,
					amount: (pack?.price ?? 0) * l.qty,
					net_weight_g: pack?.net_weight_g ?? 0
				};
			});
		},
		canCheckout(): boolean {
			return (
				!this.loading &&
				!!store.is_store_open &&
				!!this.quote?.is_orderable &&
				(this.fulfilmentType === 'Pickup' || !!this.zone)
			);
		}
	},
	watch: {
		lines: { handler: 'refreshQuote', deep: true },
		zone: 'refreshQuote',
		fulfilmentType: 'refreshQuote'
	},
	async created() {
		await loadStorefront();
		if (sf.packs.length) this.$emit('catalog-loaded', sf.packs);
		this.refreshQuote();
	},
	methods: {
		money,
		setQty(pack: string, qty: number) {
			cart.setQty(pack, qty);
		},
		remove(pack: string) {
			cart.remove(pack);
		},
		setFulfilment(type: 'Delivery' | 'Pickup') {
			cart.setFulfilmentType(type);
		},
		onZoneChange(event: Event) {
			cart.setZone((event.target as HTMLSelectElement).value || null);
		},
		async refreshQuote() {
			if (cart.isEmpty.value) {
				this.quote = null;
				return;
			}

			const id = ++this.requestId;
			this.loading = true;
			this.quoteError = null;

			try {
				const result = await call<Quote>('prime_shito.api.catalog.quote', {
					items: JSON.stringify(cart.payload()),
					delivery_zone: cart.state.zone,
					fulfilment_type: cart.state.fulfilmentType
				});
				if (id !== this.requestId) return; // a newer request already answered
				this.quote = result;

				// The server may clamp quantities (stock, per-line caps). Reflect that
				// back into the cart so what is stored matches what was priced.
				for (const line of result.lines) {
					if (cart.qtyOf(line.pack) !== line.qty) cart.setQty(line.pack, line.qty);
				}
			} catch (err) {
				if (id !== this.requestId) return;
				this.quoteError = (err as Error).message;
			} finally {
				if (id === this.requestId) this.loading = false;
			}
		},
		checkout() {
			// Checkout arrives with the order milestone. Until then this is the
			// natural place to hand off, and the WhatsApp route already works.
			this.$router.push('/checkout');
		}
	}
});
</script>
