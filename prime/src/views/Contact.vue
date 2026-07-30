<template>
	<div class="mx-auto max-w-2xl px-4 py-12">
		<h1 class="text-3xl font-bold tracking-tight text-char-900">Talk to us</h1>
		<p class="mt-2 text-char-500">
			WhatsApp is fastest. We usually reply the same day.
		</p>

		<div class="mt-8 space-y-3">
			<a
				v-if="store.whatsapp_number"
				:href="`https://wa.me/${store.whatsapp_number}`"
				target="_blank"
				rel="noopener"
				class="flex items-center gap-4 rounded-2xl border border-cream-200 bg-white p-4 transition hover:border-chili-200"
			>
				<span class="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-[#25D366]/10 text-xl">💬</span>
				<span>
					<span class="block font-semibold text-char-900">WhatsApp</span>
					<span class="block text-sm text-char-500">Message us to order or ask anything</span>
				</span>
			</a>

			<a
				v-if="store.support_phone"
				:href="`tel:${store.support_phone}`"
				class="flex items-center gap-4 rounded-2xl border border-cream-200 bg-white p-4 transition hover:border-chili-200"
			>
				<span class="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-chili-50 text-xl">📞</span>
				<span>
					<span class="block font-semibold text-char-900">Call us</span>
					<span class="block text-sm text-char-500">{{ store.support_phone }}</span>
				</span>
			</a>

			<a
				v-if="store.support_email"
				:href="`mailto:${store.support_email}`"
				class="flex items-center gap-4 rounded-2xl border border-cream-200 bg-white p-4 transition hover:border-chili-200"
			>
				<span class="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-cream-100 text-xl">✉️</span>
				<span>
					<span class="block font-semibold text-char-900">Email</span>
					<span class="block text-sm text-char-500">{{ store.support_email }}</span>
				</span>
			</a>
		</div>

		<p v-if="!hasAnyContact" class="mt-8 rounded-xl bg-cream-100 px-4 py-3 text-sm text-char-700">
			Contact details have not been set up yet.
		</p>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { store } from '../lib/boot';

export default defineComponent({
	name: 'ContactView',
	data() {
		return { store };
	},
	computed: {
		hasAnyContact(): boolean {
			return Boolean(store.whatsapp_number || store.support_phone || store.support_email);
		}
	}
});
</script>
