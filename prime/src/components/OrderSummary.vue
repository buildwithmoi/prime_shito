<template>
	<!--
		Shared totals panel. Cart and Checkout each carried their own copy of this
		markup and had already started to drift, which on a money surface means
		two places to get a rounding or a label wrong.
	-->
	<section class="rounded-2xl border border-cream-200 bg-white p-4">
		<dl class="space-y-2 text-sm">
			<div class="flex justify-between">
				<dt class="text-char-500">Subtotal</dt>
				<dd class="font-medium text-char-900">{{ money(quote?.items_total ?? 0) }}</dd>
			</div>

			<div class="flex justify-between">
				<dt class="text-char-500">Delivery</dt>
				<dd class="font-medium text-char-900">
					<span v-if="quote?.free_delivery_applied" class="text-chili-700">Free</span>
					<span v-else-if="awaitingZone" class="text-char-400">Choose an area</span>
					<span v-else>{{ money(quote?.delivery_fee ?? 0) }}</span>
				</dd>
			</div>

			<div v-if="(quote?.discount_amount ?? 0) > 0" class="flex justify-between">
				<dt class="text-char-500">Discount</dt>
				<dd class="font-medium text-chili-700">-{{ money(quote?.discount_amount ?? 0) }}</dd>
			</div>

			<div class="flex justify-between border-t border-cream-200 pt-3 text-base">
				<dt class="font-semibold text-char-900">Total</dt>
				<dd class="font-bold text-char-900">{{ money(quote?.grand_total ?? 0) }}</dd>
			</div>
		</dl>

		<slot />
	</section>
</template>

<script lang="ts">
import { defineComponent, type PropType } from 'vue';

import { money } from '../lib/money';
import type { Quote } from '../lib/types';

export default defineComponent({
	name: 'OrderSummary',
	props: {
		quote: { type: Object as PropType<Quote | null>, default: null },
		// Delivery is genuinely unknown until an area is picked, which is not the
		// same as it being free.
		awaitingZone: { type: Boolean, default: false }
	},
	methods: { money }
});
</script>
