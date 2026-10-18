<script lang="ts">
	import { api, errorText } from '#lib/api.ts';
	import { bytes, relative } from '#lib/format.ts';
	import { subscribe } from '#lib/live.svelte.ts';
	import { toast } from '#lib/toast.svelte.ts';
	import type { PlaylistGroup } from '#lib/types.ts';
	import { onMount } from 'svelte';
	import Icon from './Icon.svelte';
	import Thumb from './Thumb.svelte';

	let { onselect }: { onselect: (title: string) => void } = $props();

	let groups = $state<PlaylistGroup[]>([]);
	let loading = $state(true);
	let q = $state('');
	let timer: ReturnType<typeof setTimeout>;

	async function load() {
		try {
			groups = await api.get<PlaylistGroup[]>(`/api/playlists${q.trim() ? `?q=${encodeURIComponent(q.trim())}` : ''}`);
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			loading = false;
		}
	}

	function later(ms = 400) {
		clearTimeout(timer);
		timer = setTimeout(load, ms);
	}

	onMount(() => {
		load();
		// A finished or removed playlist video changes counts and sizes.
		return subscribe((e) => {
			if (e.event === 'download_removed' || (e.event === 'download' && e.data.playlist_title && e.data.status === 'completed')) later(800);
		});
	});
</script>

<div class="relative mb-5">
	<Icon name="search" size={16} class="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted" />
	<input class="input pl-9" placeholder="Playlist suchen…" bind:value={q} oninput={() => later(250)} />
</div>

{#if loading}
	<div class="flex justify-center py-16 text-muted"><Icon name="loader" /></div>
{:else if !groups.length}
	<div class="card flex flex-col items-center px-6 py-14 text-center">
		<div class="mb-3 flex size-11 items-center justify-center rounded-full bg-surface-2 text-muted"><Icon name="folder" /></div>
		<p class="font-medium">{q ? 'Keine Treffer' : 'Noch keine Playlists'}</p>
		<p class="mt-1 text-sm text-muted">{q ? 'Versuche einen anderen Suchbegriff.' : 'Lade eine Playlist herunter, sie erscheint dann hier gesammelt.'}</p>
	</div>
{:else}
	<p class="mb-3 text-sm text-muted">{groups.length} {groups.length === 1 ? 'Playlist' : 'Playlists'}</p>
	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each groups as g (g.title)}
			<button class="group text-left" onclick={() => onselect(g.title)}>
				<!-- stacked look: two offset layers behind the cover -->
				<div class="relative mx-3 h-2 rounded-t-lg bg-surface-2/60"></div>
				<div class="relative mx-1.5 h-1.5 rounded-t-lg bg-surface-2"></div>
				<article class="card overflow-hidden transition group-hover:border-accent/60">
					<div class="relative aspect-video">
						<Thumb src={g.thumbnail} class="size-full rounded-none" />
						<span class="absolute inset-y-0 right-0 flex w-24 flex-col items-center justify-center gap-1 bg-black/70 text-white">
							<Icon name="list" size={20} />
							<span class="text-sm font-semibold tabular-nums">{g.count}</span>
							<span class="text-[11px] opacity-80">{g.count === 1 ? 'Video' : 'Videos'}</span>
						</span>
					</div>
					<div class="p-3">
						<p class="line-clamp-2 text-sm font-medium">{g.title}</p>
						<p class="mt-1 truncate text-xs text-muted">{g.uploader ?? ''}</p>
						<p class="mt-2 flex items-center gap-2 text-xs text-muted">
							<span>{bytes(g.total_size)} · {relative(g.finished_at)}</span>
							{#if g.pending}<span class="badge bg-info-soft text-info">+{g.pending} in Arbeit</span>{/if}
						</p>
					</div>
				</article>
			</button>
		{/each}
	</div>
{/if}
