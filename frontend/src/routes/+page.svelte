<script lang="ts">
	import { page } from '$app/state';
	import { api, errorText } from '#lib/api.ts';
	import DownloadCard from '#lib/components/DownloadCard.svelte';
	import SupportedSites from '#lib/components/SupportedSites.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Thumb from '#lib/components/Thumb.svelte';
	import { duration } from '#lib/format.ts';
	import { applyEvent, subscribe } from '#lib/live.svelte.ts';
	import { session } from '#lib/session.svelte.ts';
	import { toast } from '#lib/toast.svelte.ts';
	import type { Download, Preset, ProbeResult } from '#lib/types.ts';
	import { onMount } from 'svelte';

	const QUEUE = new Set(['queued', 'downloading', 'processing', 'failed', 'canceled']);

	let url = $state('');
	let probing = $state(false);
	let probeError = $state('');
	let result = $state<ProbeResult | null>(null);
	let selected = $state<Set<number>>(new Set());
	let ownFolder = $state(true);
	let filter = $state('');

	let presets = $state<Preset[]>([]);
	let presetId = $state<number | null>(null);
	let submitting = $state(false);

	let queue = $state<Download[]>([]);
	let recent = $state<Download[]>([]);
	let loaded = $state(false);

	const activeCount = $derived(queue.filter((d) => d.status !== 'failed' && d.status !== 'canceled').length);
	const finishedCount = $derived(queue.length - activeCount);
	const entries = $derived(result?.entries ?? []);
	const visibleEntries = $derived(
		filter ? entries.filter((e) => e.title.toLowerCase().includes(filter.toLowerCase())) : entries
	);

	onMount(() => {
		load();
		const unsub = subscribe((e) => {
			queue = applyEvent(queue, e, (d) => QUEUE.has(d.status));
			if (e.event === 'download' && e.data.status === 'completed' && e.data.user_id === session.user?.id) {
				recent = [e.data, ...recent.filter((d) => d.id !== e.data.id)].slice(0, 6);
			}
			if (e.event === 'download_removed') recent = recent.filter((d) => d.id !== e.data.id);
		});
		// Opened via the PWA share sheet or a bookmarklet: /?url=...
		const shared = page.url.searchParams.get('url') ?? page.url.searchParams.get('text');
		const match = shared?.match(/https?:\/\/\S+/);
		if (match) {
			url = match[0];
			probe();
		}
		return unsub;
	});

	async function load() {
		const [p, q, r] = await Promise.all([
			api.get<{ items: Preset[] }>('/api/presets'),
			api.get<{ items: Download[] }>('/api/downloads?view=queue&limit=500'),
			api.get<{ items: Download[] }>('/api/downloads?view=library&limit=6')
		]);
		presets = p.items;
		const preferred = session.user?.default_preset_id;
		presetId = presets.find((x) => x.id === preferred)?.id ?? presets[0]?.id ?? null;
		queue = q.items;
		recent = r.items;
		loaded = true;
	}

	async function probe(e?: SubmitEvent) {
		e?.preventDefault();
		if (!url.trim()) return;
		probing = true;
		probeError = '';
		result = null;
		filter = '';
		try {
			result = await api.post<ProbeResult>('/api/probe', { url: url.trim() });
			selected = new Set((result.entries ?? []).map((x) => x.index));
		} catch (err) {
			probeError = errorText(err);
		} finally {
			probing = false;
		}
	}

	function toggle(index: number) {
		const next = new Set(selected);
		if (next.has(index)) next.delete(index);
		else next.add(index);
		selected = next;
	}

	function selectAll(on: boolean) {
		const next = new Set(selected);
		for (const e of visibleEntries) {
			if (on) next.add(e.index);
			else next.delete(e.index);
		}
		selected = next;
	}

	async function submit() {
		if (!result || presetId == null) return;
		const isList = result.type === 'playlist';
		const items = isList
			? entries.filter((e) => selected.has(e.index)).map((e) => ({ ...e, video_id: e.video_id ?? null }))
			: [
					{
						url: result.url,
						video_id: result.video_id,
						title: result.title,
						uploader: result.uploader,
						thumbnail: result.thumbnail,
						duration: result.duration
					}
				];
		if (!items.length) return;
		submitting = true;
		try {
			await api.post('/api/downloads', {
				preset_id: presetId,
				items,
				playlist_title: isList ? result.title : null,
				own_folder: ownFolder
			});
			toast(items.length === 1 ? 'Zur Warteschlange hinzugefügt' : `${items.length} Videos zur Warteschlange hinzugefügt`);
			result = null;
			url = '';
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			submitting = false;
		}
	}

	async function clearFinished() {
		try {
			await api.post('/api/downloads/clear', { statuses: ['failed', 'canceled'] });
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}
</script>

<section class="mx-auto max-w-3xl">
	<h1 class="text-2xl font-semibold tracking-tight">Neuer Download</h1>
	<p class="mt-1 text-sm text-muted">YouTube-Videos, Playlists und Kanäle sowie viele weitere Seiten.</p>

	<form class="mt-5 flex flex-col gap-2 sm:flex-row" onsubmit={probe}>
		<div class="relative flex-1">
			<Icon name="link" size={16} class="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted" />
			<input
				class="input h-11 pl-9 text-base sm:text-sm"
				placeholder="https://www.youtube.com/watch?v=…"
				bind:value={url}
				type="url"
				inputmode="url"
				required
			/>
		</div>
		<button class="btn-primary h-11 px-5" disabled={probing || !url.trim()}>
			{#if probing}<Icon name="loader" size={16} />Wird geprüft…{:else}<Icon name="search" size={16} />Prüfen{/if}
		</button>
	</form>

	<SupportedSites />

	{#if probeError}
		<div class="mt-3 flex items-start gap-2 rounded-lg bg-danger-soft px-3 py-2.5 text-sm text-danger">
			<Icon name="alert" size={16} class="mt-0.5" /><span class="break-words">{probeError}</span>
		</div>
	{/if}

	{#if result}
		<div class="card mt-4 overflow-hidden">
			<div class="flex gap-4 p-4">
				<Thumb src={result.thumbnail ?? entries[0]?.thumbnail ?? null} class="aspect-video w-32 sm:w-44" />
				<div class="min-w-0 flex-1">
					<span class="badge bg-surface-2 text-muted">
						{result.type === 'playlist' ? `Playlist · ${result.count} Videos` : (result.extractor ?? 'Video')}
					</span>
					<p class="mt-1.5 line-clamp-2 font-semibold">{result.title ?? result.url}</p>
					<p class="mt-0.5 text-sm text-muted">
						{result.uploader ?? ''}{#if result.duration}{result.uploader ? ' · ' : ''}{duration(result.duration)}{/if}
					</p>
				</div>
			</div>

			{#if result.type === 'playlist'}
				<div class="border-t border-border">
					<div class="flex flex-wrap items-center gap-2 px-4 py-2.5">
						<input class="input h-8 max-w-56 py-1" placeholder="Filtern…" bind:value={filter} />
						<button class="btn-ghost h-8 px-2.5 py-1" onclick={() => selectAll(true)}>Alle</button>
						<button class="btn-ghost h-8 px-2.5 py-1" onclick={() => selectAll(false)}>Keine</button>
						<span class="ml-auto text-sm text-muted">{selected.size} von {entries.length} ausgewählt</span>
					</div>
					<ul class="max-h-80 overflow-y-auto border-t border-border">
						{#each visibleEntries as entry (entry.index)}
							<li>
								<label class="flex cursor-pointer items-center gap-3 px-4 py-2 hover:bg-surface-2">
									<input type="checkbox" checked={selected.has(entry.index)} onchange={() => toggle(entry.index)} />
									<span class="w-8 text-right text-xs text-muted tabular-nums">{entry.index}</span>
									<span class="min-w-0 flex-1 truncate text-sm">{entry.title}</span>
									<span class="text-xs text-muted tabular-nums">{duration(entry.duration)}</span>
								</label>
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			<div class="flex flex-col gap-3 border-t border-border bg-surface-2/50 px-4 py-3 sm:flex-row sm:items-center">
				<label class="flex items-center gap-2 text-sm">
					<span class="text-muted">Preset</span>
					<select class="input h-9 w-auto py-1" bind:value={presetId}>
						{#each presets as p (p.id)}<option value={p.id}>{p.name}</option>{/each}
					</select>
				</label>
				{#if result.type === 'playlist'}
					<label class="flex items-center gap-2 text-sm text-muted">
						<input type="checkbox" bind:checked={ownFolder} /> Eigener Ordner
					</label>
				{/if}
				<div class="flex gap-2 sm:ml-auto">
					<button class="btn-ghost" onclick={() => (result = null)}>Verwerfen</button>
					<button class="btn-primary" disabled={submitting || (result.type === 'playlist' && !selected.size)} onclick={submit}>
						{#if submitting}<Icon name="loader" size={16} />{:else}<Icon name="download" size={16} />{/if}
						{result.type === 'playlist' ? `${selected.size} herunterladen` : 'Herunterladen'}
					</button>
				</div>
			</div>
		</div>
	{/if}
</section>

<section class="mx-auto mt-10 max-w-3xl">
	<div class="mb-3 flex items-center gap-3">
		<h2 class="text-lg font-semibold">Warteschlange</h2>
		{#if activeCount}<span class="badge bg-info-soft text-info">{activeCount} aktiv</span>{/if}
		{#if finishedCount}
			<button class="btn-ghost ml-auto h-8 px-2.5 py-1 text-xs" onclick={clearFinished}>Fehler & Abbrüche entfernen</button>
		{/if}
	</div>
	{#if !loaded}
		<div class="flex justify-center py-10 text-muted"><Icon name="loader" /></div>
	{:else if queue.length === 0}
		<div class="card flex flex-col items-center px-6 py-10 text-center">
			<div class="mb-3 flex size-11 items-center justify-center rounded-full bg-surface-2 text-muted"><Icon name="download" /></div>
			<p class="font-medium">Keine laufenden Downloads</p>
			<p class="mt-1 text-sm text-muted">Füge oben eine URL ein, um loszulegen.</p>
		</div>
	{:else}
		<div class="space-y-2">
			{#each queue as d (d.id)}<DownloadCard {d} />{/each}
		</div>
	{/if}
</section>

{#if recent.length}
	<section class="mx-auto mt-10 max-w-3xl">
		<div class="mb-3 flex items-center">
			<h2 class="text-lg font-semibold">Zuletzt fertig</h2>
			<a href="/library" class="ml-auto text-sm font-medium text-accent hover:underline">Zur Bibliothek</a>
		</div>
		<div class="space-y-2">
			{#each recent as d (d.id)}
				<div class="card flex items-center gap-3 p-2.5">
					<Thumb src={d.thumbnail} mode={d.mode} class="aspect-video w-20" />
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium">{d.title}</p>
						<p class="truncate text-xs text-muted">{d.filename}</p>
					</div>
					<a class="btn-icon" href="/api/downloads/{d.id}/file" title="Herunterladen"><Icon name="download" /></a>
				</div>
			{/each}
		</div>
	</section>
{/if}
