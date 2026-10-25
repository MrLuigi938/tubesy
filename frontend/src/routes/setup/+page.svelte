<script lang="ts">
	import { i18n, t } from '#lib/i18n.svelte.ts';
	import { goto } from '$app/navigation';
	import { api, errorText } from '#lib/api.ts';
	import AuthShell from '#lib/components/AuthShell.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import LangSwitch from '#lib/components/LangSwitch.svelte';
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
			error = t('Die Passwörter stimmen nicht überein');
			return;
		}
		busy = true;
		try {
			session.user = await api.post<User>('/api/setup', { username, password, language: i18n.lang });
			await goto('/');
		} catch (err) {
			error = errorText(err);
		} finally {
			busy = false;
		}
	}
</script>

<AuthShell langSwitch={false} title={t('Willkommen bei Tubesy')} subtitle={t('Wähle deine Sprache und lege das Administrator-Konto an.')}>
	<form class="space-y-4" onsubmit={submit}>
		<div class="flex items-center justify-between gap-3">
			<span class="label mb-0">{t('Sprache')}</span>
			<LangSwitch />
		</div>
		<label class="block">
			<span class="label">{t('Benutzername')}</span>
			<input class="input" bind:value={username} autocomplete="username" autocapitalize="none" required />
		</label>
		<label class="block">
			<span class="label">{t('Passwort')}</span>
			<input class="input" type="password" bind:value={password} autocomplete="new-password" required minlength="6" />
			<span class="hint">{t('Mindestens 6 Zeichen. Die Instanz ist ggf. öffentlich erreichbar, wähle ein sicheres Passwort.')}</span>
		</label>
		<label class="block">
			<span class="label">{t('Passwort wiederholen')}</span>
			<input class="input" type="password" bind:value={confirm} autocomplete="new-password" required />
		</label>
		{#if error}<p class="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>{/if}
		<button class="btn-primary w-full" disabled={busy}>
			{#if busy}<Icon name="loader" size={16} />{/if}{t('Einrichtung abschließen')}
		</button>
	</form>
</AuthShell>
