<script lang="ts">
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
	let tokenName = $state('HeimDeck');
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
		const [acc, s, t] = await Promise.all([
			api.get<User & { used_bytes: number }>('/api/account'),
			api.get<Sess[]>('/api/account/sessions'),
			api.get<Token[]>('/api/account/tokens')
		]);
		tokens = t;
		used = acc.used_bytes;
		userMin = (await api.get<{ min_password_length: number }>('/api/status')).min_password_length;
		sessions = s;
	}
	onMount(load);

	function device(ua: string | null) {
		if (!ua) return 'Unbekanntes Gerät';
		const browser = /Firefox/.test(ua) ? 'Firefox' : /Edg\//.test(ua) ? 'Edge' : /Chrome/.test(ua) ? 'Chrome' : /Safari/.test(ua) ? 'Safari' : 'Browser';
		const os = /Android/.test(ua) ? 'Android' : /iPhone|iPad/.test(ua) ? 'iOS' : /Windows/.test(ua) ? 'Windows' : /Mac OS/.test(ua) ? 'macOS' : /Linux/.test(ua) ? 'Linux' : '';
		return os ? `${browser} auf ${os}` : browser;
	}

	async function saveProfile(e: SubmitEvent) {
		e.preventDefault();
		try {
			session.user = await api.patch<User>('/api/account', { email: email || null, default_preset_id: session.user?.default_preset_id ?? null });
			toast('Profil gespeichert');
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}

	async function changePassword(e: SubmitEvent) {
		e.preventDefault();
		if (next !== confirmPw) return toast('Die neuen Passwörter stimmen nicht überein', 'error');
		busy = true;
		try {
			await api.post('/api/account/password', { current_password: current, new_password: next });
			current = next = confirmPw = '';
			toast('Passwort geändert. Andere Sitzungen wurden abgemeldet.');
			await load();
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			busy = false;
		}
	}

	function openToken() {
		tokenName = 'HeimDeck';
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
		if (await copyText(newKey)) toast('Schlüssel kopiert');
		else toast('Kopieren nicht möglich, bitte manuell markieren', 'info');
	}

	async function deleteToken(t: Token) {
		if (!confirm(`API-Schlüssel „${t.name}“ widerrufen? Anwendungen, die ihn nutzen, verlieren den Zugriff.`)) return;
		try {
			await api.del(`/api/account/tokens/${t.id}`);
			tokens = tokens.filter((x) => x.id !== t.id);
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

<h1 class="text-2xl font-semibold tracking-tight">Konto</h1>
<p class="mt-1 text-sm text-muted">Angemeldet als <b class="text-text">{session.user?.username}</b>{session.user?.role === 'admin' ? ' (Administrator)' : ''}.</p>

<div class="mt-6 grid gap-6 lg:grid-cols-2">
	<section class="card p-5">
		<h2 class="font-semibold">Speicher</h2>
		<p class="mt-3 text-2xl font-semibold tabular-nums">{bytes(used)}</p>
		<p class="text-sm text-muted">{quota ? `von ${bytes(quota)} belegt` : 'belegt · kein Limit'}</p>
		{#if quota}
			<div class="mt-3 h-2 overflow-hidden rounded-full bg-surface-2">
				<div class="h-full rounded-full {pct > 90 ? 'bg-danger' : pct > 70 ? 'bg-warn' : 'bg-ok'}" style="width: {pct}%"></div>
			</div>
		{/if}
		<form class="mt-6 space-y-3" onsubmit={saveProfile}>
			<label class="block">
				<span class="label">E-Mail</span>
				<input class="input" type="email" bind:value={email} placeholder="optional" />
			</label>
			<button class="btn-secondary">Speichern</button>
		</form>
	</section>

	<section class="card p-5">
		<h2 class="font-semibold">Passwort ändern</h2>
		<form class="mt-4 space-y-3" onsubmit={changePassword}>
			<input class="input" type="password" placeholder="Aktuelles Passwort" bind:value={current} autocomplete="current-password" required />
			<input class="input" type="password" placeholder="Neues Passwort (mind. {minLength} Zeichen)" bind:value={next} autocomplete="new-password" minlength={minLength} required />
			<input class="input" type="password" placeholder="Neues Passwort wiederholen" bind:value={confirmPw} autocomplete="new-password" required />
			<button class="btn-primary" disabled={busy}>{#if busy}<Icon name="loader" size={16} />{/if}Passwort ändern</button>
		</form>
	</section>
</div>

<section class="card mt-6">
	<div class="px-5 pt-5 pb-3">
		<h2 class="font-semibold">Aktive Sitzungen</h2>
		<p class="mt-1 text-sm text-muted">Geräte, auf denen du angemeldet bist. Unbekannte Sitzungen solltest du beenden und dein Passwort ändern.</p>
	</div>
	<ul>
		{#each sessions as s (s.id)}
			<li class="flex items-center gap-3 border-t border-border px-5 py-3">
				<Icon name="monitor" class="text-muted" />
				<div class="min-w-0 flex-1">
					<p class="text-sm font-medium">
						{device(s.user_agent)}
						{#if s.current}<span class="badge ml-1 bg-ok-soft text-ok">Diese Sitzung</span>{/if}
					</p>
					<p class="text-xs text-muted">{s.ip ?? '?'} · zuletzt aktiv {relative(s.last_seen_at)} · seit {date(s.created_at)}</p>
				</div>
				{#if !s.current}<button class="btn-ghost h-8 px-2.5 py-1 text-xs" onclick={() => revoke(s)}>Beenden</button>{/if}
			</li>
		{/each}
	</ul>
</section>

<section class="card mt-6">
	<div class="flex flex-wrap items-start gap-3 px-5 pt-5 pb-3">
		<div class="min-w-0 flex-1">
			<h2 class="font-semibold">API-Schlüssel</h2>
			<p class="mt-1 text-sm text-muted">Für Dashboards wie HeimDeck, Skripte oder Kurzbefehle. Der Schlüssel handelt mit deinen Rechten.</p>
		</div>
		<button class="btn-secondary" onclick={openToken}><Icon name="plus" size={16} />Neuer Schlüssel</button>
	</div>
	{#if !tokens.length}
		<p class="border-t border-border px-5 py-4 text-sm text-muted">Noch keine API-Schlüssel erstellt.</p>
	{:else}
		<ul>
			{#each tokens as t (t.id)}
				<li class="flex items-center gap-3 border-t border-border px-5 py-3">
					<Icon name="link" class="text-muted" />
					<div class="min-w-0 flex-1">
						<p class="text-sm font-medium">
							{t.name}
							<span class="badge ml-1 {t.scope === 'full' ? 'bg-warn-soft text-warn' : 'bg-surface-2 text-muted'}">{t.scope === 'full' ? 'Lesen & Downloads' : 'Nur lesen'}</span>
						</p>
						<p class="text-xs text-muted"><code>{t.prefix}…</code> · erstellt {date(t.created_at)} · {t.last_used_at ? `zuletzt genutzt ${relative(t.last_used_at)}` : 'noch nie genutzt'}</p>
					</div>
					<button class="btn-ghost h-8 px-2.5 py-1 text-xs" onclick={() => deleteToken(t)}>Widerrufen</button>
				</li>
			{/each}
		</ul>
	{/if}
	<details class="border-t border-border px-5 py-3 text-sm">
		<summary class="cursor-pointer font-medium text-muted hover:text-text">So verwendest du die API</summary>
		<div class="mt-3 space-y-2 text-muted">
			<p>Schlüssel im Header mitschicken: <code class="text-text">X-Api-Key: tsy_…</code> (oder <code class="text-text">Authorization: Bearer tsy_…</code>).</p>
			<ul class="list-disc space-y-1 pl-5">
				<li><code class="text-text">GET /api/v1/stats</code> – Zähler, Speicher, Tempo (Admins: zusätzlich ganze Instanz)</li>
				<li><code class="text-text">GET /api/v1/queue</code> – laufende und wartende Downloads</li>
				<li><code class="text-text">POST /api/v1/download</code> – <code class="text-text">{'{"url": "…", "preset": "Audio (MP3)"}'}</code> in die Warteschlange (nur mit „Lesen & Downloads“)</li>
			</ul>
			<p>Alle Endpunkte: <a class="text-accent hover:underline" href="/api/docs" target="_blank" rel="noopener">API-Dokumentation</a></p>
		</div>
	</details>
</section>

<Modal bind:open={tokenOpen} title="Neuer API-Schlüssel">
	{#if newKey}
		<div class="rounded-lg border border-ok/40 bg-ok-soft p-3">
			<p class="text-sm font-medium text-ok">Schlüssel erstellt. Er wird nur jetzt angezeigt:</p>
			<div class="mt-2 flex gap-2">
				<input class="input font-mono text-xs" readonly value={newKey} onfocus={(e) => e.currentTarget.select()} />
				<button class="btn-secondary" onclick={copyKey} title="Kopieren"><Icon name="copy" size={16} /></button>
			</div>
		</div>
	{:else}
		<div class="space-y-4">
			<label class="block"><span class="label">Name</span><input class="input" bind:value={tokenName} maxlength="64" placeholder="z. B. HeimDeck" /></label>
			<fieldset class="space-y-2">
				<legend class="label">Berechtigung</legend>
				{#each [['read', 'Nur lesen', 'Für Dashboards: Statistiken und Warteschlange anzeigen.'], ['full', 'Lesen & Downloads', 'Darf zusätzlich Downloads starten, abbrechen und löschen.']] as [value, label, hint] (value)}
					<label class="flex cursor-pointer gap-3 rounded-lg border p-3 {tokenScope === value ? 'border-accent bg-accent-soft/40' : 'border-border'}">
						<input type="radio" name="scope" checked={tokenScope === value} onchange={() => (tokenScope = value as 'read' | 'full')} class="mt-0.5" />
						<span><span class="block text-sm font-medium">{label}</span><span class="text-xs text-muted">{hint}</span></span>
					</label>
				{/each}
			</fieldset>
		</div>
	{/if}
	{#snippet footer()}
		{#if newKey}
			<button class="btn-primary" onclick={() => (tokenOpen = false)}>Fertig</button>
		{:else}
			<button class="btn-ghost" onclick={() => (tokenOpen = false)}>Abbrechen</button>
			<button class="btn-primary" disabled={!tokenName.trim()} onclick={createToken}>Erstellen</button>
		{/if}
	{/snippet}
</Modal>
