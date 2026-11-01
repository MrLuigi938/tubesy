// Tubesy service worker – makes the app installable in every Chromium browser.
// It caches nothing on purpose (updates are visible at once); it only passes
// page loads through and shows a short note when the server is not reachable.

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

const OFFLINE = `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tubesy</title><body style="font-family:system-ui,sans-serif;background:#0f1115;color:#e9ebef;display:grid;place-items:center;min-height:100vh;margin:0;text-align:center">
<div><p style="font-size:1.2rem;font-weight:600">Tubesy is not reachable</p><p style="color:#98a0ad">Tubesy ist nicht erreichbar – bitte Verbindung prüfen.</p>
<button onclick="location.reload()" style="margin-top:1rem;padding:.6rem 1.2rem;border:0;border-radius:.5rem;background:#ef5359;color:#fff;font-weight:600">Retry · Erneut versuchen</button></div>`;

self.addEventListener('fetch', (event) => {
	if (event.request.mode !== 'navigate') return;
	event.respondWith(
		fetch(event.request).catch(() => new Response(OFFLINE, { headers: { 'Content-Type': 'text/html; charset=utf-8' } }))
	);
});
