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

	const invite = page.url.searchParams.get('invite');
	let phase = $state<'loading' | 'ok' | 'closed' | 'invalid'>('loading');
	let username = $state('');
	let email = $state('');
	let password = $state('');
	let confirm = $state('');
	let error = $state('');
	let busy = $state(false);
	let minLength = $state(6);

	onMount(async () => {
		const s = await api.get<{ registration_mode: string; invite_valid: boolean | null; min_password_length: number }>(
			`/api/status${invite ? `?invite=${encodeURIComponent(invite)}` : ''}`
		);
		minLength = s.min_password_length;
		if (invite) phase = s.invite_valid ? 'ok' : 'invalid';
		else phase = s.registration_mode === 'open' ? 'ok' : 'closed';
	});

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		if (password !== confirm) {
			error = t('Die Passwörter stimmen nicht überein');
			return;
		}
		busy = true;
		try {
			session.user = await api.post<User>('/api/auth/register', { username, email: email || null, password, invite });
			await goto('/');
		} catch (err) {
			error = errorText(err);
		} finally {
			busy = false;
		}
	}
</script>

<AuthShell title={t('Konto erstellen')} subtitle={invite ? t('Du wurdest zu Tubesy eingeladen.') : undefined}>
	{#if phase === 'loading'}
		<div class="flex justify-center py-6 text-muted"><Icon name="loader" /></div>
	{:else if phase !== 'ok'}
		<p class="text-sm text-muted">
			{phase === 'invalid'
				? t('Diese Einladung ist ungültig, abgelaufen oder wurde bereits verwendet.')
				: t('Die Registrierung ist nur mit einer Einladung möglich. Bitte wende dich an den Administrator.')}
		</p>
		<a href="/login" class="btn-secondary mt-5 w-full">{t('Zur Anmeldung')}</a>
	{:else}
		<form class="space-y-4" onsubmit={submit}>
			<label class="block">
				<span class="label">{t('Benutzername')}</span>
				<input class="input" bind:value={username} autocomplete="username" autocapitalize="none" required minlength="3" maxlength="32" />
				<span class="hint">{t('Kleinbuchstaben, Ziffern, Punkt, Unterstrich und Bindestrich. Wird auch als Ordnername verwendet.')}</span>
			</label>
			<label class="block">
				<span class="label">{t('E-Mail')} <span class="font-normal text-muted">({t('optional')})</span></span>
				<input class="input" type="email" bind:value={email} autocomplete="email" />
			</label>
			<label class="block">
				<span class="label">{t('Passwort')}</span>
				<input class="input" type="password" bind:value={password} autocomplete="new-password" required minlength={minLength} />
				<span class="hint">{t('Mindestens {n} Zeichen.', { n: minLength })}</span>
			</label>
			<label class="block">
				<span class="label">{t('Passwort wiederholen')}</span>
				<input class="input" type="password" bind:value={confirm} autocomplete="new-password" required />
			</label>
			{#if error}<p class="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>{/if}
			<button class="btn-primary w-full" disabled={busy}>
				{#if busy}<Icon name="loader" size={16} />{/if}{t('Registrieren')}
			</button>
		</form>
		<p class="mt-5 text-center text-sm text-muted">{t('Schon ein Konto?')} <a class="font-medium text-accent hover:underline" href="/login">{t('Anmelden')}</a></p>
	{/if}
</AuthShell>
