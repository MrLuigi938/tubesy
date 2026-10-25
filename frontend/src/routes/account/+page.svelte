<script lang="ts">
	import LangSwitch from '#lib/components/LangSwitch.svelte';
	import { t } from '#lib/i18n.svelte.ts';
	import { api, errorText } from '#lib/api.ts';
	import { copyText } from '#lib/clipboard.ts';
	import Icon from '#lib/components/Icon.svelte';
	import Modal from '#lib/components/Modal.svelte';
	import { bytes, date, relative } from '#lib/format.ts';
	import { session } from '#lib/session.svelte.ts';
	import { toast } from '#lib/toast.svelte.ts';
	import type { User } from '#lib/types.ts';
	import { onMount } from 'svelte';

	interface Sess {
		id: number;
		ip: string | null;
		user_agent: string | null;
		current: boolean;
		created_at: string;
		last_seen_at: string;
	}

	interface Token {
		id: number;
		name: string;
		prefix: string;
		scope: 'read' | 'full';
		created_at: string;
		last_used_at: string | null;
	}

	let tokens = $state<Token[]>([]);
	let tokenOpen = $state(false);
	let tokenName = $state('Heimdeck');
	let tokenScope = $state<'read' | 'full'>('read');
	let newKey = $state('');
	let used = $state(0);
	let email = $state(session.user?.email ?? '');
	let sessions = $state<Sess[]>([]);
	let current = $state('');
	let next = $state('');
	let confirmPw = $state('');
	let busy = $state(false);
	let userMin = $state(6);
	const minLength = $derived(session.user?.role === 'admin' ? 6 : userMin);

	const quota = $derived(session.user?.quota_bytes ?? null);
	const pct = $derived(quota ? Math.min(100, (used / quota) * 100) : 0);

	async function load() {
		const [acc, s, tk] = await Promise.all([
			api.get<User & { used_bytes: number }>('/api/account'),
			api.get<Sess[]>('/api/account/sessions'),
			api.get<Token[]>('/api/account/tokens')
		]);
		tokens = tk;
		used = acc.used_bytes;
		userMin = (await api.get<{ min_password_length: number }>('/api/status')).min_password_length;
		sessions = s;
	}
	onMount(load);

	function device(ua: string | null) {
		if (!ua) return t('Unbekanntes Gerät');
		const browser = /Firefox/.test(ua) ? 'Firefox' : /Edg\//.test(ua) ? 'Edge' : /Chrome/.test(ua) ? 'Chrome' : /Safari/.test(ua) ? 'Safari' : 'Browser';
		const os = /Android/.test(ua) ? 'Android' : /iPhone|iPad/.test(ua) ? 'iOS' : /Windows/.test(ua) ? 'Windows' : /Mac OS/.test(ua) ? 'macOS' : /Linux/.test(ua) ? 'Linux' : '';
		return os ? t('{browser} auf {os}', { browser, os }) : browser;
	}

	async function saveProfile(e: SubmitEvent) {
		e.preventDefault();
		try {
			session.user = await api.patch<User>('/api/account', { email: email || null, default_preset_id: session.user?.default_preset_id ?? null });
			toast(t('Profil gespeichert'));
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}

	async function changePassword(e: SubmitEvent) {
		e.preventDefault();
		if (next !== confirmPw) return toast(t('Die neuen Passwörter stimmen nicht überein'), 'error');
		busy = true;
		try {
			await api.post('/api/account/password', { current_password: current, new_password: next });
			current = next = confirmPw = '';
			toast(t('Passwort geändert. Andere Sitzungen wurden abgemeldet.'));
			await load();
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			busy = false;
		}
	}

	function openToken() {
		tokenName = 'Heimdeck';
		tokenScope = 'read';
		newKey = '';
		tokenOpen = true;
	}

	async function createToken() {
		try {
			const res = await api.post<Token & { key: string }>('/api/account/tokens', { name: tokenName, scope: tokenScope });
			newKey = res.key;
			tokens = [res, ...tokens];
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}

	async function copyKey() {
		if (await copyText(newKey)) toast(t('Schlüssel kopiert'));
		else toast(t('Kopieren nicht möglich, bitte manuell markieren'), 'info');
	}

	async function deleteToken(tk: Token) {
		if (!confirm(t('API-Schlüssel „{name}“ widerrufen? Anwendungen, die ihn nutzen, verlieren den Zugriff.', { name: tk.name }))) return;
		try {
			await api.del(`/api/account/tokens/${tk.id}`);
			tokens = tokens.filter((x) => x.id !== tk.id);
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}

	async function revoke(s: Sess) {
		try {
			await api.del(`/api/account/sessions/${s.id}`);
			sessions = sessions.filter((x) => x.id !== s.id);
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}
</script>

<div class="flex flex-wrap items-end gap-4">
	<div class="flex-1">
		<h1 class="text-2xl font-semibold tracking-tight">{t('Konto')}</h1>
		<p class="mt-1 text-sm text-muted">{t('Angemeldet als')} <b class="text-text">{session.user?.username}</b>{session.user?.role === 'admin' ? ` (${t('Administrator')})` : ''}.</p>
	</div>
	<div class="flex items-center gap-2 text-sm text-muted">{t('Sprache')} <LangSwitch /></div>
</div>

<div class="mt-6 grid gap-6 lg:grid-cols-2">
	<section class="card p-5">
		<h2 class="font-semibold">{t('Speicher')}</h2>
		<p class="mt-3 text-2xl font-semibold tabular-nums">{bytes(used)}</p>
		<p class="text-sm text-muted">{quota ? t('von {quota} belegt', { quota: bytes(quota) }) : t('belegt · kein Limit')}</p>
		{#if quota}
			<div class="mt-3 h-2 overflow-hidden rounded-full bg-surface-2">
				<div class="h-full rounded-full {pct > 90 ? 'bg-danger' : pct > 70 ? 'bg-warn' : 'bg-ok'}" style="width: {pct}%"></div>
			</div>
		{/if}
		<form class="mt-6 space-y-3" onsubmit={saveProfile}>
			<label class="block">
				<span class="label">{t('E-Mail')}</span>
				<input class="input" type="email" bind:value={email} placeholder={t('optional')} />
			</label>
			<button class="btn-secondary">{t('Speichern')}</button>
		</form>
	</section>

	<section class="card p-5">
		<h2 class="font-semibold">{t('Passwort ändern')}</h2>
		<form class="mt-4 space-y-3" onsubmit={changePassword}>
			<input class="input" type="password" placeholder={t('Aktuelles Passwort')} bind:value={current} autocomplete="current-password" required />
			<input class="input" type="password" placeholder={t('Neues Passwort (mind. {n} Zeichen)', { n: minLength })} bind:value={next} autocomplete="new-password" minlength={minLength} required />
			<input class="input" type="password" placeholder={t('Neues Passwort wiederholen')} bind:value={confirmPw} autocomplete="new-password" required />
			<button class="btn-primary" disabled={busy}>{#if busy}<Icon name="loader" size={16} />{/if}{t('Passwort ändern')}</button>
		</form>
	</section>
</div>

<section class="card mt-6">
	<div class="px-5 pt-5 pb-3">
		<h2 class="font-semibold">{t('Aktive Sitzungen')}</h2>
		<p class="mt-1 text-sm text-muted">{t('Geräte, auf denen du angemeldet bist. Unbekannte Sitzungen solltest du beenden und dein Passwort ändern.')}</p>
	</div>
	<ul>
		{#each sessions as s (s.id)}
			<li class="flex items-center gap-3 border-t border-border px-5 py-3">
				<Icon name="monitor" class="text-muted" />
				<div class="min-w-0 flex-1">
					<p class="text-sm font-medium">
						{device(s.user_agent)}
						{#if s.current}<span class="badge ml-1 bg-ok-soft text-ok">{t('Diese Sitzung')}</span>{/if}
					</p>
					<p class="text-xs text-muted">{s.ip ?? '?'} · {t('zuletzt aktiv {when}', { when: relative(s.last_seen_at) })} · {t('seit {date}', { date: date(s.created_at) })}</p>
				</div>
				{#if !s.current}<button class="btn-ghost h-8 px-2.5 py-1 text-xs" onclick={() => revoke(s)}>{t('Beenden')}</button>{/if}
			</li>
		{/each}
	</ul>
</section>

<section class="card mt-6">
	<div class="flex flex-wrap items-start gap-3 px-5 pt-5 pb-3">
		<div class="min-w-0 flex-1">
			<h2 class="font-semibold">{t('API-Schlüssel')}</h2>
			<p class="mt-1 text-sm text-muted">{t('Für Dashboards wie Heimdeck, Skripte oder Kurzbefehle. Der Schlüssel handelt mit deinen Rechten.')}</p>
		</div>
		<button class="btn-secondary" onclick={openToken}><Icon name="plus" size={16} />{t('Neuer Schlüssel')}</button>
	</div>
	{#if !tokens.length}
		<p class="border-t border-border px-5 py-4 text-sm text-muted">{t('Noch keine API-Schlüssel erstellt.')}</p>
	{:else}
		<ul>
			{#each tokens as tk (tk.id)}
				<li class="flex items-center gap-3 border-t border-border px-5 py-3">
					<Icon name="link" class="text-muted" />
					<div class="min-w-0 flex-1">
						<p class="text-sm font-medium">
							{tk.name}
							<span class="badge ml-1 {tk.scope === 'full' ? 'bg-warn-soft text-warn' : 'bg-surface-2 text-muted'}">{tk.scope === 'full' ? t('Lesen & Downloads') : t('Nur lesen')}</span>
						</p>
						<p class="text-xs text-muted"><code>{tk.prefix}…</code> · {t('erstellt {date}', { date: date(tk.created_at) })} · {tk.last_used_at ? t('zuletzt genutzt {when}', { when: relative(tk.last_used_at) }) : t('noch nie genutzt')}</p>
					</div>
					<button class="btn-ghost h-8 px-2.5 py-1 text-xs" onclick={() => deleteToken(tk)}>{t('Widerrufen')}</button>
				</li>
			{/each}
		</ul>
	{/if}
	<details class="border-t border-border px-5 py-3 text-sm">
		<summary class="cursor-pointer font-medium text-muted hover:text-text">{t('So verwendest du die API')}</summary>
		<div class="mt-3 space-y-2 text-muted">
			<p>{t('Schlüssel im Header mitschicken:')} <code class="text-text">X-Api-Key: tsy_…</code> ({t('oder')} <code class="text-text">Authorization: Bearer tsy_…</code>).</p>
			<ul class="list-disc space-y-1 pl-5">
				<li><code class="text-text">GET /api/v1/stats</code> – {t('Zähler, Speicher, Tempo (Admins: zusätzlich ganze Instanz)')}</li>
				<li><code class="text-text">GET /api/v1/queue</code> – {t('laufende und wartende Downloads')}</li>
				<li><code class="text-text">POST /api/v1/download</code> – <code class="text-text">{'{"url": "…", "preset": "Audio (MP3)"}'}</code> {t('in die Warteschlange (nur mit „Lesen & Downloads“)')}</li>
			</ul>
			<p>{t('Alle Endpunkte:')} <a class="text-accent hover:underline" href="/api/docs" target="_blank" rel="noopener">{t('API-Dokumentation')}</a></p>
		</div>
	</details>
</section>

<Modal bind:open={tokenOpen} title={t('Neuer API-Schlüssel')}>
	{#if newKey}
		<div class="rounded-lg border border-ok/40 bg-ok-soft p-3">
			<p class="text-sm font-medium text-ok">{t('Schlüssel erstellt. Er wird nur jetzt angezeigt:')}</p>
			<div class="mt-2 flex gap-2">
				<input class="input font-mono text-xs" readonly value={newKey} onfocus={(e) => e.currentTarget.select()} />
				<button class="btn-secondary" onclick={copyKey} title={t('Kopieren')}><Icon name="copy" size={16} /></button>
			</div>
		</div>
	{:else}
		<div class="space-y-4">
			<label class="block"><span class="label">{t('Name')}</span><input class="input" bind:value={tokenName} maxlength="64" placeholder={t('z. B. Heimdeck')} /></label>
			<fieldset class="space-y-2">
				<legend class="label">{t('Berechtigung')}</legend>
				{#each [['read', 'Nur lesen', 'Für Dashboards: Statistiken und Warteschlange anzeigen.'], ['full', 'Lesen & Downloads', 'Darf zusätzlich Downloads starten, abbrechen und löschen.']] as [value, label, hint] (value)}
					<label class="flex cursor-pointer gap-3 rounded-lg border p-3 {tokenScope === value ? 'border-accent bg-accent-soft/40' : 'border-border'}">
						<input type="radio" name="scope" checked={tokenScope === value} onchange={() => (tokenScope = value as 'read' | 'full')} class="mt-0.5" />
						<span><span class="block text-sm font-medium">{t(label)}</span><span class="text-xs text-muted">{t(hint)}</span></span>
					</label>
				{/each}
			</fieldset>
		</div>
	{/if}
	{#snippet footer()}
		{#if newKey}
			<button class="btn-primary" onclick={() => (tokenOpen = false)}>{t('Fertig')}</button>
		{:else}
			<button class="btn-ghost" onclick={() => (tokenOpen = false)}>{t('Abbrechen')}</button>
			<button class="btn-primary" disabled={!tokenName.trim()} onclick={createToken}>{t('Erstellen')}</button>
		{/if}
	{/snippet}
</Modal>
