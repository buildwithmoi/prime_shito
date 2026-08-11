<template>
	<div class="mx-auto max-w-2xl px-4 py-8">
		<h1 class="text-3xl font-bold tracking-tight text-char-900">Track your order</h1>
		<p class="mt-2 text-char-500">
			Enter the code from your SMS and the last 4 digits of your phone number.
		</p>

		<form class="mt-6 space-y-4 rounded-2xl border border-cream-200 bg-white p-4" @submit.prevent="lookup">
			<div>
				<label for="code" class="block text-sm font-medium text-char-700">Tracking code</label>
				<input
					id="code"
					v-model="code"
					type="text"
					autocapitalize="characters"
					autocomplete="off"
					class="mt-1.5 h-12 w-full rounded-xl border border-cream-200 bg-white px-3 font-mono text-lg tracking-wider text-char-900 uppercase focus:border-chili-600 focus:outline-none"
					placeholder="PS-XXXX-XXXX"
				/>
			</div>

			<div>
				<label for="last4" class="block text-sm font-medium text-char-700">
					Last 4 digits of your phone
				</label>
				<input
					id="last4"
					v-model="last4"
					type="text"
					inputmode="numeric"
					maxlength="4"
					autocomplete="off"
					class="mt-1.5 h-12 w-32 rounded-xl border border-cream-200 bg-white px-3 text-center text-lg tracking-widest text-char-900 focus:border-chili-600 focus:outline-none"
					placeholder="4567"
				/>
			</div>

			<button
				type="submit"
				class="btn-primary h-12 w-full"
				:disabled="busy"
			>
				{{ busy ? 'Looking…' : 'Find my order' }}
			</button>

			<p v-if="error" class="rounded-xl bg-chili-50 px-3 py-2 text-sm text-chili-800" role="alert">
				{{ error }}
			</p>
		</form>

		<!-- Result -->
		<section v-if="order" class="mt-8 space-y-4">
			<div class="rounded-2xl border border-cream-200 bg-white p-5">
				<div class="flex flex-wrap items-start justify-between gap-3">
					<div>
						<p class="font-mono text-lg font-bold tracking-wider text-char-900">
							{{ order.tracking_code }}
						</p>
						<p class="mt-0.5 text-sm text-char-500">
							Hello {{ order.customer_first_name }} — {{ order.masked_phone }}
						</p>
					</div>
					<span
						class="rounded-full px-3 py-1 text-sm font-semibold"
						:class="statusClass"
					>
						{{ order.status }}
					</span>
				</div>

				<p class="mt-3 text-char-500">{{ order.status_note }}</p>
			</div>

			<!-- Timeline -->
			<div class="rounded-2xl border border-cream-200 bg-white p-5">
				<h2 class="font-semibold text-char-900">Progress</h2>
				<ol class="mt-4 space-y-4">
					<li v-for="step in order.timeline" :key="step.label" class="flex gap-3">
						<span
							class="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full"
							:class="step.done ? 'bg-chili-600 text-white' : 'bg-cream-200'"
						>
							<IconCheck v-if="step.done" class="size-(--size-icon-sm)" />
							<span v-else class="h-1.5 w-1.5 rounded-full bg-char-400" aria-hidden="true" />
						</span>
						<span>
							<span class="block text-sm font-medium" :class="step.done ? 'text-char-900' : 'text-char-400'">
								{{ step.label }}
							</span>
							<span v-if="step.at" class="block text-xs text-char-400">{{ formatDate(step.at) }}</span>
						</span>
					</li>
				</ol>
			</div>

			<!-- Items -->
			<div class="rounded-2xl border border-cream-200 bg-white p-5">
				<h2 class="font-semibold text-char-900">What you ordered</h2>
				<ul class="mt-4 space-y-3">
					<li v-for="(item, i) in order.items" :key="i" class="flex items-center gap-3">
						<div class="h-12 w-12 shrink-0 overflow-hidden rounded-lg bg-cream-100">
							<PackImage :src="item.image" :alt="item.pack_name" compact />
						</div>
						<div class="min-w-0 flex-1">
							<p class="truncate text-sm font-medium text-char-900">{{ item.pack_name }}</p>
							<p class="text-xs text-char-400">{{ item.qty }} × {{ money(item.rate) }}</p>
						</div>
						<p class="text-sm font-medium text-char-900">{{ money(item.amount) }}</p>
					</li>
				</ul>

				<dl class="mt-4 space-y-2 border-t border-cream-200 pt-4 text-sm">
					<div class="flex justify-between">
						<dt class="text-char-500">Subtotal</dt>
						<dd class="text-char-900">{{ money(order.items_total) }}</dd>
					</div>
					<div class="flex justify-between">
						<dt class="text-char-500">Delivery</dt>
						<dd class="text-char-900">{{ money(order.delivery_fee) }}</dd>
					</div>
					<div class="flex justify-between border-t border-cream-200 pt-2 text-base">
						<dt class="font-semibold text-char-900">Total</dt>
						<dd class="font-bold text-char-900">{{ money(order.grand_total) }}</dd>
					</div>
				</dl>
			</div>

			<!-- Payment + delivery -->
			<div class="grid gap-4 sm:grid-cols-2">
				<div class="rounded-2xl border border-cream-200 bg-white p-5">
					<h2 class="font-semibold text-char-900">Payment</h2>
					<p class="mt-2 text-sm text-char-500">{{ order.payment_method }}</p>
					<p
						class="mt-1 text-sm font-semibold"
						:class="order.payment_status === 'Paid' ? 'text-green-700' : 'text-chili-700'"
					>
						{{ order.payment_status }}
					</p>
					<p v-if="order.amount_due > 0" class="mt-2 text-sm text-char-500">
						Due: <span class="font-semibold text-char-900">{{ money(order.amount_due) }}</span>
					</p>
				</div>

				<div class="rounded-2xl border border-cream-200 bg-white p-5">
					<h2 class="font-semibold text-char-900">{{ order.fulfilment_type }}</h2>
					<p v-if="order.delivery_zone" class="mt-2 text-sm text-char-500">{{ order.delivery_zone }}</p>
					<p v-if="order.address_preview" class="mt-1 text-sm text-char-400">{{ order.address_preview }}</p>
				</div>
			</div>

			<p class="text-center text-xs text-char-400">
				Something wrong?
				<a v-if="store.whatsapp_number" :href="whatsappUrl" class="font-medium text-chili-700 transition-colors duration-(--duration-fast) hover:underline">
					Message us on WhatsApp
				</a>
				<span v-else-if="store.support_phone">Call {{ store.support_phone }}</span>
			</p>
		</section>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import PackImage from '../components/PackImage.vue';
