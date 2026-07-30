"""The single pricing authority.

Every price the customer is ever charged is computed here, from data in the
database. Nothing in this module reads a rate, amount, fee or total from a
request payload. `quote()` (what the cart calls) and `place_order()` (what
actually charges) both go through `compute()`, so the cart can never disagree
with the order, and a tampered request cannot change what is charged.
"""

from dataclasses import asdict, dataclass, field

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime, nowdate

CURRENCY = "GHS"
PRECISION = 2


@dataclass(frozen=True)
class PricedLine:
	pack: str
	pack_name: str
	image: str | None
	qty: int
	rate: float
	amount: float
	net_weight_g: int = 0

	def as_dict(self) -> dict:
		return asdict(self)


@dataclass
class Quote:
	lines: list[PricedLine] = field(default_factory=list)
	items_total: float = 0.0
	delivery_fee: float = 0.0
	discount_amount: float = 0.0
	grand_total: float = 0.0
	grand_total_pesewas: int = 0
	total_qty: int = 0
	currency: str = CURRENCY
	free_delivery_applied: bool = False
	warnings: list[str] = field(default_factory=list)
	blocking_errors: list[str] = field(default_factory=list)

	@property
	def is_orderable(self) -> bool:
		return not self.blocking_errors and bool(self.lines)

	def as_dict(self) -> dict:
		d = asdict(self)
		d["lines"] = [line.as_dict() for line in self.lines]
		d["is_orderable"] = self.is_orderable
		return d


PACK_FIELDS = (
	"name",
	"pack_name",
	"image",
	"price",
	"is_active",
	"min_order_qty",
	"max_order_qty",
	"available_from",
	"available_upto",
	"preorder_cutoff",
	"track_availability",
	"available_qty",
	"reserved_qty",
	"net_weight_g",
)


def _settings():
	return frappe.get_cached_doc("Prime Shito Settings")


def _pack_unavailable_reason(pack, settings) -> str | None:
	"""Return a customer-facing reason this pack cannot be ordered, or None."""
	if not pack.is_active:
		return _("{0} is not available right now.").format(pack.pack_name)

	today = getdate(nowdate())
	if pack.available_from and getdate(pack.available_from) > today:
		return _("{0} goes on sale on {1}.").format(
			pack.pack_name, frappe.format(pack.available_from, {"fieldtype": "Date"})
		)

	if pack.available_upto and getdate(pack.available_upto) < today:
		return _("{0} is no longer available.").format(pack.pack_name)

	if pack.preorder_cutoff and get_datetime(pack.preorder_cutoff) < now_datetime():
		return _("Pre-orders for {0} have closed for this batch.").format(pack.pack_name)

	return None


def _free_qty(pack) -> int:
	return cint(pack.available_qty) - cint(pack.reserved_qty)


def compute(
	items,
	delivery_zone: str | None = None,
	fulfilment_type: str = "Delivery",
	promo_code: str | None = None,
) -> Quote:
	"""Price a basket.

	`items` is a list of {"pack": <pack_code>, "qty": <int>}. Anything else on
	those dicts is ignored: rates and totals are never accepted from a caller.
	"""
	quote = Quote()
	settings = _settings()

	if isinstance(items, str):
		items = frappe.parse_json(items)

	if not items:
		return quote

	if not isinstance(items, list):
		frappe.throw(_("Invalid basket."))

	max_lines = cint(settings.max_lines_per_order) or 20
	if len(items) > max_lines:
		frappe.throw(_("You can order at most {0} different packs at a time.").format(max_lines))

	max_qty_per_line = cint(settings.max_qty_per_line) or 50

	# Merge duplicate lines for the same pack before pricing.
	requested: dict[str, int] = {}
	for row in items:
		if not isinstance(row, dict):
			frappe.throw(_("Invalid basket."))
		pack_code = (row.get("pack") or "").strip()
		qty = cint(row.get("qty"))
		if not pack_code:
			continue
		if qty <= 0:
			continue
		requested[pack_code] = requested.get(pack_code, 0) + qty

	if not requested:
		return quote

	packs = frappe.get_all(
		"Shito Pack",
		filters={"name": ("in", list(requested))},
		fields=list(PACK_FIELDS),
	)
	by_code = {p.name: p for p in packs}

	for pack_code, qty in requested.items():
		pack = by_code.get(pack_code)
		if not pack:
			quote.blocking_errors.append(_("One of the packs in your basket no longer exists."))
			continue

		reason = _pack_unavailable_reason(pack, settings)
		if reason:
			quote.blocking_errors.append(reason)
			continue

		min_qty = max(cint(pack.min_order_qty), 1)
		if qty < min_qty:
			qty = min_qty
			quote.warnings.append(_("{0} is sold in a minimum of {1}.").format(pack.pack_name, min_qty))

		ceiling = max_qty_per_line
		if cint(pack.max_order_qty) > 0:
			ceiling = min(ceiling, cint(pack.max_order_qty))
		if qty > ceiling:
			qty = ceiling
			quote.warnings.append(_("You can order at most {0} of {1}.").format(ceiling, pack.pack_name))

		if cint(pack.track_availability):
			free = _free_qty(pack)
			if free <= 0:
				quote.blocking_errors.append(_("{0} is sold out.").format(pack.pack_name))
				continue
			if qty > free:
				qty = free
				quote.warnings.append(
					_("Only {0} of {1} left, so we reduced your quantity.").format(free, pack.pack_name)
				)

		rate = flt(pack.price, PRECISION)
		amount = flt(rate * qty, PRECISION)

		quote.lines.append(
			PricedLine(
				pack=pack.name,
				pack_name=pack.pack_name,
				image=pack.image,
				qty=qty,
				rate=rate,
				amount=amount,
				net_weight_g=cint(pack.net_weight_g),
			)
		)
		quote.total_qty += qty
		quote.items_total = flt(quote.items_total + amount, PRECISION)

	quote.delivery_fee = _delivery_fee(quote, delivery_zone, fulfilment_type)

	# Promo codes are a planned fast-follow. The seam exists so that adding them
	# never requires touching a caller.
	quote.discount_amount = 0.0

	quote.grand_total = flt(quote.items_total + quote.delivery_fee - quote.discount_amount, PRECISION)
	# Integer minor units. This is the only value ever compared against a
	# gateway amount, so it must never be a float.
	quote.grand_total_pesewas = round(quote.grand_total * 100)

	_check_minimums(quote, settings, delivery_zone, fulfilment_type)

	return quote


