<script lang="ts">
	import { t } from '#lib/i18n.svelte.ts';
	import { api, errorText } from '#lib/api.ts';
	import { bytes, relative } from '#lib/format.ts';
	import { subscribe } from '#lib/live.svelte.ts';
	import { toast } from '#lib/toast.svelte.ts';
	import type { PlaylistGroup } from '#lib/types.ts';
	import { onMount } from 'svelte';
	import Icon from './Icon.svelte';
	import Modal from './Modal.svelte';
	import Thumb from './Thumb.svelte';

	let { onselect }: { onselect: (title: string) => void } = $props();

	let groups = $state<PlaylistGroup[]>([]);
	let loading = $state(true);
	let q = $state('');
	let timer: ReturnType<typeof setTimeout>;

	// Selection mode: several playlists at once.
	let selecting = $state(false);
	let selected = $state<Set<string>>(new Set());
	let deleteOpen = $state(false);
	let deleteFiles = $state(true);
	let busy = $state(false);

	async function load() {
		try {
			groups = await api.get<PlaylistGroup[]>(`/api/playlists${q.trim() ? `?q=${encodeURIComponent(q.trim())}` : ''}`);
			selected = new Set([...selected].filter((title) => groups.some((g) => g.title === title)));
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
		// A finished, hidden or removed playlist video changes counts and sizes.
		return subscribe((e) => {
			if (e.event === 'download_removed' || (e.event === 'download' && (e.data.hidden || (e.data.playlist_title && e.data.status === 'completed')))) later(800);
		});
	});

	function toggle(title: string) {
		const next = new Set(selected);
		if (next.has(title)) next.delete(title);
		else next.add(title);
		selected = next;
	}

	async function run(action: () => Promise<unknown>) {
		busy = true;
		try {
			await action();
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			busy = false;
		}
	}

	function batch(action: 'hide' | 'delete') {
		run(async () => {
			const res = await api.post<{ done: number; skipped: number }>('/api/playlists/batch', {
				titles: [...selected],
				action,
				delete_files: deleteFiles
			});
			toast(t(action === 'hide' ? 'Ausgeblendet: {n}' : 'Gelöscht: {n}', { n: res.done }));
			deleteOpen = false;
			selected = new Set();
			await load();
		});
	}

	function zip() {
		run(async () => {
			const { url } = await api.post<{ url: string }>('/api/zip', { playlists: [...selected] });
			location.href = url;
		});
	}
</script>

<div class="mb-5 flex gap-2">
	<div class="relative flex-1">
		<Icon name="search" size={16} class="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted" />
		<input class="input pl-9" placeholder={t('Playlist suchen…')} bind:value={q} oninput={() => later(250)} />
	</div>
	{#if groups.length}
		<button class="btn-secondary {selecting ? 'border-accent text-accent' : ''}" onclick={() => ((selecting = !selecting), (selected = new Set()))}>
			<Icon name="select" size={16} />{selecting ? t('Fertig') : t('Auswählen')}
		</button>
	{/if}
</div>

{#if selecting}
	<div class="card sticky bottom-3 z-20 mb-4 flex flex-wrap items-center gap-2 p-2.5 shadow-lg sm:static sm:shadow-none">
		<span class="px-1 text-sm font-medium">{t('{n} ausgewählt', { n: selected.size })}</span>
		<button class="btn-ghost h-8 px-2.5 py-1 text-xs" onclick={() => (selected = selected.size < groups.length ? new Set(groups.map((g) => g.title)) : new Set())}>
			{selected.size < groups.length ? t('Alle auswählen') : t('Keine')}
		</button>
		<span class="ml-auto"></span>
		<button class="btn-secondary h-8 px-2.5 py-1 text-xs" disabled={busy || !selected.size} onclick={zip}><Icon name="download" size={14} />{t('Als ZIP')}</button>
		<button class="btn-secondary h-8 px-2.5 py-1 text-xs" disabled={busy || !selected.size} onclick={() => batch('hide')}><Icon name="eye-off" size={14} />{t('Ausblenden')}</button>
		<button class="btn-danger h-8 px-2.5 py-1 text-xs" disabled={busy || !selected.size} onclick={() => ((deleteFiles = true), (deleteOpen = true))}>
			<Icon name="trash" size={14} />{t('Löschen')}
		</button>
	</div>
{/if}

{#if loading}
	<div class="flex justify-center py-16 text-muted"><Icon name="loader" /></div>
{:else if !groups.length}
	<div class="card flex flex-col items-center px-6 py-14 text-center">
		<div class="mb-3 flex size-11 items-center justify-center rounded-full bg-surface-2 text-muted"><Icon name="folder" /></div>
		<p class="font-medium">{q ? t('Keine Treffer') : t('Noch keine Playlists')}</p>
		<p class="mt-1 text-sm text-muted">{q ? t('Versuche einen anderen Suchbegriff.') : t('Lade eine Playlist herunter, sie erscheint dann hier gesammelt.')}</p>
	</div>
{:else}
	<p class="mb-3 text-sm text-muted">{groups.length} {groups.length === 1 ? 'Playlist' : 'Playlists'}</p>
	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each groups as g (g.title)}
			{@const isSelected = selected.has(g.title)}
			<button class="group text-left" onclick={() => (selecting ? toggle(g.title) : onselect(g.title))}>
				<!-- stacked look: two offset layers behind the cover -->
				<div class="relative mx-3 h-2 rounded-t-lg bg-surface-2/60"></div>
				<div class="relative mx-1.5 h-1.5 rounded-t-lg bg-surface-2"></div>
				<article class="card overflow-hidden transition group-hover:border-accent/60 {isSelected ? 'ring-2 ring-accent' : ''}">
					<div class="relative aspect-video">
						<Thumb src={g.thumbnail} class="size-full rounded-none" />
						{#if selecting}
							<span class="absolute top-2 left-2 flex size-6 items-center justify-center rounded-md border-2 {isSelected ? 'border-accent bg-accent text-white' : 'border-white bg-black/40'}">
								{#if isSelected}<Icon name="check" size={14} />{/if}
							</span>
						{/if}
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
							{#if g.pending}<span class="badge bg-info-soft text-info">{t('+{n} in Arbeit', { n: g.pending })}</span>{/if}
						</p>
					</div>
				</article>
			</button>
		{/each}
	</div>
{/if}

<Modal bind:open={deleteOpen} title={t('{n} Playlists löschen?', { n: selected.size })} size="sm">
	<p class="text-sm">{t('Alle Videos der ausgewählten Playlists werden aus der Bibliothek entfernt. Laufende Downloads werden übersprungen.')}</p>
	<label class="mt-4 flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={deleteFiles} /> {t('Dateien auch auf dem Speicher löschen')}</label>
	{#snippet footer()}
		<button class="btn-ghost" onclick={() => (deleteOpen = false)}>{t('Abbrechen')}</button>
		<button class="btn-danger" disabled={busy} onclick={() => batch('delete')}>{t('Löschen')}</button>
	{/snippet}
</Modal>
