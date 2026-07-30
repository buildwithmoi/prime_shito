<template>
	<!--
		A floating WhatsApp button with the cart pre-filled.

		This is deliberately prominent. In Ghana a large share of first-time
		buyers would rather send a message than complete a checkout form, and
		this path costs nothing to run.
	-->
	<a
		v-if="store.whatsapp_number"
		:href="url"
		target="_blank"
		rel="noopener"
		class="fixed bottom-5 right-4 z-30 grid h-14 w-14 place-items-center rounded-full bg-[#25D366] shadow-lg shadow-black/20 transition hover:scale-105 print:hidden"
		aria-label="Order on WhatsApp"
	>
		<svg viewBox="0 0 24 24" fill="currentColor" class="h-7 w-7 text-white" aria-hidden="true">
			<path
				d="M17.5 14.4c-.3-.2-1.7-.9-2-1-.3-.1-.5-.1-.6.1-.2.3-.7 1-.9 1.2-.2.2-.3.2-.6.1-.3-.2-1.2-.5-2.3-1.4-.9-.8-1.4-1.7-1.6-2-.2-.3 0-.5.1-.6l.5-.5c.1-.2.2-.3.3-.5 0-.2 0-.4 0-.5 0-.2-.6-1.5-.8-2-.2-.5-.4-.5-.6-.5h-.5c-.2 0-.5.1-.7.3-.3.3-1 1-1 2.4s1 2.8 1.2 3c.1.2 2 3.1 4.9 4.3.7.3 1.2.5 1.6.6.7.2 1.3.2 1.8.1.6-.1 1.7-.7 1.9-1.4.2-.7.2-1.3.2-1.4-.1-.1-.3-.2-.6-.3z"
			/>
			<path
				d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2c-1.5 0-3-.4-4.3-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2z"
			/>
		</svg>
	</a>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import cart from '../stores/cart';
import { store } from '../lib/boot';
import type { Pack } from '../lib/types';

export default defineComponent({
	name: 'WhatsAppFab',
	props: {
		// Passed in where the catalog is already loaded, so the message can name
		// the packs rather than their codes.
		packs: { type: Array as () => Pack[], default: () => [] }
	},
	data() {
		return { store };
	},
	computed: {
		url(): string {
			const lines = cart.state.lines;
			let text = `Hello ${store.business_name}, I would like to order:`;

			if (lines.length) {
				const byCode = new Map(this.packs.map((p) => [p.pack, p.pack_name]));
				for (const line of lines) {
					text += `\n- ${line.qty} x ${byCode.get(line.pack) ?? line.pack}`;
				}
			} else {
				text = `Hello ${store.business_name}, I would like to ask about your shito packs.`;
			}

			return `https://wa.me/${store.whatsapp_number}?text=${encodeURIComponent(text)}`;
		}
	}
});
</script>
