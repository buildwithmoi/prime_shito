import path from 'path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import tailwindcss from '@tailwindcss/vite';
import proxyOptions from './proxyOptions.ts';

// https://vitejs.dev/config/
export default defineConfig({
	plugins: [vue(), tailwindcss()],
	server: {
		port: 8080,
		host: '0.0.0.0',
		proxy: proxyOptions
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src')
		}
	},
	build: {
		outDir: '../prime_shito/public/shop',
		emptyOutDir: true,
		// es2015 was the scaffold default. Every Android Chrome since 2020
		// handles es2020, and it produces meaningfully smaller output, which
		// matters on metered mobile data.
		target: 'es2020',
		chunkSizeWarningLimit: 600
	}
});
