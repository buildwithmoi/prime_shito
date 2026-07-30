<template>
	<div>
		<label :for="id" class="block text-sm font-medium text-char-700">{{ label }}</label>
		<div
			class="mt-1.5 flex h-12 items-center overflow-hidden rounded-xl border bg-white transition"
			:class="error ? 'border-chili-600' : 'border-cream-200 focus-within:border-chili-600'"
		>
			<span class="grid h-full place-items-center border-r border-cream-200 bg-cream-50 px-3 text-sm font-medium text-char-500">
				+233
			</span>
			<input
				:id="id"
				ref="input"
				type="tel"
				inputmode="numeric"
				autocomplete="tel-national"
				class="h-full min-w-0 flex-1 px-3 text-char-900 focus:outline-none"
				placeholder="24 123 4567"
				:value="display"
				:disabled="disabled"
				@input="onInput"
			/>
		</div>
		<p v-if="error" class="mt-1 text-xs text-chili-700">{{ error }}</p>
		<p v-else-if="hint" class="mt-1 text-xs text-char-400">{{ hint }}</p>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

/**
 * Ghanaian mobile number entry.
 *
 * The +233 prefix is fixed rather than typed. Customers naturally write
 * 024..., and letting them also type +233 or 00233 produces three spellings of
 * the same number. The server normalises regardless, but showing one shape
 * avoids the "is my number wrong?" moment at the most abandonment-prone step.
 */
export default defineComponent({
	name: 'PhoneInput',
	props: {
		modelValue: { type: String, default: '' },
		label: { type: String, default: 'Phone number' },
		hint: { type: String, default: 'We will text your order updates here' },
		error: { type: String, default: '' },
		disabled: { type: Boolean, default: false }
	},
	emits: ['update:modelValue'],
	data() {
		return { id: `phone-${Math.random().toString(36).slice(2, 8)}` };
	},
	computed: {
		display(): string {
			// Show the national form: strip a leading 233 or 0 the customer pasted.
			let digits = (this.modelValue || '').replace(/\D/g, '');
			if (digits.startsWith('233')) digits = digits.slice(3);
			if (digits.startsWith('0')) digits = digits.slice(1);
			return digits.slice(0, 9);
		}
	},
	methods: {
		onInput(event: Event) {
			const el = event.target as HTMLInputElement;
			let digits = el.value.replace(/\D/g, '');
			if (digits.startsWith('233')) digits = digits.slice(3);
			if (digits.startsWith('0')) digits = digits.slice(1);
			digits = digits.slice(0, 9);
			el.value = digits;
			// Emit the full national form; the server normalises to E.164.
			this.$emit('update:modelValue', digits ? `0${digits}` : '');
		},
		focus() {
			(this.$refs.input as HTMLInputElement | undefined)?.focus();
		}
	}
});
</script>
