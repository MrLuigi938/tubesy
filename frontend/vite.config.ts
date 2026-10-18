import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

const backend = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			// Single-page app: FastAPI serves index.html for every non-API route.
			adapter: adapter({ pages: 'build', assets: 'build', fallback: 'index.html' })
		})
	],
	server: {
		proxy: { '/api': { target: backend, ws: true, changeOrigin: false } }
	}
});