def _delivery_fee(quote: Quote, delivery_zone: str | None, fulfilment_type: str) -> float:
	if fulfilment_type == "Pickup":
		return 0.0

	if not delivery_zone:
		# Not an error yet: the cart shows a total before a zone is chosen.
		return 0.0

	zone = frappe.db.get_value(
		"Shito Delivery Zone",
		delivery_zone,
		["delivery_fee", "free_delivery_over", "is_active"],
		as_dict=True,
	)

	if not zone or not zone.is_active:
		quote.blocking_errors.append(_("We do not deliver to that area yet."))
		return 0.0

	threshold = flt(zone.free_delivery_over)
	if threshold > 0 and quote.items_total >= threshold:
		quote.free_delivery_applied = True
		return 0.0

	return flt(zone.delivery_fee, PRECISION)


def money(value) -> str:
	"""Format an amount for display, e.g. 1234.5 -> "1,234.50".

	Deliberately does not use `frappe.utils.fmt_money`, which prefixes the cedi
	symbol. That symbol is outside GSM-7, and these strings reach SMS templates
	where a single one cuts the segment size from 160 characters to 70. Callers
	prepend a literal "GHS".
	"""
	return f"{flt(value, PRECISION):,.2f}"


def _check_minimums(quote: Quote, settings, delivery_zone: str | None, fulfilment_type: str) -> None:
	if not quote.lines:
		return

	store_min = flt(settings.min_order_amount)
	if store_min > 0 and quote.items_total < store_min:
		quote.blocking_errors.append(
			_("Minimum order is GHS {0}. Please add a little more.").format(money(store_min))
		)

	if delivery_zone and fulfilment_type != "Pickup":
		zone_min = flt(frappe.db.get_value("Shito Delivery Zone", delivery_zone, "min_order_amount"))
		if zone_min > 0 and quote.items_total < zone_min:
			quote.blocking_errors.append(
				_("Orders to this area must be at least GHS {0}.").format(money(zone_min))
			)


def apply_to_order(order) -> None:
	"""Overwrite every money field on a Shito Order from the database.

	Called unconditionally from ShitoOrder.validate(), including on staff saves
	in Desk. Marking a field read_only in the DocType JSON does not stop an API
	caller from setting it -- only recomputing does.
	"""
	basket = [{"pack": row.pack, "qty": row.qty} for row in (order.items or [])]

	quote = compute(
		basket,
		delivery_zone=order.get("delivery_zone"),
		fulfilment_type=order.get("fulfilment_type") or "Delivery",
	)

	if quote.blocking_errors:
		frappe.throw("<br>".join(quote.blocking_errors))

	priced = {line.pack: line for line in quote.lines}

	for row in list(order.items or []):
		line = priced.get(row.pack)
		if not line:
			order.remove(row)
			continue
		row.qty = line.qty
		row.rate = line.rate
		row.amount = line.amount
		row.pack_name = line.pack_name
		row.image = line.image
		row.net_weight_g = line.net_weight_g

	order.currency = CURRENCY
	order.items_total = quote.items_total
	order.delivery_fee = quote.delivery_fee
	order.discount_amount = quote.discount_amount
	order.grand_total = quote.grand_total
	order.grand_total_pesewas = quote.grand_total_pesewas
	order.amount_due = flt(quote.grand_total - flt(order.amount_paid), PRECISION)
