<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import Icon, { type IconName } from '#lib/components/Icon.svelte';
	import { session } from '#lib/session.svelte.ts';

	let { children } = $props();

	const tabs: { href: string; label: string; icon: IconName }[] = [
		{ href: '/admin/users', label: 'Benutzer', icon: 'users' },
		{ href: '/admin/invites', label: 'Einladungen', icon: 'mail' },
		{ href: '/admin/downloads', label: 'Alle Downloads', icon: 'list' },
		{ href: '/admin/settings', label: 'Einstellungen', icon: 'settings' }
	];

	$effect(() => {
		if (session.user && session.user.role !== 'admin') goto('/', { replace: true });
	});
</script>

{#if session.user?.role === 'admin'}
	<h1 class="text-2xl font-semibold tracking-tight">Verwaltung</h1>
	<nav class="mt-4 mb-6 flex gap-1 overflow-x-auto border-b border-border">
		{#each tabs as t (t.href)}
			<a
				href={t.href}
				class="-mb-px flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium whitespace-nowrap {page.url.pathname.startsWith(t.href)
					? 'border-accent text-text'
					: 'border-transparent text-muted hover:text-text'}"
			>
				<Icon name={t.icon} size={16} />{t.label}
			</a>
		{/each}
	</nav>
	{@render children()}
{/if}
