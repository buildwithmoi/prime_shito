<template>
	<div class="grid place-items-center px-4 py-24 text-center">
		<div class="text-6xl" aria-hidden="true">🌶️</div>
		<h1 class="mt-4 text-2xl font-bold text-char-900">This page does not exist</h1>
		<p class="mt-2 text-char-500">The link may be old, or we may have moved things around.</p>
		<router-link
			to="/"
			class="mt-6 inline-flex h-12 items-center rounded-xl bg-chili-600 px-6 font-semibold text-white transition hover:bg-chili-700"
		>
			Go to the shop
		</router-link>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({ name: 'NotFoundView' });
</script>
