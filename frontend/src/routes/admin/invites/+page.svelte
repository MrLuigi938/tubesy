<script lang="ts">
	import { api, errorText } from '#lib/api.ts';
	import Icon from '#lib/components/Icon.svelte';
	import { date } from '#lib/format.ts';
	import { toast } from '#lib/toast.svelte.ts';
	import { onMount } from 'svelte';

	interface Invite {
		id: number;
		note: string | null;
		role: string;
		max_uses: number;
		uses: number;
		expires_at: string | null;
		created_at: string;
	}

	let invites = $state<Invite[]>([]);
	let mode = $state('invite');
	let form = $state({ note: '', role: 'user', max_uses: 1, expires_days: '7' });
	let link = $state('');
	let busy = $state(false);

	async function load() {
		const [i, s] = await Promise.all([api.get<Invite[]>('/api/admin/invites'), api.get<{ registration_mode: string }>('/api/admin/settings')]);
		invites = i;
		mode = s.registration_mode;
	}
	onMount(load);

	function expired(i: Invite) {
		return i.uses >= i.max_uses || (i.expires_at != null && new Date(i.expires_at) < new Date());
	}

	async function create(e: SubmitEvent) {
		e.preventDefault();
		busy = true;
		try {
			const res = await api.post<Invite & { token: string }>('/api/admin/invites', {
				note: form.note || null,
				role: form.role,
				max_uses: Number(form.max_uses),
				expires_days: form.expires_days ? Number(form.expires_days) : null
			});
			link = `${location.origin}/register?invite=${res.token}`;
			form.note = '';
			await load();
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			busy = false;
		}
	}

	async function copy() {
		try {
			await navigator.clipboard.writeText(link);
			toast('Link kopiert');
		} catch {
			toast('Kopieren nicht möglich, bitte manuell markieren', 'info');
		}
	}

	async function remove(i: Invite) {
		try {
			await api.del(`/api/admin/invites/${i.id}`);
			await load();
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}

	async function setMode(value: string) {
		try {
			await api.put('/api/admin/settings', { registration_mode: value });
			mode = value;
			toast('Registrierungsmodus gespeichert');
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}
</script>

<div class="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
	<div class="space-y-6">
		<section class="card p-5">
			<h2 class="font-semibold">Registrierung</h2>
			<div class="mt-3 space-y-2">
				{#each [['closed', 'Geschlossen', 'Nur Administratoren legen Konten an.'], ['invite', 'Nur mit Einladung', 'Empfohlen für öffentlich erreichbare Instanzen.'], ['open', 'Offen', 'Jeder mit dem Link kann sich registrieren.']] as [value, label, hint] (value)}
					<label class="flex cursor-pointer gap-3 rounded-lg border p-3 {mode === value ? 'border-accent bg-accent-soft/40' : 'border-border'}">
						<input type="radio" name="mode" checked={mode === value} onchange={() => setMode(value)} class="mt-0.5 accent-[var(--accent)]" />
						<span><span class="block text-sm font-medium">{label}</span><span class="text-xs text-muted">{hint}</span></span>
					</label>
				{/each}
			</div>
		</section>

		<section class="card p-5">
			<h2 class="font-semibold">Neue Einladung</h2>
			<form class="mt-4 space-y-3" onsubmit={create}>
				<input class="input" bind:value={form.note} placeholder="Notiz, z. B. „Für Max“" maxlength="255" />
				<div class="grid grid-cols-3 gap-2">
					<label><span class="label text-xs">Rolle</span><select class="input" bind:value={form.role}><option value="user">Benutzer</option><option value="admin">Admin</option></select></label>
					<label><span class="label text-xs">Nutzungen</span><input class="input" type="number" min="1" max="1000" bind:value={form.max_uses} /></label>
					<label><span class="label text-xs">Gültig</span><select class="input" bind:value={form.expires_days}><option value="1">1 Tag</option><option value="7">7 Tage</option><option value="30">30 Tage</option><option value="">Unbegrenzt</option></select></label>
				</div>
				<button class="btn-primary w-full" disabled={busy}><Icon name="link" size={16} />Einladungslink erzeugen</button>
			</form>
			{#if link}
				<div class="mt-4 rounded-lg border border-ok/40 bg-ok-soft p-3">
					<p class="text-xs font-medium text-ok">Link wird nur jetzt angezeigt:</p>
					<div class="mt-2 flex gap-2">
						<input class="input font-mono text-xs" readonly value={link} onfocus={(e) => e.currentTarget.select()} />
						<button class="btn-secondary" onclick={copy} title="Kopieren"><Icon name="copy" size={16} /></button>
					</div>
				</div>
			{/if}
		</section>
	</div>

	<section class="card self-start">
		<h2 class="px-5 pt-5 pb-3 font-semibold">Einladungen</h2>
		{#if !invites.length}
			<p class="border-t border-border px-5 py-6 text-sm text-muted">Noch keine Einladungen erstellt.</p>
		{:else}
			<ul>
				{#each invites as i (i.id)}
					<li class="flex items-center gap-3 border-t border-border px-5 py-3 {expired(i) ? 'opacity-55' : ''}">
						<div class="min-w-0 flex-1">
							<p class="truncate text-sm font-medium">{i.note || 'Ohne Notiz'} {#if i.role === 'admin'}<span class="badge bg-accent-soft text-accent">Admin</span>{/if}</p>
							<p class="text-xs text-muted">
								{i.uses}/{i.max_uses} genutzt · {i.expires_at ? `gültig bis ${date(i.expires_at)}` : 'unbegrenzt gültig'}
								{#if expired(i)} · <span class="text-danger">abgelaufen</span>{/if}
							</p>
						</div>
						<button class="btn-icon hover:text-danger" title="Widerrufen" onclick={() => remove(i)}><Icon name="trash" size={16} /></button>
					</li>
				{/each}
			</ul>
		{/if}
	</section>
</div>
