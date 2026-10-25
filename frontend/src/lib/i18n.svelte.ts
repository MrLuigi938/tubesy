// Translations for the web interface. German is the source language: the
// code calls t('German text') and gets the English version when English is
// selected. {name} placeholders are filled from the second argument.
import { en } from './en';

export type Lang = 'de' | 'en';
const KEY = 'tubesy-lang';

function initial(): Lang {
	try {
		const saved = localStorage.getItem(KEY);
		if (saved === 'de' || saved === 'en') return saved;
	} catch {
		/* private mode */
	}
	return (navigator.language || 'de').toLowerCase().startsWith('de') ? 'de' : 'en';
}

export const i18n = $state<{ lang: Lang }>({ lang: typeof navigator === 'undefined' ? 'de' : initial() });
if (typeof document !== 'undefined') document.documentElement.lang = i18n.lang;

export function setLang(lang: string) {
	if (lang !== 'de' && lang !== 'en') return;
	i18n.lang = lang;
	document.documentElement.lang = lang;
	try {
		localStorage.setItem(KEY, lang);
	} catch {
		/* private mode */
	}
}

// A text can carry a context after "|" when one German word needs two English
// ones ('Benutzer|Rolle' -> 'User'); the German output drops it.
export function t(text: string, vars?: Record<string, string | number>): string {
	let out = i18n.lang === 'en' ? (en[text] ?? text.split('|')[0]) : text.split('|')[0];
	if (vars) out = out.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
	return out;
}

// Server messages with values in them, matched to a dictionary entry with {placeholders}.
const PATTERNS: [RegExp, string, string[]][] = [
	[/^Mindestens (\d+) Zeichen$/, 'Mindestens {n} Zeichen', ['n']],
	[/^Das Passwort muss mindestens (\d+) Zeichen haben$/, 'Das Passwort muss mindestens {n} Zeichen haben', ['n']],
	[/^Höchstens (\d+) Einträge pro Auftrag$/, 'Höchstens {n} Einträge pro Auftrag', ['n']],
	[/^Zu viele Anmeldeversuche\. Bitte in (\d+) Minuten erneut versuchen\.$/, 'Zu viele Anmeldeversuche. Bitte in {n} Minuten erneut versuchen.', ['n']],
	[/^Unbekannte SponsorBlock-Kategorien: (.*)$/, 'Unbekannte SponsorBlock-Kategorien: {list}', ['list']],
	[/^Update fehlgeschlagen: ([\s\S]*)$/, 'Update fehlgeschlagen: {error}', ['error']],
	[/^Interner Fehler: ([\s\S]*)$/, 'Interner Fehler: {error}', ['error']],
	[/^yt-dlp beendet mit Code (-?\d+)$/, 'yt-dlp beendet mit Code {code}', ['code']],
	[/^Download Stream (\d+)$/, 'Download Stream {n}', ['n']],
	[
		/^Keine Schreibrechte auf den Download-Ordner \(Container läuft als UID (\d+), GID (\d+)\)\./,
		"Keine Schreibrechte auf den Download-Ordner (Container läuft als UID {uid}, GID {gid}). Auf der NAS den Ordner diesem Benutzer geben, z. B. 'chown -R {uid}:{gid} <ordner>', oder PUID/PGID anpassen.",
		['uid', 'gid']
	]
];

/** Translates a text that came from the server (error messages, download stages). */
export function tServer(text: string): string {
	if (i18n.lang !== 'en' || !text) return text;
	if (text in en) return en[text];
	for (const [re, key, names] of PATTERNS) {
		const m = text.match(re);
		if (m) return t(key, Object.fromEntries(names.map((n, i) => [n, m[i + 1]])));
	}
	return text;
}

/** Locale for dates and numbers. */
export const locale = () => (i18n.lang === 'en' ? 'en-GB' : 'de-DE');
