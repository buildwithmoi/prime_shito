/**
 * Money formatting.
 *
 * Always renders "GHS 120.00", never the cedi symbol. Two reasons: the symbol
 * is outside the GSM-7 alphabet so it is banned from anything that may reach an
 * SMS, and keeping one representation everywhere means the price on the card,
 * in the cart and in the confirmation SMS always read identically.
 */

export function money(value: number | string | null | undefined): string {
	const n = Number(value ?? 0);
	if (!Number.isFinite(n)) return 'GHS 0.00';
	return `GHS ${n.toLocaleString('en-GH', {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2
	})}`;
}

/** Bare number, for places where the currency is already implied by a label. */
export function amount(value: number | string | null | undefined): string {
	const n = Number(value ?? 0);
	if (!Number.isFinite(n)) return '0.00';
	return n.toLocaleString('en-GH', {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2
	});
}

export default money;
