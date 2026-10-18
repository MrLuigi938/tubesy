<script lang="ts">
	import { api, errorText } from '#lib/api.ts';
	import Icon from '#lib/components/Icon.svelte';
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

	let used = $state(0);
	let email = $state(session.user?.email ?? '');
	let sessions = $state<Sess[]>([]);
	let current = $state('');
	let next = $state('');
	let confirmPw = $state('');
	let busy = $state(false);

	const quota = $derived(session.user?.quota_bytes ?? null);
	const pct = $derived(quota ? Math.min(100, (used / quota) * 100) : 0);

	async function load() {
		const [acc, s] = await Promise.all([api.get<User & { used_bytes: number }>('/api/account'), api.get<Sess[]>('/api/account/sessions')]);
		used = acc.used_bytes;
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
			<input class="input" type="password" placeholder="Neues Passwort (mind. 10 Zeichen)" bind:value={next} autocomplete="new-password" minlength="10" required />
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
