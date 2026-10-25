<script lang="ts">
	import { t } from '#lib/i18n.svelte.ts';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api, errorText } from '#lib/api.ts';
	import AuthShell from '#lib/components/AuthShell.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { session } from '#lib/session.svelte.ts';
	import type { User } from '#lib/types.ts';
	import { onMount } from 'svelte';

	let username = $state('');
	let password = $state('');
	let remember = $state(true);
	let error = $state('');
	let busy = $state(false);
	let canRegister = $state(false);

	onMount(async () => {
		const s = await api.get<{ registration_mode: string }>('/api/status');
		canRegister = s.registration_mode === 'open';
	});

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		busy = true;
		error = '';
		try {
			session.user = await api.post<User>('/api/auth/login', { username, password, remember });
			const next = page.url.searchParams.get('next');
			await goto(next?.startsWith('/') && !next.startsWith('//') ? next : '/');
		} catch (err) {
			error = errorText(err);
		} finally {
			busy = false;
		}
	}
</script>

<AuthShell title={t('Bei Tubesy anmelden')}>
	<form class="space-y-4" onsubmit={submit}>
		<label class="block">
			<span class="label">{t('Benutzername')}</span>
			<input class="input" bind:value={username} autocomplete="username" autocapitalize="none" required />
		</label>
		<label class="block">
			<span class="label">{t('Passwort')}</span>
			<input class="input" type="password" bind:value={password} autocomplete="current-password" required />
		</label>
		<label class="flex items-center gap-2 text-sm text-muted">
			<input type="checkbox" bind:checked={remember} /> {t('Angemeldet bleiben')}
		</label>
		{#if error}<p class="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>{/if}
		<button class="btn-primary w-full" disabled={busy}>
			{#if busy}<Icon name="loader" size={16} />{/if}{t('Anmelden')}
		</button>
	</form>
	{#if canRegister}
		<p class="mt-5 text-center text-sm text-muted">{t('Noch kein Konto?')} <a class="font-medium text-accent hover:underline" href="/register">{t('Registrieren')}</a></p>
	{/if}
</AuthShell>
