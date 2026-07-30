import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

import Home from '../views/Home.vue';

// Only the home route is eager. Everything else is split so the first paint on
// a slow connection ships as little JavaScript as possible.
const routes: RouteRecordRaw[] = [
	{ path: '/', name: 'Home', component: Home },
	{
		path: '/packs',
		name: 'Catalog',
		component: () => import('../views/Catalog.vue')
	},
	{
		path: '/packs/:route',
		name: 'PackDetail',
		component: () => import('../views/PackDetail.vue'),
		props: true
	},
	{
		path: '/cart',
		name: 'Cart',
		component: () => import('../views/Cart.vue')
	},
	{
		path: '/checkout',
		name: 'Checkout',
		component: () => import('../views/Checkout.vue')
	},
	{
		path: '/track',
		name: 'Track',
		component: () => import('../views/Track.vue')
	},
	{
		// SMS links land here with the code prefilled. The last 4 phone digits
		// are still required, so a forwarded link cannot expose an address.
		path: '/track/:code',
		name: 'TrackCode',
		component: () => import('../views/Track.vue')
	},
	{
		path: '/about',
		name: 'About',
		component: () => import('../views/About.vue')
	},
	{
		path: '/contact',
		name: 'Contact',
		component: () => import('../views/Contact.vue')
	},
	{
		path: '/:pathMatch(.*)*',
		name: 'NotFound',
		component: () => import('../views/NotFound.vue')
	}
];

const router = createRouter({
	// The storefront is the site root, not a sub-path.
	history: createWebHistory('/'),
	routes,
	scrollBehavior(to, _from, saved) {
		if (saved) return saved;
		if (to.hash) return { el: to.hash, behavior: 'smooth' };
		return { top: 0 };
	}
});

export default router;
