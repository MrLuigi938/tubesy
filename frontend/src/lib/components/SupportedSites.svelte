<script lang="ts">
	import { api, errorText } from '#lib/api.ts';
	import Icon from './Icon.svelte';

	const POPULAR = [
		'YouTube', 'YouTube Music', 'Vimeo', 'Twitch', 'TikTok', 'Instagram', 'X / Twitter', 'Facebook',
		'Reddit', 'SoundCloud', 'Bandcamp', 'Dailymotion', 'ARD Mediathek', 'ZDF Mediathek', 'arte', 'Bilibili'
	];

	let open = $state(false);
	let sites = $state<string[] | null>(null);
	let error = $state('');
	let filter = $state('');

	const shown = $derived.by(() => {
		if (!sites) return [];
		const f = filter.trim().toLowerCase();
		return f ? sites.filter((s) => s.toLowerCase().includes(f)) : sites;
	});

	async function toggle(e: Event) {
		open = (e.currentTarget as HTMLDetailsElement).open;
		if (open && !sites) {
			try {
				sites = (await api.get<{ sites: string[] }>('/api/extractors')).sites;
			} catch (err) {
				error = errorText(err);
			}
		}
	}
</script>

<details class="card mt-3 overflow-hidden" ontoggle={toggle}>
	<summary class="flex cursor-pointer list-none items-center gap-2 px-4 py-2.5 text-sm text-muted select-none hover:text-text [&::-webkit-details-marker]:hidden">
		<Icon name="list" size={16} />
		<span>Welche Seiten werden unterstützt?</span>
		{#if sites}<span class="badge bg-surface-2">{sites.length.toLocaleString('de-DE')}</span>{/if}
		<span class="ml-auto transition-transform {open ? 'rotate-180' : ''}"><Icon name="chevron" size={16} /></span>
	</summary>
	<div class="border-t border-border px-4 py-4">
		<p class="text-xs font-semibold tracking-wide text-muted uppercase">Beliebt</p>
		<div class="mt-2 flex flex-wrap gap-1.5">
			{#each POPULAR as name (name)}<span class="badge bg-accent-soft py-1 text-accent">{name}</span>{/each}
		</div>
		<p class="mt-3 text-xs text-muted">
			Neben einzelnen Videos funktionieren meist auch Playlists, Kanäle und Alben. Direkte Links auf Video-/Audiodateien gehen immer.
		</p>

		<div class="mt-4 flex items-center gap-2">
			<p class="text-xs font-semibold tracking-wide text-muted uppercase">Alle Seiten</p>
			<div class="relative ml-auto w-full max-w-56">
				<Icon name="search" size={14} class="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-muted" />
				<input class="input h-8 py-1 pl-8 text-xs" placeholder="Seite suchen…" bind:value={filter} />
			</div>
		</div>
		{#if error}
			<p class="mt-3 text-sm text-danger">{error}</p>
		{:else if !sites}
			<div class="flex justify-center py-6 text-muted"><Icon name="loader" /></div>
		{:else if !shown.length}
			<p class="mt-3 text-sm text-muted">Keine Seite mit „{filter}“ gefunden. Probieren lohnt sich trotzdem: Viele Seiten mit eingebetteten Videos funktionieren auch ohne eigenen Eintrag.</p>
		{:else}
			<ul class="mt-3 grid max-h-64 grid-cols-2 gap-x-4 gap-y-1 overflow-y-auto text-sm sm:grid-cols-3 md:grid-cols-4">
				{#each shown as site (site)}<li class="truncate" title={site}>{site}</li>{/each}
			</ul>
			<p class="mt-2 text-xs text-muted">{shown.length.toLocaleString('de-DE')} {shown.length === 1 ? 'Seite' : 'Seiten'} · Liste von yt-dlp</p>
		{/if}
	</div>
</details>
