<script lang="ts">
	import '../app.css';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api, setUnauthorizedHandler } from '#lib/api.ts';
	import Icon, { type IconName } from '#lib/components/Icon.svelte';
	import Toasts from '#lib/components/Toasts.svelte';
	import { connect, connection, disconnect } from '#lib/live.svelte.ts';
	import { refreshUser, session } from '#lib/session.svelte.ts';
	import { onMount } from 'svelte';

	let { children } = $props();

	const PUBLIC = ['/login', '/register', '/setup'];
	const isPublic = $derived(PUBLIC.some((p) => page.url.pathname.startsWith(p)));
	let menuOpen = $state(false);
	let theme = $state<'light' | 'dark' | null>(null);

	const nav: { href: string; label: string; icon: IconName; admin?: boolean }[] = [
		{ href: '/', label: 'Downloads', icon: 'download' },
		{ href: '/library', label: 'Bibliothek', icon: 'library' },
		{ href: '/presets', label: 'Presets', icon: 'sliders' },
		{ href: '/admin/users', label: 'Verwaltung', icon: 'shield', admin: true }
	];

	function active(href: string) {
		const path = page.url.pathname;
		if (href === '/') return path === '/';
		if (href.startsWith('/admin')) return path.startsWith('/admin');
		return path.startsWith(href);
	}

	async function guard() {
		const status = await api.get<{ needs_setup: boolean }>('/api/status');
		const path = page.url.pathname;
		if (status.needs_setup) {
			if (path !== '/setup') await goto('/setup', { replaceState: true });
		} else if (!session.user && !isPublic) {
			const next = path + page.url.search;
			await goto(`/login${next !== '/' ? `?next=${encodeURIComponent(next)}` : ''}`, { replaceState: true });
		} else if (session.user && isPublic) {
			await goto('/', { replaceState: true });
		}
	}

	onMount(async () => {
		try {
			theme = (localStorage.getItem('tubesy-theme') as typeof theme) ?? null;
		} catch {}
		setUnauthorizedHandler(() => {
			session.user = null;
			guard();
		});
		await refreshUser();
		session.ready = true;
		await guard();
	});

	$effect(() => {
		if (session.user) connect();
		else disconnect();
	});

	$effect(() => {
		// Re-check access on navigation (e.g. after logout).
		page.url.pathname;
		if (session.ready) guard();
		menuOpen = false;
	});

	function toggleTheme() {
		const dark = theme ? theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
		theme = dark ? 'light' : 'dark';
		document.documentElement.dataset.theme = theme;
		try {
			localStorage.setItem('tubesy-theme', theme);
		} catch {}
	}

	async function logout() {
		try {
			await api.post('/api/auth/logout');
		} finally {
			session.user = null;
			await goto('/login');
		}
	}
</script>

<Toasts />

{#if !session.ready}
	<div class="flex min-h-screen items-center justify-center text-muted"><Icon name="loader" size={28} /></div>
{:else if isPublic}
	{@render children()}
{:else if !session.user}
	<div class="flex min-h-screen items-center justify-center text-muted"><Icon name="loader" size={28} /></div>
{:else}
	<div class="min-h-screen">
		<header class="sticky top-0 z-30 border-b border-border bg-surface/85 backdrop-blur">
			<div class="mx-auto flex h-14 max-w-6xl items-center gap-2 px-4">
				<a href="/" class="mr-4 flex items-center gap-2 font-semibold">
					<img src="/favicon.svg" alt="" class="size-7" />
					<span>Tubesy</span>
				</a>
				<nav class="hidden items-center gap-1 md:flex">
					{#each nav.filter((n) => !n.admin || session.user?.role === 'admin') as item (item.href)}
						<a
							href={item.href}
							class="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors {active(item.href)
								? 'bg-surface-2 text-text'
								: 'text-muted hover:text-text'}"
						>
							<Icon name={item.icon} size={16} />{item.label}
						</a>
					{/each}
				</nav>
				<div class="ml-auto flex items-center gap-1">
					<span
						class="mr-1 size-2 rounded-full {connection.online ? 'bg-ok' : 'bg-warn'}"
						title={connection.online ? 'Live-Verbindung aktiv' : 'Live-Verbindung getrennt – wird neu aufgebaut'}
					></span>
					<button class="btn-icon" onclick={toggleTheme} aria-label="Farbschema wechseln"><Icon name={theme === 'light' ? 'moon' : 'sun'} /></button>
					<a href="/account" class="btn-ghost hidden sm:inline-flex {active('/account') ? 'bg-surface-2 text-text' : ''}">
						<Icon name="user" size={16} />{session.user.username}
					</a>
					<button class="btn-icon hidden sm:inline-flex" onclick={logout} title="Abmelden"><Icon name="logout" /></button>
					<button class="btn-icon md:hidden" onclick={() => (menuOpen = !menuOpen)} aria-label="Menü"><Icon name="menu" /></button>
				</div>
			</div>
			{#if menuOpen}
				<nav class="border-t border-border px-4 py-2 md:hidden">
					{#each [...nav.filter((n) => !n.admin || session.user?.role === 'admin'), { href: '/account', label: 'Konto', icon: 'user' as IconName }] as item (item.href)}
						<a href={item.href} class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium {active(item.href) ? 'bg-surface-2' : 'text-muted'}">
							<Icon name={item.icon} size={16} />{item.label}
						</a>
					{/each}
					<button class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted" onclick={logout}>
						<Icon name="logout" size={16} />Abmelden
					</button>
				</nav>
			{/if}
		</header>
		<main class="mx-auto max-w-6xl px-4 py-6 sm:py-8">
			{@render children()}
		</main>
	</div>
{/if}
