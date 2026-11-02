// Installing Tubesy as an app (PWA). Browsers only offer this on HTTPS (or
// localhost), with a manifest, PNG icons and a service worker.

interface InstallPrompt extends Event {
	prompt(): Promise<void>;
}

export type Check = 'ok' | 'missing' | 'pending';

export const install = $state<{
	prompt: InstallPrompt | null;
	installed: boolean;
	secure: boolean;
	// What the account page shows under "Check" – each requirement on its own.
	checks: { manifest: Check; icons: Check; worker: Check; offered: Check };
	workerError: string;
}>({
	prompt: null,
	installed: false,
	secure: true,
	checks: { manifest: 'pending', icons: 'pending', worker: 'pending', offered: 'pending' },
	workerError: ''
});

async function checkManifest() {
	try {
		const res = await fetch('/manifest.webmanifest', { cache: 'no-store' });
		const manifest = await res.json();
		install.checks.manifest = res.ok && manifest.start_url && manifest.display ? 'ok' : 'missing';
		const icons: { src: string; sizes: string }[] = manifest.icons ?? [];
		const big = icons.filter((i) => /(^|\s)(192x192|512x512)(\s|$)/.test(i.sizes));
		const loaded = await Promise.all(big.map((i) => fetch(i.src, { cache: 'no-store' }).then((r) => r.ok && (r.headers.get('content-type') ?? '').startsWith('image/'))));
		install.checks.icons = loaded.length >= 2 && loaded.every(Boolean) ? 'ok' : 'missing';
	} catch {
		install.checks.manifest = install.checks.icons = 'missing';
	}
}

export function setupInstall() {
	install.secure = window.isSecureContext;
	install.installed = matchMedia('(display-mode: standalone)').matches;
	if ('serviceWorker' in navigator && window.isSecureContext) {
		navigator.serviceWorker
			.register('/sw.js')
			.then(() => navigator.serviceWorker.ready)
			.then(() => (install.checks.worker = 'ok'))
			.catch((err) => {
				install.checks.worker = 'missing';
				install.workerError = String(err?.message ?? err);
			});
	} else {
		install.checks.worker = 'missing';
	}
	checkManifest();
	// Chromium asks first; keep the event so the account page can offer a button.
	addEventListener('beforeinstallprompt', (e) => {
		e.preventDefault();
		install.prompt = e as InstallPrompt;
		install.checks.offered = 'ok';
	});
	addEventListener('appinstalled', () => {
		install.prompt = null;
		install.installed = true;
	});
	// No offer within a few seconds: this browser does not (or not yet) consider Tubesy installable.
	setTimeout(() => {
		if (install.checks.offered === 'pending') install.checks.offered = 'missing';
	}, 8000);
}

export async function promptInstall() {
	const p = install.prompt;
	if (!p) return;
	install.prompt = null;
	await p.prompt();
}
