<template>
	<article
		class="group flex flex-col overflow-hidden rounded-2xl border border-cream-200 bg-white transition-[border-color,box-shadow] duration-(--duration-fast) hover:border-chili-200 hover:shadow-lg hover:shadow-chili-600/5"
	>
		<router-link :to="`/packs/${pack.route}`" class="relative block aspect-square overflow-hidden bg-cream-100">
			<!-- The one scale transform in the app. Keeping it singular means the
			     storefront has a signature move rather than five competing ones. -->
			<div class="h-full w-full transition-transform duration-(--duration-slow) ease-(--ease-out-soft) group-hover:scale-105">
				<PackImage :src="pack.image" :alt="pack.pack_name" />
			</div>

			<span
				v-if="pack.sold_out"
				class="absolute left-3 top-3 rounded-full bg-char-900/85 px-3 py-1 text-xs font-semibold text-white"
			>
				Sold out
			</span>
			<span
				v-else-if="hasDiscount"
				class="absolute left-3 top-3 rounded-full bg-chili-600 px-3 py-1 text-xs font-semibold text-white"
			>
				Save {{ discountPercent }}%
			</span>
		</router-link>

		<div class="flex flex-1 flex-col p-4">
			<div class="flex items-start justify-between gap-2">
				<h3 class="font-semibold leading-tight text-char-900">
					<router-link :to="`/packs/${pack.route}`" class="hover:text-chili-700">
						{{ pack.pack_name }}
					</router-link>
				</h3>
				<span
					v-if="pack.heat_level"
					class="shrink-0 rounded-full bg-chili-50 px-2 py-0.5 text-xs font-medium text-chili-700"
				>
					{{ pack.heat_level }}
				</span>
			</div>

			<p v-if="pack.description" class="mt-1.5 line-clamp-2 text-sm text-char-500">
				{{ pack.description }}
			</p>

			<div class="mt-4 flex items-end justify-between gap-3">
				<div>
					<div class="text-lg font-bold text-char-900">{{ money(pack.price) }}</div>
					<div v-if="hasDiscount" class="text-sm text-char-400 line-through">
						{{ money(pack.compare_at_price) }}
					</div>
					<div v-if="pack.net_weight_g" class="text-xs text-char-400">{{ pack.net_weight_g }}g</div>
				</div>

				<button
					type="button"
					class="btn-primary h-11 px-4 text-sm"
					:disabled="pack.sold_out"
					@click="add"
				>
					{{ pack.sold_out ? 'Sold out' : added ? 'Added' : 'Add' }}
				</button>
			</div>
		</div>
	</article>
</template>

<script lang="ts">
import { defineComponent, type PropType } from 'vue';
import PackImage from './PackImage.vue';
import cart from '../stores/cart';
import { money } from '../lib/money';
import type { Pack } from '../lib/types';

export default defineComponent({
	name: 'PackCard',
	components: { PackImage },
	props: {
		pack: { type: Object as PropType<Pack>, required: true }
	},
	emits: ['added'],
	data() {
		return { added: false, timer: 0 as unknown as ReturnType<typeof setTimeout> };
	},
	computed: {
		hasDiscount(): boolean {
			return Number(this.pack.compare_at_price) > Number(this.pack.price);
		},
		discountPercent(): number {
			const was = Number(this.pack.compare_at_price);
			const now = Number(this.pack.price);
			return Math.round(((was - now) / was) * 100);
		}
	},
	methods: {
		money,
		add() {
			if (this.pack.sold_out) return;
			cart.add(this.pack.pack, Math.max(this.pack.min_order_qty || 1, 1));
			this.added = true;
			this.$emit('added', this.pack);
			clearTimeout(this.timer);
			this.timer = setTimeout(() => (this.added = false), 1500);
		}
	},
	beforeUnmount() {
		clearTimeout(this.timer);
	}
});
</script>
