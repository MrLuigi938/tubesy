// Installing Tubesy as an app (PWA). Browsers only offer this on HTTPS (or
// localhost), with a manifest, PNG icons and a service worker.

interface InstallPrompt extends Event {
	prompt(): Promise<void>;
}

export const install = $state<{ prompt: InstallPrompt | null; installed: boolean; secure: boolean }>({
	prompt: null,
	installed: false,
	secure: true
});

export function setupInstall() {
	install.secure = window.isSecureContext;
	install.installed = matchMedia('(display-mode: standalone)').matches;
	if ('serviceWorker' in navigator && window.isSecureContext) {
		navigator.serviceWorker.register('/sw.js').catch(() => {});
	}
	// Chromium asks first; keep the event so the account page can offer a button.
	addEventListener('beforeinstallprompt', (e) => {
		e.preventDefault();
		install.prompt = e as InstallPrompt;
	});
	addEventListener('appinstalled', () => {
		install.prompt = null;
		install.installed = true;
	});
}

export async function promptInstall() {
	const p = install.prompt;
	if (!p) return;
	install.prompt = null;
	await p.prompt();
}
