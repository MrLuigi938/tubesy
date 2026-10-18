<script lang="ts">
	import { goto } from '$app/navigation';
	import { api, errorText } from '#lib/api.ts';
	import AuthShell from '#lib/components/AuthShell.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { session } from '#lib/session.svelte.ts';
	import type { User } from '#lib/types.ts';

	let username = $state('admin');
	let password = $state('');
	let confirm = $state('');
	let error = $state('');
	let busy = $state(false);

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		if (password !== confirm) {
			error = 'Die Passwörter stimmen nicht überein';
			return;
		}
		busy = true;
		try {
			session.user = await api.post<User>('/api/setup', { username, password });
			await goto('/');
		} catch (err) {
			error = errorText(err);
		} finally {
			busy = false;
		}
	}
</script>

<AuthShell title="Willkommen bei TubeVault" subtitle="Lege zuerst das Administrator-Konto an.">
	<form class="space-y-4" onsubmit={submit}>
		<label class="block">
			<span class="label">Benutzername</span>
			<input class="input" bind:value={username} autocomplete="username" autocapitalize="none" required />
		</label>
		<label class="block">
			<span class="label">Passwort</span>
			<input class="input" type="password" bind:value={password} autocomplete="new-password" required minlength="10" />
			<span class="hint">Mindestens 10 Zeichen. Die Instanz ist ggf. öffentlich erreichbar, wähle ein starkes Passwort.</span>
		</label>
		<label class="block">
			<span class="label">Passwort wiederholen</span>
			<input class="input" type="password" bind:value={confirm} autocomplete="new-password" required />
		</label>
		{#if error}<p class="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>{/if}
		<button class="btn-primary w-full" disabled={busy}>
			{#if busy}<Icon name="loader" size={16} />{/if}Einrichtung abschließen
		</button>
	</form>
</AuthShell>
