<template>
	<header class="sticky top-0 z-40 border-b border-cream-200 bg-cream-50/95 backdrop-blur">
		<div class="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4">
			<router-link to="/" class="flex min-w-0 items-center gap-2">
				<img
					v-if="store.logo"
					:src="store.logo"
					:alt="store.business_name"
					class="h-9 w-9 shrink-0 rounded-full object-cover"
					width="36"
					height="36"
				/>
				<span
					v-else
					class="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-chili-600 text-base font-bold text-white"
					aria-hidden="true"
				>
					PS
				</span>
				<span class="truncate text-lg font-bold tracking-tight text-char-900">
					{{ store.business_name }}
				</span>
			</router-link>

			<nav class="ml-auto hidden items-center gap-1 sm:flex">
				<router-link
					v-for="link in links"
					:key="link.to"
					:to="link.to"
					class="rounded-lg px-3 py-2 text-sm font-medium text-char-700 transition hover:bg-cream-100 hover:text-chili-700"
					active-class="text-chili-700"
				>
					{{ link.label }}
				</router-link>
			</nav>

			<router-link
				to="/cart"
				class="relative ml-auto grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-cream-200 bg-white text-char-700 transition hover:border-chili-200 hover:text-chili-700 sm:ml-0"
				:aria-label="cartLabel"
			>
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="h-5 w-5">
					<path d="M3 3h2l2.4 12.3a2 2 0 0 0 2 1.7h7.7a2 2 0 0 0 2-1.6L21 7H6" stroke-linecap="round" stroke-linejoin="round" />
					<circle cx="10" cy="20" r="1.4" fill="currentColor" stroke="none" />
					<circle cx="17" cy="20" r="1.4" fill="currentColor" stroke="none" />
				</svg>
				<span
					v-if="count > 0"
					class="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-chili-600 px-1 text-xs font-bold text-white"
				>
					{{ count > 99 ? '99+' : count }}
				</span>
			</router-link>
		</div>
	</header>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import cart from '../stores/cart';
import { store } from '../lib/boot';

export default defineComponent({
	name: 'AppHeader',
	data() {
		return {
			store,
			links: [
				{ to: '/packs', label: 'Shop' },
				{ to: '/about', label: 'About' },
				{ to: '/contact', label: 'Contact' }
			]
		};
	},
	computed: {
		count(): number {
			return cart.count.value;
		},
		cartLabel(): string {
			return this.count === 1 ? 'Cart, 1 item' : `Cart, ${this.count} items`;
		}
	}
});
</script>
