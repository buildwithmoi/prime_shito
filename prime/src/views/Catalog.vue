<template>
	<div class="mx-auto max-w-6xl px-4 py-8">
		<h1 class="text-3xl font-bold tracking-tight text-char-900">Our packs</h1>
		<p class="mt-1 text-sm text-char-500">
			{{ sf.packs.length }} {{ sf.packs.length === 1 ? 'pack' : 'packs' }} available for pre-order.
		</p>

		<!-- Filters only appear once there are enough packs to be worth filtering. -->
		<div v-if="flavours.length > 1" class="mt-6 flex flex-wrap gap-2">
			<button
				type="button"
				class="h-10 rounded-full px-4 text-sm font-medium transition-colors duration-(--duration-fast)"
				:class="
					activeFlavour === null
						? 'bg-chili-600 text-white'
						: 'border border-cream-200 bg-white text-char-700 hover:border-chili-200'
				"
				@click="activeFlavour = null"
			>
				All
			</button>
			<button
				v-for="flavour in flavours"
				:key="flavour"
				type="button"
				class="h-10 rounded-full px-4 text-sm font-medium transition-colors duration-(--duration-fast)"
				:class="
					activeFlavour === flavour
						? 'bg-chili-600 text-white'
						: 'border border-cream-200 bg-white text-char-700 hover:border-chili-200'
				"
				@click="activeFlavour = flavour"
			>
				{{ flavour }}
			</button>
		</div>

		<StateBlock
			v-if="sf.loading || sf.error || !visible.length"
			:loading="sf.loading"
			:error="sf.error"
			loading-text="Loading our packs…"
			empty-title="Nothing matches that"
			empty-text="Try another flavour."
			:on-retry="retry"
		/>

		<div v-else class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
			<PackCard v-for="pack in visible" :key="pack.pack" :pack="pack" />
		</div>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import PackCard from '../components/PackCard.vue';
import StateBlock from '../components/StateBlock.vue';
import { state as sf, loadStorefront } from '../lib/storefront';
import type { Pack } from '../lib/types';

export default defineComponent({
	name: 'CatalogView',
	components: { PackCard, StateBlock },
	emits: ['catalog-loaded'],
	data() {
		return { sf, activeFlavour: null as string | null };
	},
	computed: {
		flavours(): string[] {
			return [...new Set(sf.packs.map((p) => p.flavour).filter((f): f is string => Boolean(f)))];
		},
		visible(): Pack[] {
			if (!this.activeFlavour) return sf.packs;
			return sf.packs.filter((p) => p.flavour === this.activeFlavour);
		}
	},
	async created() {
		await loadStorefront();
		if (sf.packs.length) this.$emit('catalog-loaded', sf.packs);
	},
	methods: {
		retry() {
			loadStorefront(true);
		}
	}
});
</script>
