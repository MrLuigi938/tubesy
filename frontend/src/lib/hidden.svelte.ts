import { api } from './api';
import type { Download } from './types';

/**
 * Hidden videos come from the server without title, thumbnail, link and file name.
 * "Tap to reveal" loads them for the current view; leaving the page hides them again.
 */
export const revealed = $state<Record<number, Download>>({});

export async function reveal(id: number): Promise<Download> {
	const full = await api.get<Download>(`/api/downloads/${id}`);
	revealed[id] = full;
	return full;
}

export function hideAll() {
	for (const id of Object.keys(revealed)) delete revealed[Number(id)];
}

/** A hidden download that has not been revealed in this view. */
export const masked = (d: Download) => d.hidden && !revealed[d.id];

/** The download as it may be shown: live fields from d, the hidden ones once revealed. */
export function shown(d: Download): Download {
	const r = d.hidden ? revealed[d.id] : undefined;
	if (!r) return d;
	const { url, video_id, title, uploader, thumbnail, playlist_title, filename } = r;
	return { ...d, url, video_id, title, uploader, thumbnail, playlist_title, filename };
}
