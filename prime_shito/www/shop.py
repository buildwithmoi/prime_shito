"""Server context for the storefront SPA.

This backs the `shop` route, which `hooks.py` sets as the site home page. The
built Vue app is copied here as `shop.html` by `yarn build`.
"""

import frappe

from prime_shito.prime_shito.doctype.prime_shito_settings.prime_shito_settings import (
	storefront_context,
)

# Order status and cart state must never be served from the website cache.
no_cache = 1


def get_context(context):
	store = storefront_context()

	context.boot = frappe._dict(
		{
			# Harmless for guests (who carry no persisted token) but required
			# once a staff member browses the storefront while logged in.
			"csrf_token": frappe.sessions.get_csrf_token(),
			"site_name": frappe.local.site,
			"socketio_port": frappe.conf.socketio_port,
			"read_only_mode": frappe.flags.read_only,
			"store": store,
		}
	)

	# Drives WhatsApp and Facebook link previews. In Ghana a large share of
	# storefront traffic arrives through a shared WhatsApp link, so a missing
	# preview image is a real loss of conversions, not a cosmetic detail.
	business_name = store.get("business_name") or "Prime Shito"
	tagline = store.get("tagline") or ""

	context.metatags = {
		"title": f"{business_name} — {tagline}" if tagline else business_name,
		"description": store.get("meta_description")
		or store.get("about_text")
		or f"Order {business_name} shito online. Pay online or on delivery.",
		"image": store.get("og_image") or store.get("hero_image") or store.get("logo"),
		"og:type": "website",
		"twitter:card": "summary_large_image",
	}

	return context
