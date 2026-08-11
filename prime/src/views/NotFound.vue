<template>
	<!-- The heading says the page does not exist; a chilli above it added
	     nothing and was drawn differently on every phone vendor. -->
	<div class="grid place-items-center px-4 py-24 text-center">
		<h1 class="text-2xl font-bold text-char-900">This page does not exist</h1>
		<p class="mt-2 text-char-500">The link may be old, or we may have moved things around.</p>
		<router-link to="/" class="btn-primary mt-6">Go to the shop</router-link>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({ name: 'NotFoundView' });
</script>
