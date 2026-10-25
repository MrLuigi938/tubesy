<script lang="ts">
	import { t } from '#lib/i18n.svelte.ts';
	import '../app.css';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api, setUnauthorizedHandler } from '#lib/api.ts';
	import { appInfo, refreshInfo, updateStale } from '#lib/appinfo.svelte.ts';
	import Credit from '#lib/components/Credit.svelte';
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
			if (path !== '/setup') await goto('/setup', { replace: true });
		} else if (!session.user && !isPublic) {
			const next = path + page.url.search;
			await goto(`/login${next !== '/' ? `?next=${encodeURIComponent(next)}` : ''}`, { replace: true });
		} else if (session.user && isPublic) {
			await goto('/', { replace: true });
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

	// Version and update hint for the footer; the server itself checks twice a day.
	$effect(() => {
		if (!session.user) return;
		refreshInfo();
		const timer = setInterval(refreshInfo, 6 * 3600e3);
		return () => clearInterval(timer);
	});

	// Admins: red dot on "Verwaltung" and, once per browser session, a short hint.
	const isAdmin = $derived(session.user?.role === 'admin');
	const stale = $derived(isAdmin && updateStale(appInfo.update));
	let updateBubble = $state(false);
	$effect(() => {
		if (!stale || !appInfo.update) return;
		const key = 'tubesy-update-hint';
		try {
			if (!location.search.includes('updatehint') && sessionStorage.getItem(key) === appInfo.update.version) return;
			sessionStorage.setItem(key, appInfo.update.version);
		} catch {
			/* private mode: show it anyway */
		}
		updateBubble = true;
		const timer = setTimeout(() => (updateBubble = false), 5000);
		return () => clearTimeout(timer);
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
	<div class="flex min-h-screen flex-col">
		<header class="sticky top-0 z-30 border-b border-border bg-surface/85 backdrop-blur">
			<div class="relative mx-auto flex h-14 max-w-6xl items-center gap-2 px-4">
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
							<Icon name={item.icon} size={16} />{t(item.label)}
							{#if item.admin && stale}<span class="size-2 rounded-full bg-danger" title={t('Update verfügbar')}></span>{/if}
						</a>
					{/each}
				</nav>
				<div class="ml-auto flex items-center gap-1">
					<span
						class="mr-1 size-2 rounded-full {connection.online ? 'bg-ok' : 'bg-warn'}"
						title={connection.online ? t('Live-Verbindung aktiv') : t('Live-Verbindung getrennt – wird neu aufgebaut')}
					></span>
					<button class="btn-icon" onclick={toggleTheme} aria-label={t('Farbschema wechseln')}><Icon name={theme === 'light' ? 'moon' : 'sun'} /></button>
					<a href="/account" class="btn-ghost hidden sm:inline-flex {active('/account') ? 'bg-surface-2 text-text' : ''}">
						<Icon name="user" size={16} />{session.user.username}
					</a>
					<button class="btn-icon hidden sm:inline-flex" onclick={logout} title={t('Abmelden')}><Icon name="logout" /></button>
					<button class="btn-icon relative md:hidden" onclick={() => (menuOpen = !menuOpen)} aria-label={stale ? t('Menü – Update verfügbar') : t('Menü')}>
						<Icon name="menu" />
						{#if stale}<span class="absolute top-1.5 right-1.5 size-2 rounded-full bg-danger ring-2 ring-surface"></span>{/if}
					</button>
				</div>
				{#if updateBubble}
					<a
						href="/admin/settings#info"
						class="absolute top-[calc(100%+6px)] right-4 z-40 rounded-full bg-danger px-3.5 py-1.5 text-[13px] font-semibold text-white shadow-lg"
						onclick={() => (updateBubble = false)}>⬆ {t('Update verfügbar')}</a
					>
				{/if}
			</div>
			{#if menuOpen}
				<nav class="border-t border-border px-4 py-2 md:hidden">
					{#each [...nav.filter((n) => !n.admin || session.user?.role === 'admin'), { href: '/account', label: 'Konto', icon: 'user' as IconName }] as item (item.href)}
						<a href={item.href} class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium {active(item.href) ? 'bg-surface-2' : 'text-muted'}">
							<Icon name={item.icon} size={16} />{t(item.label)}
							{#if 'admin' in item && item.admin && stale}<span class="size-2 rounded-full bg-danger"></span>{/if}
						</a>
					{/each}
					<button class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted" onclick={logout}>
						<Icon name="logout" size={16} />{t('Abmelden')}
					</button>
				</nav>
			{/if}
		</header>
		<main class="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:py-8">
			{@render children()}
		</main>
		<Credit app version={appInfo.version} update={appInfo.update} />
	</div>
{/if}
