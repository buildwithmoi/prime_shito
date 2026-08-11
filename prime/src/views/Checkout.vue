<template>
	<div class="mx-auto max-w-2xl px-4 py-8">
		<!-- Success -->
		<!-- No party popper. The customer has just spent money and is looking for
		     their tracking code; the app congratulating itself is not what the
		     moment is for. Lead with the code. -->
		<div v-if="placed" class="text-center">
			<h1 class="text-2xl font-bold text-char-900">Order received</h1>
			<p class="mt-2 text-char-500">
				Thank you, {{ firstName }}. We will confirm your order shortly.
			</p>

			<div class="mt-6 rounded-2xl border-2 border-dashed border-chili-200 bg-chili-50 p-5">
				<p class="text-xs font-medium uppercase tracking-wide text-chili-700">Your tracking code</p>
				<p class="mt-1 text-2xl font-bold tracking-wider text-char-900">{{ placed.tracking_code }}</p>
				<p class="mt-2 text-sm text-char-500">
					Keep this. Enter it with the last 4 digits of your phone to check your order any time.
				</p>
			</div>

			<dl class="mt-6 space-y-2 rounded-2xl border border-cream-200 bg-white p-4 text-sm">
				<div class="flex justify-between">
					<dt class="text-char-500">Total</dt>
					<dd class="font-bold text-char-900">{{ money(placed.grand_total) }}</dd>
				</div>
				<div class="flex justify-between">
					<dt class="text-char-500">Payment</dt>
					<dd class="font-medium text-char-900">{{ placed.payment_method }}</dd>
				</div>
			</dl>

			<div class="mt-6 flex flex-col gap-3">
				<router-link :to="`/track/${placed.tracking_code}`" class="btn-primary">
					Track this order
				</router-link>
				<router-link
					to="/packs"
					class="text-sm font-medium text-chili-700 transition-colors duration-(--duration-fast) hover:underline"
				>
					Order something else
				</router-link>
			</div>
		</div>

		<!-- Checkout -->
		<div v-else>
			<h1 class="text-3xl font-bold tracking-tight text-char-900">Checkout</h1>

			<!-- Steps -->
			<ol class="mt-6 flex items-center gap-2 text-xs font-medium">
				<li
					v-for="(label, i) in stepLabels"
					:key="label"
					class="flex flex-1 items-center gap-2"
					:aria-current="step === i + 1 ? 'step' : undefined"
				>
					<span
						class="grid h-7 w-7 shrink-0 place-items-center rounded-full transition-colors duration-(--duration-fast)"
						:class="step >= i + 1 ? 'bg-chili-600 text-white' : 'bg-cream-200 text-char-500'"
					>
						<IconCheck v-if="step > i + 1" class="size-(--size-icon-sm)" />
						<template v-else>{{ i + 1 }}</template>
					</span>
					<span class="hidden sm:inline" :class="step >= i + 1 ? 'text-char-900' : 'text-char-400'">
						{{ label }}
					</span>
				</li>
			</ol>

			<!-- On a phone the row above is four numbered circles and nothing else,
			     which announces "this takes 4 steps" without saying what any of them
			     are. This line carries the words the circles cannot. -->
			<p class="mt-2 text-sm font-medium text-char-700 sm:hidden">
				Step {{ step }} of {{ stepLabels.length }} · {{ stepLabels[step - 1] }}
			</p>

			<StateBlock
				v-if="cartEmpty"
				:empty-icon="IconCart"
				empty-title="Your cart is empty"
				empty-text="Add a pack before checking out."
			>
				<template #empty-action>
					<router-link
						to="/packs"
						class="btn-primary mt-5 h-11 px-5 text-sm"
					>
						Browse packs
					</router-link>
				</template>
			</StateBlock>

			<form v-else class="mt-8 space-y-6" @submit.prevent="onSubmit">
				<!-- Steps are v-if rather than v-show: display cannot be animated.
				     Safe because every value lives in data().form, not in the DOM, so
				     nothing is lost going back from Verify to Details. -->
				<Transition name="page" mode="out-in" @after-enter="onStepShown">
					<!-- 1. Contact -->
					<fieldset v-if="step === 1" key="step-1" class="space-y-4 rounded-2xl border border-cream-200 bg-white p-4">
						<legend class="px-1 text-sm font-semibold text-char-900">Your details</legend>

						<div>
							<label for="name" class="block text-sm font-medium text-char-700">Full name</label>
							<input
								id="name"
								v-model="form.customer_name"
								type="text"
								autocomplete="name"
								maxlength="140"
								class="mt-1.5 h-12 w-full rounded-xl border border-cream-200 bg-white px-3 text-char-900 focus:border-chili-600 focus:outline-none"
								placeholder="Ama Mensah"
							/>
						</div>

						<PhoneInput v-model="form.phone" :error="errors.phone" />
					</fieldset>

					<!-- 2. Verify -->
					<fieldset v-else-if="step === 2" key="step-2" class="space-y-4 rounded-2xl border border-cream-200 bg-white p-4">
						<legend class="px-1 text-sm font-semibold text-char-900">Verify your number</legend>

						<p class="text-sm text-char-500">
							We sent a code to <span class="font-medium text-char-900">{{ maskedPhone }}</span
							>. This makes sure we can reach you about your order.
						</p>

						<div v-if="devOtp" class="rounded-xl bg-cream-100 px-3 py-2 text-sm text-char-700">
							Developer mode — your code is <strong>{{ devOtp }}</strong>
						</div>

						<OtpInput ref="otp" v-model="form.otp" :error="errors.otp" @complete="verifyOtp" />

						<div class="flex items-center justify-between text-sm">
							<button
								type="button"
								class="font-medium text-chili-700 transition-colors duration-(--duration-fast) hover:underline disabled:text-char-400 disabled:no-underline"
								:disabled="resendIn > 0 || busy"
								@click="requestOtp"
							>
								{{ resendIn > 0 ? `Resend in ${resendIn}s` : 'Resend code' }}
							</button>
							<button type="button" class="text-char-500 transition-colors duration-(--duration-fast) hover:text-chili-700" @click="step = 1">
								Change number
							</button>
						</div>
					</fieldset>

					<!-- 3. Delivery -->
					<fieldset v-else-if="step === 3" key="step-3" class="space-y-4 rounded-2xl border border-cream-200 bg-white p-4">
						<legend class="px-1 text-sm font-semibold text-char-900">Where should we send it?</legend>

						<div class="flex gap-2">
							<button
								v-for="type in (['Delivery', 'Pickup'] as const)"
								:key="type"
								type="button"
								class="h-11 flex-1 rounded-xl text-sm font-medium transition-colors duration-(--duration-fast)"
								:class="
									fulfilmentType === type
										? 'bg-chili-600 text-white'
										: 'border border-cream-200 text-char-700 hover:border-chili-200'
								"
								@click="setFulfilment(type)"
							>
								{{ type }}
							</button>
						</div>

						<template v-if="fulfilmentType === 'Delivery'">
							<div>
								<label for="zone" class="block text-sm font-medium text-char-700">Delivery area</label>
								<select
									id="zone"
									class="mt-1.5 h-12 w-full rounded-xl border border-cream-200 bg-white px-3 text-char-900 focus:border-chili-600 focus:outline-none"
									:value="zone ?? ''"
									@change="onZoneChange"
								>
									<option value="">Select your area…</option>
									<option v-for="z in sf.zones" :key="z.zone" :value="z.zone">
										{{ z.zone_name }} — {{ money(z.delivery_fee) }}
									</option>
								</select>
								<p v-if="errors.zone" class="mt-1 text-xs text-chili-700">{{ errors.zone }}</p>
							</div>

							<div>
								<label for="address" class="block text-sm font-medium text-char-700">Address</label>
								<textarea
									id="address"
									v-model="form.delivery_address"
									rows="2"
									maxlength="500"
									class="mt-1.5 w-full rounded-xl border border-cream-200 bg-white p-3 text-char-900 focus:border-chili-600 focus:outline-none"
									placeholder="House number, street, area"
								/>
								<p v-if="errors.address" class="mt-1 text-xs text-chili-700">{{ errors.address }}</p>
							</div>

							<div>
								<label for="landmark" class="block text-sm font-medium text-char-700">
									Nearest landmark <span class="font-normal text-char-400">(optional)</span>
								</label>
								<input
									id="landmark"
									v-model="form.landmark"
									type="text"
									maxlength="140"
									class="mt-1.5 h-12 w-full rounded-xl border border-cream-200 bg-white px-3 text-char-900 focus:border-chili-600 focus:outline-none"
									placeholder="Opposite the filling station"
								/>
								<p class="mt-1 text-xs text-char-400">Landmarks help our riders far more than street names.</p>
							</div>
						</template>

						<div>
							<label for="notes" class="block text-sm font-medium text-char-700">
								Notes <span class="font-normal text-char-400">(optional)</span>
							</label>
							<textarea
								id="notes"
								v-model="form.delivery_notes"
								rows="2"
								maxlength="500"
								class="mt-1.5 w-full rounded-xl border border-cream-200 bg-white p-3 text-char-900 focus:border-chili-600 focus:outline-none"
								placeholder="Call when you arrive"
							/>
						</div>
					</fieldset>

					<!-- 4. Payment -->
					<fieldset v-else key="step-4" class="space-y-4 rounded-2xl border border-cream-200 bg-white p-4">
						<legend class="px-1 text-sm font-semibold text-char-900">How would you like to pay?</legend>

						<label
							v-if="store.allow_pay_on_delivery"
							class="flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition-colors duration-(--duration-fast)"
							:class="form.payment_method === 'Pay on Delivery' ? 'border-chili-600 bg-chili-50' : 'border-cream-200'"
						>
							<input v-model="form.payment_method" type="radio" value="Pay on Delivery" class="mt-1" />
							<span>
								<span class="block font-medium text-char-900">Pay on delivery</span>
								<span class="block text-sm text-char-500">
									Pay cash or Mobile Money when your order reaches you.
								</span>
							</span>
						</label>

						<label
							v-if="store.allow_online_payment"
							class="flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition-colors duration-(--duration-fast)"
							:class="form.payment_method === 'Pay Online' ? 'border-chili-600 bg-chili-50' : 'border-cream-200'"
						>
							<input v-model="form.payment_method" type="radio" value="Pay Online" class="mt-1" />
							<span>
								<span class="block font-medium text-char-900">Pay online now</span>
								<span class="block text-sm text-char-500">Mobile Money or card.</span>
							</span>
						</label>

						<label class="flex cursor-pointer items-start gap-3 pt-2">
							<input v-model="form.marketing_consent" type="checkbox" class="mt-1" />
							<span class="text-sm text-char-500">
								Text me about new flavours and offers. You can stop this any time.
							</span>
						</label>

						<!-- Honeypot: hidden from people, filled by scripted spam. -->
						<div class="hidden" aria-hidden="true">
							<label>Do not fill this<input v-model="form.hp" type="text" tabindex="-1" autocomplete="off" /></label>
						</div>
					</fieldset>
				</Transition>

				<!-- Summary. Shared with Cart so the two cannot drift. -->
				<OrderSummary :quote="quote" :awaiting-zone="fulfilmentType === 'Delivery' && !zone" />

				<div v-if="formError" class="rounded-xl border border-chili-200 bg-chili-50 px-4 py-3 text-sm text-chili-800" role="alert">
					{{ formError }}
				</div>

				<div class="flex gap-3">
					<button
						v-if="step > 1 && step !== 2"
						type="button"
						class="btn-secondary h-12 px-5"
						@click="step--"
					>
						Back
					</button>
					<button
						type="submit"
						class="btn-primary h-12 flex-1"
						:disabled="busy"
					>
						{{ busy ? 'Please wait…' : submitLabel }}
					</button>
				</div>
			</form>
		</div>
	</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import PhoneInput from '../components/PhoneInput.vue';
