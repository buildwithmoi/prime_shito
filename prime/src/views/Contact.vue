<template>
	<div class="mx-auto max-w-2xl px-4 py-12">
		<h1 class="text-3xl font-bold tracking-tight text-char-900">Talk to us</h1>
		<p class="mt-2 text-char-500">WhatsApp is fastest. We usually reply the same day.</p>

		<!--
			One card, three rows. This was three separate bordered cards, each with
			its own pastel chip, for three items of identical importance -- three
			accent colours in one viewport with no meaning attached to the
			difference. One icon treatment says they are the same kind of thing.
		-->
		<div v-if="channels.length" class="mt-8 divide-y divide-cream-200 rounded-2xl border border-cream-200 bg-white">
			<a
				v-for="channel in channels"
				:key="channel.label"
				:href="channel.href"
				:target="channel.external ? '_blank' : undefined"
				:rel="channel.external ? 'noopener' : undefined"
				class="flex items-center gap-4 p-4 transition-colors duration-(--duration-fast) hover:bg-cream-50"
			>
				<component :is="channel.icon" class="size-(--size-icon-md) shrink-0 text-char-500" />
				<span class="min-w-0">
					<span class="block font-semibold text-char-900">{{ channel.label }}</span>
					<span class="block truncate text-sm text-char-500">{{ channel.detail }}</span>
				</span>
			</a>
		</div>

		<p v-else class="mt-8 rounded-xl bg-cream-100 px-4 py-3 text-sm text-char-700">
			Contact details have not been set up yet.
		</p>
	</div>
</template>

<script lang="ts">
import { defineComponent, type Component } from 'vue';

import IconWhatsApp from '../components/icons/IconWhatsApp.vue';
import IconPhone from '../components/icons/IconPhone.vue';
import IconMail from '../components/icons/IconMail.vue';
import { store } from '../lib/boot';

interface Channel {
	label: string;
	detail: string;
	href: string;
	icon: Component;
	external?: boolean;
}

export default defineComponent({
	name: 'ContactView',
	data() {
		return { store };
	},
	computed: {
		channels(): Channel[] {
			const rows: Channel[] = [];

			if (store.whatsapp_number) {
				rows.push({
					label: 'WhatsApp',
					detail: 'Message us to order or ask anything',
					href: `https://wa.me/${store.whatsapp_number}`,
					icon: IconWhatsApp,
					external: true
				});
			}

			if (store.support_phone) {
				rows.push({
					label: 'Call us',
					detail: store.support_phone,
					href: `tel:${store.support_phone}`,
					icon: IconPhone
				});
			}

			if (store.support_email) {
				rows.push({
					label: 'Email',
					detail: store.support_email,
					href: `mailto:${store.support_email}`,
					icon: IconMail
				});
			}

			return rows;
		}
	}
});
</script>
