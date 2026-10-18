<script lang="ts">
	import { api, errorText } from '#lib/api.ts';
	import Icon from '#lib/components/Icon.svelte';
	import Modal from '#lib/components/Modal.svelte';
	import { bytes, relative } from '#lib/format.ts';
	import { session } from '#lib/session.svelte.ts';
	import { toast } from '#lib/toast.svelte.ts';
	import type { User } from '#lib/types.ts';
	import { onMount } from 'svelte';

	type Row = User & { downloads: number; used_bytes: number };
	const GB = 1024 ** 3;

	let users = $state<Row[]>([]);
	let createOpen = $state(false);
	let form = $state({ username: '', password: '', email: '', role: 'user', quota_gb: '' });
	let editOpen = $state(false);
	let edit = $state<{ user: Row; role: string; is_active: boolean; quota_gb: string; password: string; email: string } | null>(null);
	let deleteOpen = $state(false);
	let deleting = $state<Row | null>(null);
	let deleteFiles = $state(false);
	let busy = $state(false);
	let userMin = $state(6);
	const createMin = $derived(form.role === 'admin' ? 6 : userMin);

	const load = async () => (users = await api.get<Row[]>('/api/admin/users'));
	onMount(async () => {
		await load();
		userMin = (await api.get<{ min_password_length: number }>('/api/status')).min_password_length;
	});

	async function act(fn: () => Promise<unknown>, ok: string) {
		busy = true;
		try {
			await fn();
			toast(ok);
			await load();
			return true;
		} catch (err) {
			toast(errorText(err), 'error');
			return false;
		} finally {
			busy = false;
		}
	}

	async function createUser(e: SubmitEvent) {
		e.preventDefault();
		const body = { ...form, email: form.email || null, quota_gb: form.quota_gb ? Number(form.quota_gb) : null };
		if (await act(() => api.post('/api/admin/users', body), `Benutzer ${form.username} angelegt`)) {
			createOpen = false;
			form = { username: '', password: '', email: '', role: 'user', quota_gb: '' };
		}
	}

	function openEdit(u: Row) {
		edit = {
			user: u,
			role: u.role,
			is_active: u.is_active,
			quota_gb: u.quota_bytes != null ? String(+(u.quota_bytes / GB).toFixed(2)) : '',
			password: '',
			email: u.email ?? ''
		};
		editOpen = true;
	}

	async function saveEdit() {
		if (!edit) return;
		const body = {
			email: edit.email,
			role: edit.role,
			is_active: edit.is_active,
			quota_gb: edit.quota_gb === '' ? null : Number(edit.quota_gb),
			clear_quota: edit.quota_gb === '',
			password: edit.password || null
		};
		if (await act(() => api.patch(`/api/admin/users/${edit!.user.id}`, body), 'Gespeichert')) editOpen = false;
	}

	async function confirmDelete() {
		if (!deleting) return;
		if (await act(() => api.del(`/api/admin/users/${deleting!.id}?delete_files=${deleteFiles}`), `${deleting.username} gelöscht`)) deleteOpen = false;
	}
</script>

<div class="mb-4 flex items-center">
	<p class="text-sm text-muted">{users.length} Benutzer</p>
	<button class="btn-primary ml-auto" onclick={() => (createOpen = true)}><Icon name="plus" size={16} />Benutzer anlegen</button>
</div>

