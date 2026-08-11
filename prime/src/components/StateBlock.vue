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
			<IconAlert class="mx-auto size-(--size-icon-lg) text-char-400" />
			<h2 class="mt-3 font-semibold text-char-900">{{ errorTitle }}</h2>
			<p class="mt-1 whitespace-pre-line text-sm text-char-500">{{ error }}</p>
			<button v-if="onRetry" type="button" class="btn-primary mt-5 h-11 px-5 text-sm" @click="onRetry">
				Try again
			</button>
		</div>

		<div v-else class="max-w-sm">
			<component
				:is="emptyIcon"
				v-if="emptyIcon"
				class="mx-auto size-(--size-icon-lg) text-char-400"
			/>
			<h2 class="mt-3 font-semibold text-char-900">{{ emptyTitle }}</h2>
			<p v-if="emptyText" class="mt-1 text-sm text-char-500">{{ emptyText }}</p>
			<slot name="empty-action" />
		</div>
	</div>
</template>

<script lang="ts">
import { defineComponent, type Component, type PropType } from 'vue';

import IconAlert from './icons/IconAlert.vue';

export default defineComponent({
	name: 'StateBlock',
	components: { IconAlert },
	props: {
		loading: { type: Boolean, default: false },
		error: { type: String as PropType<string | null>, default: null },
		loadingText: { type: String, default: 'Loading…' },
		errorTitle: { type: String, default: 'That did not work' },
		// A component, not a String. The old String type is precisely what
		// invited a text character in; now an emoji cannot be passed without a
		// type error, and `yarn type-check` keeps it that way.
		emptyIcon: { type: [Object, Function] as PropType<Component>, default: undefined },
		emptyTitle: { type: String, default: 'Nothing here yet' },
		emptyText: { type: String, default: '' },
		onRetry: { type: Function as PropType<() => void>, default: undefined }
	}
});
</script>
