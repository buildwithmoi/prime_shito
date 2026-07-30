import { createApp } from 'vue';

import App from './App.vue';
import router from './router';
import cart from './stores/cart';
import call from './lib/call';
import { store } from './lib/boot';

// The scaffold never imported a stylesheet, which is why the app rendered
// completely unstyled and Login.vue's utility classes did nothing.
import './style.css';

const app = createApp(App);

app.use(router);

// Injected rather than imported so components stay easy to test in isolation,
// matching how the original scaffold exposed $auth/$call.
app.provide('$cart', cart);
app.provide('$call', call);
app.provide('$store', store);

app.config.globalProperties.$cart = cart;

// NOTE: the scaffold installed a global router.beforeEach guard that redirected
// every route to /login unless a session cookie was present. That is correct
// for an internal dashboard and fatal for a public storefront: it made the shop
// unreachable to the customers it exists for. Routes that genuinely need a
// session declare `meta.requiresAuth`, and none do today.

app.mount('#app');