<div class="card table-wrap">
	<table>
		<thead>
			<tr><th>Benutzer</th><th>Rolle</th><th>Speicher</th><th class="hidden md:table-cell">Letzte Anmeldung</th><th></th></tr>
		</thead>
		<tbody>
			{#each users as u (u.id)}
				<tr class={u.is_active ? '' : 'opacity-55'}>
					<td>
						<p class="font-medium">{u.username} {#if u.id === session.user?.id}<span class="text-xs font-normal text-muted">(du)</span>{/if}</p>
						<p class="text-xs text-muted">{u.email ?? '–'}</p>
					</td>
					<td>
						<span class="badge {u.role === 'admin' ? 'bg-accent-soft text-accent' : 'bg-surface-2 text-muted'}">{u.role === 'admin' ? 'Admin' : 'Benutzer'}</span>
						{#if !u.is_active}<span class="badge ml-1 bg-danger-soft text-danger">Gesperrt</span>{/if}
					</td>
					<td class="whitespace-nowrap">
						<p class="tabular-nums">{bytes(u.used_bytes)}{u.quota_bytes != null ? ` / ${bytes(u.quota_bytes)}` : ''}</p>
						<p class="text-xs text-muted">{u.downloads} Dateien</p>
					</td>
					<td class="hidden text-muted md:table-cell">{relative(u.last_login_at)}</td>
					<td class="text-right whitespace-nowrap">
						<button class="btn-icon" title="Bearbeiten" onclick={() => openEdit(u)}><Icon name="edit" size={16} /></button>
						{#if u.id !== session.user?.id}
							<button class="btn-icon hover:text-danger" title="Löschen" onclick={() => ((deleting = u), (deleteFiles = false), (deleteOpen = true))}>
								<Icon name="trash" size={16} />
							</button>
						{/if}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<Modal bind:open={createOpen} title="Benutzer anlegen">
	<form id="create-user" class="space-y-4" onsubmit={createUser}>
		<label class="block"><span class="label">Benutzername</span><input class="input" bind:value={form.username} autocapitalize="none" required /></label>
		<label class="block"><span class="label">Passwort</span><input class="input" type="text" bind:value={form.password} minlength={createMin} required /><span class="hint">Mindestens {createMin} Zeichen. Teile es der Person auf sicherem Weg mit.</span></label>
		<label class="block"><span class="label">E-Mail <span class="font-normal text-muted">(optional)</span></span><input class="input" type="email" bind:value={form.email} /></label>
		<div class="grid gap-4 sm:grid-cols-2">
			<label class="block"><span class="label">Rolle</span><select class="input" bind:value={form.role}><option value="user">Benutzer</option><option value="admin">Administrator</option></select></label>
			<label class="block"><span class="label">Kontingent (GB)</span><input class="input" type="number" min="0" step="0.5" bind:value={form.quota_gb} placeholder="unbegrenzt" /></label>
		</div>
	</form>
	{#snippet footer()}
		<button class="btn-ghost" onclick={() => (createOpen = false)}>Abbrechen</button>
		<button class="btn-primary" form="create-user" disabled={busy}>Anlegen</button>
	{/snippet}
</Modal>

<Modal bind:open={editOpen} title="Benutzer {edit?.user.username ?? ''} bearbeiten">
	{#if edit}
		<div class="space-y-4">
			<label class="block"><span class="label">E-Mail</span><input class="input" type="email" bind:value={edit.email} /></label>
			<div class="grid gap-4 sm:grid-cols-2">
				<label class="block"><span class="label">Rolle</span><select class="input" bind:value={edit.role}><option value="user">Benutzer</option><option value="admin">Administrator</option></select></label>
				<label class="block"><span class="label">Kontingent (GB)</span><input class="input" type="number" min="0" step="0.5" bind:value={edit.quota_gb} placeholder="unbegrenzt" /></label>
			</div>
			<label class="block"><span class="label">Neues Passwort</span><input class="input" type="text" bind:value={edit.password} placeholder="leer lassen = unverändert" /><span class="hint">Mindestens {edit.role === 'admin' ? 6 : userMin} Zeichen. Setzt das Passwort zurück und meldet alle Sitzungen ab.</span></label>
			{#if edit.user.id !== session.user?.id}
				<label class="flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={edit.is_active} /> Konto aktiv (deaktivieren sperrt die Anmeldung sofort)</label>
			{/if}
		</div>
	{/if}
	{#snippet footer()}
		<button class="btn-ghost" onclick={() => (editOpen = false)}>Abbrechen</button>
		<button class="btn-primary" disabled={busy} onclick={saveEdit}>Speichern</button>
	{/snippet}
</Modal>

<Modal bind:open={deleteOpen} title="Benutzer löschen?" size="sm">
	<p class="text-sm">Das Konto <b>{deleting?.username}</b> und alle zugehörigen Einträge werden entfernt.</p>
	<label class="mt-4 flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={deleteFiles} /> Auch alle Dateien des Benutzers löschen</label>
	{#snippet footer()}
		<button class="btn-ghost" onclick={() => (deleteOpen = false)}>Abbrechen</button>
		<button class="btn-danger" disabled={busy} onclick={confirmDelete}>Endgültig löschen</button>
	{/snippet}
</Modal>
