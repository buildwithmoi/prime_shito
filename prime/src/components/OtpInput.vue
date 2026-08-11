<template>
	<div>
		<label :for="id" class="block text-sm font-medium text-char-700">{{ label }}</label>
		<input
			:id="id"
			ref="input"
			type="text"
			inputmode="numeric"
			:maxlength="length"
			autocomplete="one-time-code"
			class="mt-1.5 h-14 w-full rounded-xl border bg-white text-center text-2xl font-bold tracking-[0.5em] text-char-900 transition-colors duration-(--duration-fast) focus:outline-none"
			:class="error ? 'border-chili-600' : 'border-cream-200 focus:border-chili-600'"
			:value="modelValue"
			:disabled="disabled"
			@input="onInput"
		/>
		<p v-if="error" class="mt-1 text-xs text-chili-700">{{ error }}</p>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

/**
 * One-time code entry.
 *
 * A single wide input rather than the usual row of separate boxes:
 * `autocomplete="one-time-code"` lets Android and iOS fill the code straight
 * from the SMS, and that autofill is unreliable across split inputs. On a
 * cheap Android phone, one tap beats a prettier six-box layout.
 */
export default defineComponent({
	name: 'OtpInput',
	props: {
		modelValue: { type: String, default: '' },
		label: { type: String, default: 'Enter the 6-digit code' },
		length: { type: Number, default: 6 },
		error: { type: String, default: '' },
		disabled: { type: Boolean, default: false }
	},
	emits: ['update:modelValue', 'complete'],
	data() {
		return { id: `otp-${Math.random().toString(36).slice(2, 8)}` };
	},
	methods: {
		onInput(event: Event) {
			const el = event.target as HTMLInputElement;
			const digits = el.value.replace(/\D/g, '').slice(0, this.length);
			el.value = digits;
			this.$emit('update:modelValue', digits);
			if (digits.length === this.length) this.$emit('complete', digits);
		},
		focus() {
			(this.$refs.input as HTMLInputElement | undefined)?.focus();
		}
	}
});
</script>
