<template>
	<img
		v-if="src"
		:src="src"
		:alt="alt"
		:loading="eager ? 'eager' : 'lazy'"
		decoding="async"
		class="h-full w-full object-cover"
	/>

	<!--
		No photo yet. Deliberately not a glyph: a cartoon chilli standing in for a
		missing photo of food reads as "this product is a cartoon". The pack's own
		name reads as "photo coming", and it stays honest at every size from the
		80px cart thumbnail to the full detail square.
	-->
	<div v-else class="flex h-full w-full items-center justify-center bg-cream-100 p-2">
		<span class="line-clamp-3 text-center text-[0.65rem] leading-tight font-medium text-char-400">
			{{ alt }}
		</span>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
	name: 'PackImage',
	props: {
		src: { type: String as () => string | null, default: null },
		alt: { type: String, required: true },
		// Only the pack detail hero should skip lazy loading; everything else is
		// below the fold on a phone.
		eager: { type: Boolean, default: false }
	}
});
</script>
