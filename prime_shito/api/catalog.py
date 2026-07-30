"""Public catalog endpoints.

Everything here is reachable by an anonymous visitor, so three rules hold
throughout:

1. Responses are explicit projections. We never hand back a Document or
   `as_dict()`, because Shito Pack carries internal stock counters and the
   ERPNext link, and Prime Shito Settings carries API secrets.
2. Every endpoint is rate limited. Guest sessions carry no persisted CSRF
   token in Frappe, so CSRF provides no protection here at all.
3. No endpoint accepts a doctype name, a fieldname or a filter dict from the
   caller. Whitelisting anything that does would be a data-leak primitive.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from prime_shito.prime_shito.doctype.prime_shito_settings.prime_shito_settings import (
	storefront_context,
)
from prime_shito.shito import pricing

STOREFRONT_CACHE_KEY = "prime_shito_storefront"
STOREFRONT_CACHE_TTL = 300


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=120, seconds=60)
def get_storefront() -> dict:
	"""Everything the shop needs for a first paint: config, packs and zones."""
	cached = frappe.cache.get_value(STOREFRONT_CACHE_KEY)
	if cached:
		return cached

	payload = {
		"store": storefront_context(),
		"packs": _active_packs(),
		"zones": _active_zones(),
	}

	frappe.cache.set_value(STOREFRONT_CACHE_KEY, payload, expires_in_sec=STOREFRONT_CACHE_TTL)
	return payload


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=120, seconds=60)
def get_pack(pack: str) -> dict:
	"""Fetch one pack by its code or its URL slug."""
	pack = (pack or "").strip()
	if not pack:
		frappe.throw(_("Pack not found."), frappe.DoesNotExistError)

	name = frappe.db.get_value("Shito Pack", {"route": pack, "is_active": 1}, "name")
	if not name:
		name = frappe.db.get_value("Shito Pack", {"name": pack, "is_active": 1}, "name")

	if not name:
		# Same message whether it never existed or was deactivated: no reason to
		# confirm which pack codes are real.
		frappe.throw(_("Pack not found."), frappe.DoesNotExistError)

	doc = frappe.get_cached_doc("Shito Pack", name)
	return doc.as_storefront_dict()


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=60)
def quote(
	items: str,
	delivery_zone: str | None = None,
	fulfilment_type: str = "Delivery",
	promo_code: str | None = None,
) -> dict:
	"""Price a basket.

	The cart calls this on every change. It is the same code path `place_order`
	uses, so what the customer is shown is what they will be charged.
	"""
	if fulfilment_type not in ("Delivery", "Pickup"):
		fulfilment_type = "Delivery"

	result = pricing.compute(
		items,
		delivery_zone=delivery_zone,
		fulfilment_type=fulfilment_type,
		promo_code=promo_code,
	)
	return result.as_dict()


def _active_packs() -> list[dict]:
	names = frappe.get_all(
		"Shito Pack",
		filters={"is_active": 1},
		order_by="display_order asc, pack_name asc",
		pluck="name",
	)
	return [frappe.get_cached_doc("Shito Pack", n).as_storefront_dict() for n in names]


def _active_zones() -> list[dict]:
	names = frappe.get_all(
		"Shito Delivery Zone",
		filters={"is_active": 1},
		order_by="display_order asc, zone_name asc",
		pluck="name",
	)
	return [frappe.get_cached_doc("Shito Delivery Zone", n).as_storefront_dict() for n in names]


def clear_storefront_cache(doc=None, method=None):
	"""Bust the storefront cache. Wired to pack, zone and settings updates."""
	frappe.cache.delete_value(STOREFRONT_CACHE_KEY)
