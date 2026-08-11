<template>
	<div>
		<!-- Hero -->
		<section class="bg-gradient-to-b from-cream-100 to-cream-50">
			<div class="mx-auto grid max-w-6xl gap-8 px-4 py-12 sm:py-16 md:grid-cols-2 md:items-center">
				<div>
					<span
						class="inline-flex items-center gap-1.5 rounded-full bg-chili-50 px-3 py-1 text-xs font-semibold text-chili-700"
					>
						Made fresh in Ghana
					</span>

					<h1 class="mt-4 text-4xl font-extrabold leading-tight tracking-tight text-char-900 sm:text-5xl">
						{{ store.business_name }}
					</h1>

					<p v-if="store.tagline" class="mt-3 text-lg text-char-500">
						{{ store.tagline }}
					</p>

					<div class="mt-7 flex flex-wrap gap-3">
						<router-link
							to="/packs"
							class="btn-primary"
						>
							Order now
						</router-link>
						<a
							v-if="store.whatsapp_number"
							:href="`https://wa.me/${store.whatsapp_number}`"
							target="_blank"
							rel="noopener"
							class="btn-secondary"
						>
							Order on WhatsApp
						</a>
					</div>
				</div>

				<div class="order-first md:order-last">
					<img
						:src="heroImage"
						alt="A jar of Prime Shito"
						class="aspect-[4/3] w-full rounded-3xl object-cover shadow-xl shadow-chili-600/10"
						width="640"
						height="480"
						fetchpriority="high"
					/>
				</div>
			</div>
		</section>

		<!-- Featured packs -->
		<section class="mx-auto max-w-6xl px-4 py-12">
			<div class="flex items-end justify-between gap-4">
				<div>
					<h2 class="text-2xl font-bold tracking-tight text-char-900">Our packs</h2>
					<p class="mt-1 text-sm text-char-500">Pre-order and we make yours in the next batch.</p>
				</div>
				<router-link to="/packs" class="shrink-0 text-sm font-semibold text-chili-700 transition-colors duration-(--duration-fast) hover:underline">
					See all
				</router-link>
			</div>

			<StateBlock
				v-if="sf.loading || sf.error || !featured.length"
				:loading="sf.loading"
				:error="sf.error"
				loading-text="Loading our packs…"
				empty-title="No packs yet"
				empty-text="The shop is being stocked. Please check back soon."
				:on-retry="retry"
			/>

			<div v-else class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				<PackCard v-for="pack in featured" :key="pack.pack" :pack="pack" />
			</div>
		</section>

		<!-- Order tracking: a headline feature, so it sits on the front page
		     rather than behind a nav link. -->
		<section class="border-y border-cream-200 bg-char-900">
			<div class="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 sm:flex-row sm:items-center sm:justify-between">
				<div>
					<h2 class="text-xl font-bold text-white">Already ordered?</h2>
					<p class="mt-1 text-sm text-cream-200">
						Track it with the code we texted you.
					</p>
				</div>
				<form class="flex gap-2" @submit.prevent="goToTrack">
					<input
						v-model="trackCode"
						type="text"
						autocapitalize="characters"
						class="h-12 w-full min-w-0 rounded-xl border-0 px-3 font-mono uppercase tracking-wider text-char-900 focus:outline-none focus:ring-2 focus:ring-chili-500 sm:w-52"
						placeholder="PS-XXXX-XXXX"
						aria-label="Tracking code"
					/>
					<button
						type="submit"
						class="btn-primary h-12 shrink-0 px-5"
					>
						Track
					</button>
				</form>
			</div>
		</section>

		<!-- How it works -->
		<section class="border-y border-cream-200 bg-white">
			<div class="mx-auto max-w-6xl px-4 py-12">
				<h2 class="text-2xl font-bold tracking-tight text-char-900">How it works</h2>
				<ol class="mt-6 grid gap-6 sm:grid-cols-3">
					<li v-for="(step, i) in steps" :key="step.title" class="flex gap-4">
						<span
							class="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-chili-600 font-bold text-white"
						>
							{{ i + 1 }}
						</span>
						<div>
							<h3 class="font-semibold text-char-900">{{ step.title }}</h3>
							<p class="mt-1 text-sm text-char-500">{{ step.body }}</p>
						</div>
					</li>
				</ol>
			</div>
		</section>

		<!-- About -->
		<section v-if="store.about_text" class="mx-auto max-w-3xl px-4 py-12 text-center">
			<h2 class="text-2xl font-bold tracking-tight text-char-900">Made the slow way</h2>
			<p class="mt-4 text-char-500">{{ store.about_text }}</p>
		</section>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import PackCard from '../components/PackCard.vue';
import StateBlock from '../components/StateBlock.vue';
import { store } from '../lib/boot';
import { state as sf, loadStorefront } from '../lib/storefront';
import heroFallback from '../assets/hero.png';
import type { Pack } from '../lib/types';

export default defineComponent({
	name: 'HomeView',
	components: { PackCard, StateBlock },
	emits: ['catalog-loaded'],
	data() {
		return {
			store,
			sf,
			trackCode: '',
			steps: [
				{
					title: 'Choose your packs',
					body: 'Classic, beef or dried fish. Pick the heat level you can handle.'
				},
				{
					title: 'Tell us where',
					body: 'We deliver across Ghana. Delivery is calculated by area at checkout.'
				},
				{
					title: 'Pay your way',
					body: 'Mobile Money, card, or cash when it reaches you.'
				}
			]
		};
	},
	computed: {
		heroImage(): string {
			return store.hero_image || heroFallback;
		},
		featured(): Pack[] {
			const starred = sf.packs.filter((p) => p.is_featured);
			return (starred.length ? starred : sf.packs).slice(0, 3);
		}
	},
	async created() {
		await loadStorefront();
		if (sf.packs.length) this.$emit('catalog-loaded', sf.packs);
	},
	methods: {
		retry() {
			loadStorefront(true);
		},
		goToTrack() {
			const code = this.trackCode.trim().toUpperCase();
			this.$router.push(code ? `/track/${code}` : '/track');
		}
	}
});
</script>
