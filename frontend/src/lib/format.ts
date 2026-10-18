export function bytes(n: number | null | undefined): string {
	if (n == null || !isFinite(n)) return '–';
	const units = ['B', 'KB', 'MB', 'GB', 'TB'];
	let i = 0;
	while (n >= 1024 && i < units.length - 1) {
		n /= 1024;
		i++;
	}
	return `${n.toLocaleString('de-DE', { maximumFractionDigits: i >= 3 ? 2 : i ? 1 : 0 })} ${units[i]}`;
}

export function duration(sec: number | null | undefined): string {
	if (sec == null || !isFinite(sec)) return '';
	sec = Math.round(sec);
	const h = Math.floor(sec / 3600);
	const m = Math.floor((sec % 3600) / 60);
	const s = sec % 60;
	const pad = (v: number) => String(v).padStart(2, '0');
	return h ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

export function eta(sec: number | null | undefined): string {
	if (sec == null || !isFinite(sec)) return '';
	if (sec < 60) return `${Math.round(sec)} s`;
	if (sec < 3600) return `${Math.round(sec / 60)} min`;
	return `${(sec / 3600).toLocaleString('de-DE', { maximumFractionDigits: 1 })} h`;
}

export function date(iso: string | null | undefined): string {
	if (!iso) return '–';
	return new Date(iso).toLocaleString('de-DE', { dateStyle: 'medium', timeStyle: 'short' });
}

export function relative(iso: string | null | undefined): string {
	if (!iso) return '–';
	const diff = (Date.now() - new Date(iso).getTime()) / 1000;
	const rtf = new Intl.RelativeTimeFormat('de', { numeric: 'auto' });
	if (diff < 60) return 'gerade eben';
	if (diff < 3600) return rtf.format(-Math.round(diff / 60), 'minute');
	if (diff < 86400) return rtf.format(-Math.round(diff / 3600), 'hour');
	if (diff < 86400 * 30) return rtf.format(-Math.round(diff / 86400), 'day');
	return date(iso);
}
