<template>
	<div class="inline-flex items-center rounded-xl border border-cream-200 bg-white">
		<button
			type="button"
			class="grid h-11 w-11 place-items-center rounded-l-xl text-lg font-semibold text-char-700 transition-colors duration-(--duration-fast) hover:bg-cream-100 disabled:cursor-not-allowed disabled:text-char-400"
			:disabled="modelValue <= min"
			:aria-label="`Reduce quantity of ${label}`"
			@click="step(-1)"
		>
			&minus;
		</button>

		<input
			type="number"
			class="h-11 w-12 border-x border-cream-200 text-center text-sm font-semibold text-char-900 [appearance:textfield] focus:outline-none [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
			:value="modelValue"
			:min="min"
			:max="max"
			inputmode="numeric"
			:aria-label="`Quantity of ${label}`"
			@change="onInput"
		/>

		<button
			type="button"
			class="grid h-11 w-11 place-items-center rounded-r-xl text-lg font-semibold text-char-700 transition-colors duration-(--duration-fast) hover:bg-cream-100 disabled:cursor-not-allowed disabled:text-char-400"
			:disabled="modelValue >= max"
			:aria-label="`Increase quantity of ${label}`"
			@click="step(1)"
		>
			+
		</button>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
	name: 'QtyStepper',
	props: {
		modelValue: { type: Number, required: true },
		min: { type: Number, default: 1 },
		max: { type: Number, default: 50 },
		label: { type: String, default: 'item' }
	},
	emits: ['update:modelValue'],
	methods: {
		clamp(n: number): number {
			if (!Number.isFinite(n)) return this.min;
			return Math.min(Math.max(Math.floor(n), this.min), this.max);
		},
		step(delta: number) {
			this.$emit('update:modelValue', this.clamp(this.modelValue + delta));
		},
		onInput(event: Event) {
			const raw = Number((event.target as HTMLInputElement).value);
			const next = this.clamp(raw);
			// Reflect the clamped value back, so typing 999 visibly snaps to the max.
			(event.target as HTMLInputElement).value = String(next);
			this.$emit('update:modelValue', next);
		}
	}
});
</script>
