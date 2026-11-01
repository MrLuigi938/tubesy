// Browser notifications when a download finishes while Tubesy is in the background.
// Chosen per browser; ntfy and Telegram are set up on the server (Account page).
import { t } from './i18n.svelte';
import type { Download } from './types';

const KEY = 'tubesy-browser-notify';
const RUNNING = new Set(['queued', 'downloading', 'processing']);

function saved(): boolean {
	try {
		return localStorage.getItem(KEY) === '1';
	} catch {
		return false;
	}
}

export const browserNotify = $state({
	enabled: typeof window !== 'undefined' && saved(),
	supported: typeof window !== 'undefined' && 'Notification' in window
});

export async function setBrowserNotify(on: boolean): Promise<boolean> {
	if (on && browserNotify.supported && Notification.permission !== 'granted') {
		on = (await Notification.requestPermission()) === 'granted';
	}
	browserNotify.enabled = on;
	try {
		localStorage.setItem(KEY, on ? '1' : '0');
	} catch {
		/* private mode */
	}
	return on;
}

// Last status seen per download: only a change from running to finished is reported.
const last = new Map<number, string>();

export function onDownloadEvent(d: Download, ownUserId: number | undefined) {
	const before = last.get(d.id);
	last.set(d.id, d.status);
	if (d.user_id !== ownUserId || !before || !RUNNING.has(before)) return;
	if (d.status !== 'completed' && d.status !== 'failed') return;
	if (!browserNotify.enabled || !browserNotify.supported || Notification.permission !== 'granted') return;
	if (document.visibilityState === 'visible') return;
	const title = d.hidden ? t('Ausgeblendetes Video') : (d.title ?? d.url);
	new Notification(d.status === 'completed' ? t('Fertig') : t('Fehlgeschlagen'), { body: title, icon: '/icon-192.png', tag: `tubesy-${d.id}` });
}
