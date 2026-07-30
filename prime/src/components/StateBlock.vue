<template>
	<!-- Shared loading / error / empty presentation, so every view handles all
	     three states instead of only the happy path. -->
	<div class="grid place-items-center px-4 py-16 text-center">
		<div v-if="loading" class="flex flex-col items-center gap-3">
			<span
				class="h-8 w-8 animate-spin rounded-full border-2 border-cream-200 border-t-chili-600"
				role="status"
				aria-label="Loading"
			/>
			<p class="text-sm text-char-500">{{ loadingText }}</p>
		</div>

		<div v-else-if="error" class="max-w-sm">
			<div class="text-4xl" aria-hidden="true">😕</div>
			<h2 class="mt-3 font-semibold text-char-900">{{ errorTitle }}</h2>
			<p class="mt-1 whitespace-pre-line text-sm text-char-500">{{ error }}</p>
			<button
				v-if="onRetry"
				type="button"
				class="mt-5 h-11 rounded-xl bg-chili-600 px-5 text-sm font-semibold text-white transition hover:bg-chili-700"
				@click="onRetry"
			>
				Try again
			</button>
		</div>

		<div v-else class="max-w-sm">
			<div class="text-4xl" aria-hidden="true">{{ emptyIcon }}</div>
			<h2 class="mt-3 font-semibold text-char-900">{{ emptyTitle }}</h2>
			<p v-if="emptyText" class="mt-1 text-sm text-char-500">{{ emptyText }}</p>
			<slot name="empty-action" />
		</div>
	</div>
</template>

<script lang="ts">
import { defineComponent, type PropType } from 'vue';

export default defineComponent({
	name: 'StateBlock',
	props: {
		loading: { type: Boolean, default: false },
		error: { type: String as PropType<string | null>, default: null },
		loadingText: { type: String, default: 'Loading…' },
		errorTitle: { type: String, default: 'That did not work' },
		emptyIcon: { type: String, default: '🌶️' },
		emptyTitle: { type: String, default: 'Nothing here yet' },
		emptyText: { type: String, default: '' },
		onRetry: { type: Function as PropType<() => void>, default: undefined }
	}
});
</script>