import OtpInput from '../components/OtpInput.vue';
import StateBlock from '../components/StateBlock.vue';
import OrderSummary from '../components/OrderSummary.vue';
import IconCart from '../components/icons/IconCart.vue';
import IconCheck from '../components/icons/IconCheck.vue';
import cart from '../stores/cart';
import call, { FrappeError } from '../lib/call';
import { money } from '../lib/money';
import { store } from '../lib/boot';
import { state as sf, loadStorefront } from '../lib/storefront';
import type { Quote } from '../lib/types';

export default defineComponent({
	name: 'CheckoutView',
	components: { PhoneInput, OtpInput, StateBlock, OrderSummary, IconCheck },
	emits: ['catalog-loaded'],
	data() {
		return {
			IconCart,
			sf,
			store,
			step: 1,
			stepLabels: ['Details', 'Verify', 'Delivery', 'Payment'],
			busy: false,
			formError: '',
			errors: {} as Record<string, string>,
			quote: null as Quote | null,
			placed: null as any,
			devOtp: '',
			resendIn: 0,
			timer: 0 as unknown as ReturnType<typeof setInterval>,
			verificationToken: '',
			form: {
				customer_name: '',
				phone: '',
				otp: '',
				delivery_address: '',
				landmark: '',
				delivery_notes: '',
				payment_method: 'Pay on Delivery',
				marketing_consent: false,
				hp: ''
			}
		};
	},
	computed: {
		cartEmpty(): boolean {
			return cart.isEmpty.value;
		},
		zone(): string | null {
			return cart.state.zone;
		},
		fulfilmentType(): 'Delivery' | 'Pickup' {
			return cart.state.fulfilmentType;
		},
		firstName(): string {
			return (this.form.customer_name || '').split(' ')[0];
		},
		maskedPhone(): string {
			const d = this.form.phone.replace(/\D/g, '');
			return d ? `+233 ${d.slice(1, 3)} *** **${d.slice(-2)}` : '';
		},
		submitLabel(): string {
			if (this.step === 1) return 'Continue';
			if (this.step === 2) return 'Verify code';
			if (this.step === 3) return 'Continue to payment';
			return `Place order — ${money(this.quote?.grand_total ?? 0)}`;
		}
	},
	async created() {
		await loadStorefront();
		if (sf.packs.length) this.$emit('catalog-loaded', sf.packs);
		this.refreshQuote();
	},
	beforeUnmount() {
		clearInterval(this.timer);
	},
	methods: {
		money,
		/**
		 * Focus the code field once the step has finished animating in.
		 * `$nextTick` is too early with `mode="out-in"`: the incoming fieldset is
		 * not mounted until the outgoing one has left.
		 */
		onStepShown() {
			if (this.step === 2) (this.$refs.otp as { focus?: () => void } | undefined)?.focus?.();
		},
		setFulfilment(type: 'Delivery' | 'Pickup') {
			cart.setFulfilmentType(type);
			this.refreshQuote();
		},
		onZoneChange(event: Event) {
			cart.setZone((event.target as HTMLSelectElement).value || null);
			this.refreshQuote();
		},
		async refreshQuote() {
			if (cart.isEmpty.value) return;
			try {
				this.quote = await call<Quote>('prime_shito.api.catalog.quote', {
					items: JSON.stringify(cart.payload()),
					delivery_zone: cart.state.zone,
					fulfilment_type: cart.state.fulfilmentType
				});
			} catch {
				/* the summary just shows the previous total; placing re-validates */
			}
		},

		onSubmit() {
			this.formError = '';
			this.errors = {};

			if (this.step === 1) return this.startVerification();
			if (this.step === 2) return this.verifyOtp();
			if (this.step === 3) return this.goToPayment();
			return this.submitOrder();
		},

		async startVerification() {
			if (!this.form.customer_name.trim()) {
				this.formError = 'Please enter your name.';
				return;
			}
			if (this.form.phone.replace(/\D/g, '').length < 10) {
				this.errors = { phone: 'Enter your 9-digit number, e.g. 24 123 4567.' };
				return;
			}
			await this.requestOtp();
		},

		async requestOtp() {
			this.busy = true;
			this.formError = '';
			try {
				const res = await call<any>('prime_shito.api.orders.request_otp', {
					phone: this.form.phone
				});
				this.devOtp = res.dev_otp || '';
				this.step = 2;
				this.startResendTimer(res.resend_in || 60);
			} catch (err) {
				this.formError = (err as FrappeError).message;
			} finally {
				this.busy = false;
			}
		},

		startResendTimer(seconds: number) {
			clearInterval(this.timer);
			this.resendIn = seconds;
			this.timer = setInterval(() => {
				this.resendIn -= 1;
				if (this.resendIn <= 0) clearInterval(this.timer);
			}, 1000);
		},

		async verifyOtp() {
			if (this.form.otp.length < 4) {
				this.errors = { otp: 'Enter the code we sent you.' };
				return;
			}
			this.busy = true;
			this.formError = '';
			try {
				const res = await call<any>('prime_shito.api.orders.verify_otp', {
					phone: this.form.phone,
					otp_code: this.form.otp
				});
				this.verificationToken = res.verification_token;
				this.step = 3;
			} catch (err) {
				this.errors = { otp: (err as FrappeError).message };
			} finally {
				this.busy = false;
			}
		},

		goToPayment() {
			if (this.fulfilmentType === 'Delivery') {
				if (!this.zone) {
					this.errors = { zone: 'Please choose your delivery area.' };
					return;
				}
				if (!this.form.delivery_address.trim()) {
					this.errors = { address: 'Please enter where we should deliver.' };
					return;
				}
			}
			this.step = 4;
			this.refreshQuote();
		},

		async submitOrder() {
			this.busy = true;
			this.formError = '';
			try {
				const res = await call<any>('prime_shito.api.orders.place_order', {
					customer_name: this.form.customer_name,
					phone: this.form.phone,
					verification_token: this.verificationToken,
					items: JSON.stringify(cart.payload()),
					payment_method: this.form.payment_method,
					fulfilment_type: this.fulfilmentType,
					delivery_zone: this.zone,
					delivery_address: this.form.delivery_address,
					landmark: this.form.landmark,
					delivery_notes: this.form.delivery_notes,
					marketing_consent: this.form.marketing_consent ? 1 : 0,
					hp: this.form.hp
				});
				this.placed = res;
				cart.clear();
			} catch (err) {
				this.formError = (err as FrappeError).message;
				// The verification token is single-use and has now been burnt, so
				// a retry has to start from the phone step rather than silently
				// failing again.
				if (/verify/i.test(this.formError)) {
					this.verificationToken = '';
					this.step = 1;
				}
			} finally {
				this.busy = false;
			}
		}
	}
});
</script>
