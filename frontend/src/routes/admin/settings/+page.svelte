<script lang="ts">
	import { i18n, locale, t } from '#lib/i18n.svelte.ts';
	import { api, errorText } from '#lib/api.ts';
	import { appInfo, channel, isRelease, REPO, refreshInfo, type UpdateInfo } from '#lib/appinfo.svelte.ts';
	import { copyText } from '#lib/clipboard.ts';
	import Icon from '#lib/components/Icon.svelte';
	import { bytes } from '#lib/format.ts';
	import { toast } from '#lib/toast.svelte.ts';
	import { onMount } from 'svelte';

	interface Settings {
		registration_mode: string;
		max_concurrent_downloads: number;
		max_concurrent_per_user: number;
		default_quota_gb: number | null;
		session_days: number;
		max_playlist_items: number;
		min_password_length: number;
		update_check: boolean;
	}
	interface System {
		version: string;
		update: UpdateInfo | null;
		update_checked_at: string | null;
		python: string;
		ytdlp_version: string;
		ffmpeg: boolean;
		deno: boolean;
		download_dir: string;
		download_dir_writable: boolean;
		disk_total: number;
		disk_free: number;
		users: number;
		downloads_by_status: Record<string, number>;
	}

	let s = $state<Settings | null>(null);
	let quota = $state('');
	let sys = $state<System | null>(null);
	let saving = $state(false);
	let updating = $state(false);

	onMount(async () => {
		s = await api.get<Settings>('/api/admin/settings');
		quota = s.default_quota_gb != null ? String(s.default_quota_gb) : '';
		sys = await api.get<System>('/api/admin/system');
	});

	async function save(e: SubmitEvent) {
		e.preventDefault();
		if (!s) return;
		saving = true;
		try {
			s = await api.put<Settings>('/api/admin/settings', {
				...s,
				default_quota_gb: quota === '' ? null : Number(quota),
				clear_default_quota: quota === ''
			});
			toast(t('Einstellungen gespeichert'));
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			saving = false;
		}
	}

	async function setUpdateCheck(e: Event) {
		if (!s) return;
		const on = (e.currentTarget as HTMLInputElement).checked;
		try {
			s = await api.put<Settings>('/api/admin/settings', { update_check: on });
			// The server checks in the background; give it a moment before asking again.
			setTimeout(async () => {
				sys = await api.get<System>('/api/admin/system');
				await refreshInfo();
			}, 2500);
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}

	const statusNames: Record<string, string> = {
		queued: 'wartend',
		downloading: 'lädt',
		processing: 'in Verarbeitung',
		completed: 'fertig',
		failed: 'fehlgeschlagen',
		canceled: 'abgebrochen'
	};

	// Guides in the repository, in the language of the interface.
	const docs = (page: string) => `${REPO}/blob/main/docs/${i18n.lang}/${page}.md`;

	const fmtDate = (d: string, time = false) =>
		new Date(d).toLocaleString(locale(), time ? { dateStyle: 'medium', timeStyle: 'short' } : { dateStyle: 'medium' });

	function infoText(): string {
		return [
			`Tubesy ${sys?.version || '?'}`,
			`yt-dlp: ${sys?.ytdlp_version || '?'}`,
			`Python: ${sys?.python || '?'} · ffmpeg: ${sys?.ffmpeg ? 'ja' : 'nein'} · Deno: ${sys?.deno ? 'ja' : 'nein'}`,
			`Browser: ${navigator.userAgent}`
		].join('\n');
	}
	// "Fehler melden" opens a new GitHub issue with the version details filled in.
	const issueLink = $derived(sys ? `${REPO}/issues/new?body=${encodeURIComponent('\n\n---\n' + infoText())}` : REPO);

	async function copyInfo() {
		if (await copyText(infoText())) toast(t('Kopiert'));
		else toast(t('Kopieren nicht möglich – bitte von Hand markieren.'), 'error');
	}

	async function updateYtdlp() {
		updating = true;
		try {
			const res = await api.post<{ ytdlp_version: string }>('/api/admin/ytdlp/update');
			if (sys) sys.ytdlp_version = res.ytdlp_version;
			toast(t('yt-dlp ist auf Version {v}', { v: res.ytdlp_version }));
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			updating = false;
		}
	}
</script>

<div class="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
	<form class="card p-5" onsubmit={save}>
		<h2 class="font-semibold">{t('Einstellungen')}</h2>
		{#if s}
			<div class="mt-4 grid gap-4 sm:grid-cols-2">
				<label><span class="label">{t('Gleichzeitige Downloads (gesamt)')}</span><input class="input" type="number" min="1" max="20" bind:value={s.max_concurrent_downloads} /></label>
				<label><span class="label">{t('Gleichzeitige Downloads pro Benutzer')}</span><input class="input" type="number" min="1" max="20" bind:value={s.max_concurrent_per_user} /><span class="hint">{t('Verhindert, dass eine große Playlist alle anderen blockiert.')}</span></label>
				<label><span class="label">{t('Max. Einträge pro Playlist')}</span><input class="input" type="number" min="1" max="5000" bind:value={s.max_playlist_items} /></label>
				<label><span class="label">{t('Standard-Kontingent neuer Benutzer (GB)')}</span><input class="input" type="number" min="0" step="0.5" bind:value={quota} placeholder={t('unbegrenzt')} /></label>
				<label><span class="label">{t('Anmeldung gültig (Tage)')}</span><input class="input" type="number" min="1" max="365" bind:value={s.session_days} /></label>
				<label><span class="label">{t('Mindestlänge Passwort (Benutzer)')}</span><input class="input" type="number" min="6" max="64" bind:value={s.min_password_length} /><span class="hint">{t('Gilt für normale Benutzer. Administratoren brauchen immer mindestens 6 Zeichen.')}</span></label>
			</div>
			<button class="btn-primary mt-5" disabled={saving}>{#if saving}<Icon name="loader" size={16} />{/if}{t('Speichern')}</button>
		{/if}
	</form>

	<div class="grid gap-6 self-start">
	<section id="info" class="card scroll-mt-20 p-5">
		<h2 class="font-semibold">{t('Info')}</h2>
		{#if sys && s}
			{@const update = sys.update ?? appInfo.update}
			<div class="mt-4 grid gap-2.5 rounded-lg border bg-surface-2 p-3.5 {update ? 'border-accent/55' : 'border-border'}">
				<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
					<span class="w-20 text-muted">{t('Installiert')}</span>
					<b class="font-semibold tabular-nums">{isRelease(sys.version) || sys.version.startsWith('edge') ? sys.version : t('Entwicklerversion')}</b>
					<span class="text-xs text-muted">{t(channel(sys.version))}</span>
				</div>
				{#if update}
					<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
						<span class="w-20 text-muted">{t('Neu')}</span>
						<b class="font-semibold text-accent tabular-nums">{update.version}</b>
						{#if update.published}<span class="text-xs text-muted">{t('seit {date}', { date: fmtDate(update.published) })}</span>{/if}
					</div>
					<div class="flex flex-wrap gap-2">
						<a class="btn-primary" href={update.url} target="_blank" rel="noopener noreferrer">✨ {t('Was ist neu?')}</a>
						<a class="btn-secondary" href={docs('updating')} target="_blank" rel="noopener noreferrer">{t('So aktualisierst du')}</a>
					</div>
				{:else if s.update_check && isRelease(sys.version)}
					<p class="text-sm text-ok">
						✓ {t('Du hast die neueste Version.')}{#if sys.update_checked_at} <span class="text-muted">{t('Zuletzt geprüft: {date}', { date: fmtDate(sys.update_checked_at, true) })}</span>{/if}
					</p>
				{:else if !isRelease(sys.version)}
					<p class="text-xs text-muted">{t('Entwicklungs- und Edge-Builds suchen nicht nach Updates.')}</p>
				{/if}
			</div>
			<label class="mt-4 flex items-start gap-2 text-sm">
				<input type="checkbox" class="mt-0.5" checked={s.update_check} onchange={setUpdateCheck} />
				<span>{t('Auf neue Tubesy-Versionen hinweisen')}<span class="hint">{t('Der Server fragt zweimal am Tag bei GitHub nach der neuesten Version und zeigt sie unten in der Fußzeile an. Es wird nichts automatisch installiert.')}</span></span>
			</label>
			<div class="mt-4 flex flex-wrap gap-2">
				<a class="btn-secondary h-8 px-2.5 text-xs" href={REPO} target="_blank" rel="noopener noreferrer"><Icon name="external" size={14} />GitHub</a>
				<a class="btn-secondary h-8 px-2.5 text-xs" href={docs('usage')} target="_blank" rel="noopener noreferrer">📖 {t('Anleitung')}</a>
				<a class="btn-secondary h-8 px-2.5 text-xs" href={issueLink} target="_blank" rel="noopener noreferrer">🐞 {t('Fehler melden')}</a>
				<button type="button" class="btn-secondary h-8 px-2.5 text-xs" onclick={copyInfo}><Icon name="copy" size={14} />{t('Infos kopieren')}</button>
			</div>
		{:else}
			<div class="flex justify-center py-8 text-muted"><Icon name="loader" /></div>
		{/if}
	</section>

	<section class="card p-5">
		<h2 class="font-semibold">System</h2>
		{#if sys}
			{@const usedPct = ((sys.disk_total - sys.disk_free) / sys.disk_total) * 100}
			<dl class="mt-4 space-y-3 text-sm">
				<div class="flex items-center justify-between gap-2">
					<dt class="text-muted">yt-dlp</dt>
					<dd class="flex items-center gap-2 font-mono text-xs">
						{sys.ytdlp_version}
						<button type="button" class="btn-secondary h-7 px-2 py-0.5 text-xs" disabled={updating} onclick={updateYtdlp}>
							{#if updating}<Icon name="loader" size={12} />{:else}<Icon name="retry" size={12} />{/if}{t('Aktualisieren')}
						</button>
					</dd>
				</div>
				<div class="flex justify-between"><dt class="text-muted">ffmpeg</dt><dd class={sys.ffmpeg ? 'text-ok' : 'text-danger'}>{sys.ffmpeg ? t('vorhanden') : t('fehlt')}</dd></div>
				<div class="flex justify-between"><dt class="text-muted">{t('Deno (für YouTube)')}</dt><dd class={sys.deno ? 'text-ok' : 'text-warn'}>{sys.deno ? t('vorhanden') : t('fehlt')}</dd></div>
				<div class="flex justify-between gap-4"><dt class="text-muted">{t('Download-Ordner')}</dt><dd class="truncate font-mono text-xs">{sys.download_dir}</dd></div>
				<div class="flex justify-between"><dt class="text-muted">{t('Schreibrechte')}</dt><dd class={sys.download_dir_writable ? 'text-ok' : 'text-danger'}>{sys.download_dir_writable ? t('vorhanden') : t('fehlen – PUID/PGID bzw. Ordnerrechte prüfen')}</dd></div>
				<div>
					<div class="flex justify-between"><dt class="text-muted">{t('Speicherplatz')}</dt><dd class="tabular-nums">{t('{free} frei von {total}', { free: bytes(sys.disk_free), total: bytes(sys.disk_total) })}</dd></div>
					<div class="mt-2 h-2 overflow-hidden rounded-full bg-surface-2"><div class="h-full rounded-full {usedPct > 90 ? 'bg-danger' : 'bg-info'}" style="width: {usedPct}%"></div></div>
				</div>
				<div class="flex justify-between"><dt class="text-muted">{t('Benutzer')}</dt><dd>{sys.users}</dd></div>
				<div class="flex justify-between"><dt class="text-muted">{t('Downloads')}</dt><dd class="text-right">{Object.entries(sys.downloads_by_status).map(([k, v]) => `${v} ${t(statusNames[k] ?? k)}`).join(' · ') || '–'}</dd></div>
			</dl>
		{:else}
			<div class="flex justify-center py-8 text-muted"><Icon name="loader" /></div>
		{/if}
	</section>
	</div>
</div>
