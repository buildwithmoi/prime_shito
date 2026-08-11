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
					class="rounded-lg px-3 py-2 text-sm font-medium text-char-700 transition-colors duration-(--duration-fast) hover:bg-cream-100 hover:text-chili-700"
					active-class="text-chili-700"
				>
					{{ link.label }}
				</router-link>
			</nav>

			<router-link
				to="/cart"
				class="relative ml-auto grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-cream-200 bg-white text-char-700 transition-colors duration-(--duration-fast) hover:border-chili-200 hover:text-chili-700 sm:ml-0"
				:aria-label="cartLabel"
			>
				<IconCart class="size-(--size-icon-md)" />
				<span
					v-if="count > 0"
					class="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-chili-600 px-1 text-xs font-bold text-white"
				>
					{{ count > 99 ? '99+' : count }}
				</span>
			</router-link>
		</div>

		<!--
			Mobile navigation. Until now the phone header was a logo and a cart
			icon, which left Shop, About and Contact unreachable from every page on
			the device most customers actually use.

			A scrollable inline row rather than a drawer: four links do not justify
			an open/close state, and a row that is always visible cannot be left
			shut.
		-->
		<nav
			class="scrollbar-none -mt-px flex gap-1 overflow-x-auto border-t border-cream-200 px-4 py-2 sm:hidden"
			aria-label="Main"
		>
			<router-link
				v-for="link in mobileLinks"
				:key="link.to"
				:to="link.to"
				class="shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium text-char-700 transition-colors duration-(--duration-fast)"
				active-class="bg-chili-50 text-chili-700"
			>
				{{ link.label }}
			</router-link>
		</nav>
	</header>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import IconCart from './icons/IconCart.vue';
import cart from '../stores/cart';
import { store } from '../lib/boot';

const LINKS = [
	{ to: '/packs', label: 'Shop' },
	{ to: '/about', label: 'About' },
	{ to: '/contact', label: 'Contact' }
];

export default defineComponent({
	name: 'AppHeader',
	components: { IconCart },
	data() {
		return {
			store,
			links: LINKS,
			// Track is reachable from the front page on desktop, but on a phone
			// this row is the only way to it.
			mobileLinks: [...LINKS, { to: '/track', label: 'Track order' }]
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
