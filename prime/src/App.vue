<template>
	<div class="flex min-h-screen flex-col">
		<AppHeader />

		<div
			v-if="!store.is_store_open"
			class="bg-char-900 px-4 py-2.5 text-center text-sm text-cream-100"
			role="status"
		>
			{{ store.store_closed_message || 'We are not taking orders right now.' }}
		</div>

		<main class="flex-1">
			<!-- `mode="out-in"` is not optional: without it the outgoing and
			     incoming pages are mounted together and the footer jumps. -->
			<router-view v-slot="{ Component }">
				<Transition name="page" mode="out-in">
					<component :is="Component" @catalog-loaded="onCatalogLoaded" />
				</Transition>
			</router-view>
		</main>

		<AppFooter />
		<!--
			Hidden during checkout: the button floats bottom-right, which is exactly
			where the submit button sits, so it covered "Continue to payment". A
			customer mid-checkout is already converting; offering them a different
			channel there is a distraction on top of a collision.

			Raised on PackDetail, the only other view with a sticky action bar.
		-->
		<WhatsAppFab
			v-if="$route.name !== 'Checkout'"
			:packs="packs"
			:raised="$route.name === 'PackDetail'"
		/>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import AppHeader from './components/AppHeader.vue';
import AppFooter from './components/AppFooter.vue';
import WhatsAppFab from './components/WhatsAppFab.vue';
import { store } from './lib/boot';
import type { Pack } from './lib/types';

export default defineComponent({
	name: 'App',
	components: { AppHeader, AppFooter, WhatsAppFab },
	data() {
		return { store, packs: [] as Pack[] };
	},
	methods: {
		// Views emit this once they have the catalog, so the WhatsApp message can
		// name packs instead of codes without a second network request.
		onCatalogLoaded(packs: Pack[]) {
			if (Array.isArray(packs) && packs.length) this.packs = packs;
		}
	}
});
</script>
