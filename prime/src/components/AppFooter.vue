<template>
	<footer class="mt-16 border-t border-cream-200 bg-white">
		<div class="mx-auto max-w-6xl px-4 py-10">
			<div class="grid gap-8 sm:grid-cols-3">
				<div>
					<h2 class="text-base font-bold text-char-900">{{ store.business_name }}</h2>
					<p v-if="store.tagline" class="mt-2 text-sm text-char-500">{{ store.tagline }}</p>
				</div>

				<div>
					<h3 class="text-sm font-semibold text-char-900">Shop</h3>
					<!-- Track order was previously reachable from nowhere: a real route
					     with its own SMS integration that a customer could only get to
					     by typing the URL. Contact was in the header but not here; the
					     two menus should not disagree about what the site contains. -->
					<ul class="mt-3 space-y-2 text-sm">
						<li v-for="link in shopLinks" :key="link.to">
							<router-link
								:to="link.to"
								class="text-char-500 transition-colors duration-(--duration-fast) hover:text-chili-700"
							>
								{{ link.label }}
							</router-link>
						</li>
					</ul>
				</div>

				<div>
					<h3 class="text-sm font-semibold text-char-900">Talk to us</h3>
					<ul class="mt-3 space-y-2 text-sm">
						<li v-if="store.support_phone">
							<a :href="`tel:${store.support_phone}`" class="text-char-500 transition-colors duration-(--duration-fast) hover:text-chili-700">
								{{ store.support_phone }}
							</a>
						</li>
						<li v-if="store.whatsapp_number">
							<a :href="whatsappUrl" class="text-char-500 transition-colors duration-(--duration-fast) hover:text-chili-700" rel="noopener">
								WhatsApp
							</a>
						</li>
						<li v-if="store.support_email">
							<a :href="`mailto:${store.support_email}`" class="text-char-500 transition-colors duration-(--duration-fast) hover:text-chili-700">
								{{ store.support_email }}
							</a>
						</li>
					</ul>
				</div>
			</div>

			<p class="mt-8 border-t border-cream-200 pt-6 text-xs text-char-400">
				&copy; {{ year }} {{ store.business_name }}. Made in Ghana.
			</p>
		</div>
	</footer>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { store } from '../lib/boot';

export default defineComponent({
	name: 'AppFooter',
	data() {
		return {
			store,
			year: new Date().getFullYear(),
			shopLinks: [
				{ to: '/packs', label: 'All packs' },
				{ to: '/cart', label: 'Your cart' },
				{ to: '/track', label: 'Track order' },
				{ to: '/about', label: 'About us' },
				{ to: '/contact', label: 'Contact' }
			]
		};
	},
	computed: {
		whatsappUrl(): string {
			return `https://wa.me/${store.whatsapp_number}`;
		}
	}
});
</script>