import IconCheck from '../components/icons/IconCheck.vue';
import call, { FrappeError } from '../lib/call';
import { money } from '../lib/money';
import { store } from '../lib/boot';

const STATUS_CLASSES: Record<string, string> = {
	'Awaiting Approval': 'bg-cream-200 text-char-700',
	Approved: 'bg-chili-50 text-chili-700',
	'Out for Delivery': 'bg-blue-50 text-blue-700',
	Completed: 'bg-green-50 text-green-700',
	Cancelled: 'bg-char-900 text-white',
	Expired: 'bg-char-900 text-white',
	'Pending Payment': 'bg-cream-200 text-char-700'
};

export default defineComponent({
	name: 'TrackView',
	components: { PackImage, IconCheck },
	props: {
		// Filled from /track/:code so an SMS link prefills the code. The phone
		// digits are still required: the link alone must not reveal an address.
		code_param: { type: String, default: '' }
	},
	data() {
		return {
			store,
			code: (this.$route.params.code as string) || '',
			last4: '',
			order: null as any,
			busy: false,
			error: ''
		};
	},
	computed: {
		statusClass(): string {
			return STATUS_CLASSES[this.order?.status] || 'bg-cream-200 text-char-700';
		},
		whatsappUrl(): string {
			const text = `Hello, I have a question about order ${this.order?.tracking_code ?? ''}`;
			return `https://wa.me/${store.whatsapp_number}?text=${encodeURIComponent(text)}`;
		}
	},
	methods: {
		money,
		formatDate(value: string): string {
			if (!value) return '';
			const d = new Date(value.replace(' ', 'T'));
			if (Number.isNaN(d.getTime())) return '';
			return d.toLocaleString('en-GH', {
				day: 'numeric',
				month: 'short',
				hour: '2-digit',
				minute: '2-digit'
			});
		},
		async lookup() {
			this.error = '';
			this.order = null;

			const code = this.code.trim().toUpperCase();
			const digits = this.last4.replace(/\D/g, '');

			if (!code || digits.length !== 4) {
				this.error = 'Enter your tracking code and the last 4 digits of your phone.';
				return;
			}

			this.busy = true;
			try {
				this.order = await call('prime_shito.api.orders.track_order', {
					code,
					phone_last4: digits
				});
			} catch (err) {
				this.error = (err as FrappeError).message;
			} finally {
				this.busy = false;
			}
		}
	}
});
</script>
