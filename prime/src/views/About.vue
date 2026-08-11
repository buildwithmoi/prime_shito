<template>
	<div class="mx-auto max-w-3xl px-4 py-12">
		<h1 class="text-3xl font-bold tracking-tight text-char-900">About {{ store.business_name }}</h1>

		<p v-if="store.tagline" class="mt-3 text-lg text-char-500">{{ store.tagline }}</p>

		<p v-if="store.about_text" class="mt-6 whitespace-pre-line text-char-500">
			{{ store.about_text }}
		</p>

		<div class="mt-10 rounded-2xl border border-cream-200 bg-white p-6">
			<h2 class="font-semibold text-char-900">Pre-order, made fresh</h2>
			<p class="mt-2 text-sm text-char-500">
				We do not keep shito sitting on a shelf. You order, we make it in the next batch, and it
				reaches you fresh. That is why we ask for a day or two.
			</p>
		</div>

		<!-- Kept rather than deleted as a Home duplicate: this is the only exit
		     from a content page, and the copy is its own. -->
		<router-link to="/packs" class="btn-primary mt-8">See our packs</router-link>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { store } from '../lib/boot';

export default defineComponent({
	name: 'AboutView',
	data() {
		return { store };
	}
});
</script>
