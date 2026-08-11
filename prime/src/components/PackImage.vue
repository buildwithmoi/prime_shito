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
	<div v-else class="flex h-full w-full items-center justify-center bg-cream-100 p-1.5" :title="alt">
		<!--
			The label is dropped below roughly 64px. In a 48px thumbnail even 0.65rem
			text is wider than the box and gets clipped mid-word, and the pack name is
			already printed next to the thumbnail in those rows. break-words keeps a
			long single word from clipping at the sizes where the label does show.
		-->
		<span
			v-if="!compact"
			class="line-clamp-3 text-center text-[0.65rem] leading-tight font-medium break-words text-char-400"
		>
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
		eager: { type: Boolean, default: false },
		// For thumbnails too small to carry a readable label.
		compact: { type: Boolean, default: false }
	}
});
</script>
