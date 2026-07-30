/** Shapes returned by the prime_shito catalog API. */

export interface Pack {
	pack: string;
	pack_name: string;
	route: string;
	description: string | null;
	long_description: string | null;
	image: string | null;
	image_alt: string | null;
	flavour: string | null;
	heat_level: string | null;
	net_weight_g: number;
	price: number;
	compare_at_price: number;
	min_order_qty: number;
	max_order_qty: number;
	is_featured: number;
	sold_out: boolean;
}

export interface Zone {
	zone: string;
	zone_name: string;
	region: string | null;
	delivery_fee: number;
	free_delivery_over: number;
	min_order_amount: number;
	estimated_days: number;
	delivery_days: string | null;
}

export interface QuoteLine {
	pack: string;
	pack_name: string;
	image: string | null;
	qty: number;
	rate: number;
	amount: number;
	net_weight_g: number;
}

export interface Quote {
	lines: QuoteLine[];
	items_total: number;
	delivery_fee: number;
	discount_amount: number;
	grand_total: number;
	grand_total_pesewas: number;
	total_qty: number;
	currency: string;
	free_delivery_applied: boolean;
	warnings: string[];
	blocking_errors: string[];
	is_orderable: boolean;
}

export interface Storefront {
	store: Record<string, any>;
	packs: Pack[];
	zones: Zone[];
}
