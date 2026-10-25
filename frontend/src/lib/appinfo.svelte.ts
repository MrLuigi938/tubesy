import { api } from './api';

export const REPO = 'https://github.com/MrLuigi938/tubesy';

export interface UpdateInfo {
	version: string;
	url: string;
	published: string | null;
}

/** Version of the server and, when its update check found one, the newer release. */
export const appInfo = $state<{ version: string; update: UpdateInfo | null }>({ version: '', update: null });

export async function refreshInfo(): Promise<void> {
	try {
		Object.assign(appInfo, await api.get<{ version: string; update: UpdateInfo | null }>('/api/info'));
	} catch {
		/* not signed in or offline: keep what we have */
	}
}

/** Released versions only; "dev" and "edge-…" builds are shown as such. */
export const isRelease = (v: string) => /^\d+\.\d+\.\d+/.test(v);

export function channel(v: string): string {
	if (!isRelease(v)) return v.startsWith('edge') ? 'Entwicklungsstand (edge)' : '';
	return v.includes('-') ? 'Testversion (Beta)' : 'Stabile Version';
}

// A newer release that is out for more than three days gets a red dot on
// "Verwaltung". ?updatehint in the address shows it right away to try it out
// (only when a newer version is actually there).
const STALE_DAYS = 3;
export function updateStale(update: UpdateInfo | null): boolean {
	if (!update?.published) return false;
	const forced = typeof location !== 'undefined' && new URLSearchParams(location.search).has('updatehint');
	return forced || Date.now() - Date.parse(update.published) > STALE_DAYS * 86400e3;
}
