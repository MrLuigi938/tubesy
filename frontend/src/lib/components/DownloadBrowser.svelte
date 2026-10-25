<script lang="ts">
	import { t } from '#lib/i18n.svelte.ts';
	import { api, errorText } from '#lib/api.ts';
	import { bytes, date, duration } from '#lib/format.ts';
	import { applyEvent, subscribe } from '#lib/live.svelte.ts';
	import { toast } from '#lib/toast.svelte.ts';
	import type { Download, User } from '#lib/types.ts';
	import { onMount } from 'svelte';
	import Icon from './Icon.svelte';
	import Modal from './Modal.svelte';
	import StatusBadge from './StatusBadge.svelte';
	import Thumb from './Thumb.svelte';

	let {
		admin = false,
		standalone = false,
		playlist = null
	}: { admin?: boolean; standalone?: boolean; playlist?: string | null } = $props();

	const PAGE = 48;
	let items = $state<Download[]>([]);
	let total = $state(0);
	let q = $state('');
	let userId = $state<number | ''>('');
	let users = $state<User[]>([]);
	let loading = $state(true);
	let playing = $state<Download | null>(null);
	let playerOpen = $state(false);
	let deleting = $state<Download | null>(null);
	let deleteOpen = $state(false);
	let deleteFile = $state(true);
	let searchTimer: ReturnType<typeof setTimeout>;

	const view = $derived(admin ? 'all' : 'library');

	function query(offset: number) {
		const params = new URLSearchParams({ view, limit: String(PAGE), offset: String(offset) });
		if (q.trim()) params.set('q', q.trim());
		if (admin) params.set('scope', 'all');
		if (playlist != null) params.set('playlist', playlist);
		else if (standalone) params.set('standalone', 'true');
		if (admin && userId !== '') params.set('user_id', String(userId));
		return `/api/downloads?${params}`;
	}

	async function load(append = false) {
		loading = true;
		try {
			const res = await api.get<{ total: number; items: Download[] }>(query(append ? items.length : 0));
			items = append ? [...items, ...res.items] : res.items;
			total = res.total;
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		load();
		if (admin) api.get<User[]>('/api/admin/users').then((u) => (users = u));
		return subscribe((e) => {
			const accept = (d: Download) => {
				if (admin) return userId === '' || d.user_id === userId;
				if (d.status !== 'completed') return false;
				if (playlist != null) return d.playlist_title === playlist;
				return !standalone || d.playlist_title == null;
			};
			const before = items.length;
			const next = applyEvent(items, e, accept);
			// New completions belong at the top of the library.
			if (next.length > before && e.event === 'download') items = [e.data, ...items];
			else items = next;
			total += items.length - before;
		});
	});

	function onSearch() {
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => load(), 250);
	}

	function play(d: Download) {
		playing = d;
		playerOpen = true;
	}

	function askDelete(d: Download) {
		deleting = d;
		deleteFile = true;
		deleteOpen = true;
	}

	async function confirmDelete() {
		if (!deleting) return;
		try {
			await api.del(`/api/downloads/${deleting.id}?delete_file=${deleteFile}`);
			toast(deleteFile ? t('Datei gelöscht') : t('Eintrag entfernt'));
			deleteOpen = false;
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}
</script>

<div class="mb-5 flex flex-col gap-2 sm:flex-row">
	<div class="relative flex-1">
		<Icon name="search" size={16} class="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted" />
		<input class="input pl-9" placeholder={playlist != null ? t('In dieser Playlist suchen…') : standalone ? t('Titel oder Kanal suchen…') : t('Titel, Kanal oder Playlist suchen…')} bind:value={q} oninput={onSearch} />
	</div>
	{#if admin}
		<select class="input sm:w-56" bind:value={userId} onchange={() => load()}>
			<option value="">{t('Alle Benutzer')}</option>
			{#each users as u (u.id)}<option value={u.id}>{u.username}</option>{/each}
		</select>
	{/if}
</div>

{#if loading && !items.length}
	<div class="flex justify-center py-16 text-muted"><Icon name="loader" /></div>
{:else if !items.length}
	<div class="card flex flex-col items-center px-6 py-14 text-center">
		<div class="mb-3 flex size-11 items-center justify-center rounded-full bg-surface-2 text-muted"><Icon name="library" /></div>
		<p class="font-medium">{q ? t('Keine Treffer') : standalone ? t('Noch keine einzelnen Videos') : t('Noch keine Downloads')}</p>
		<p class="mt-1 text-sm text-muted">
			{q ? t('Versuche einen anderen Suchbegriff.') : standalone ? t('Videos aus Playlists findest du unter „Playlists“.') : t('Fertige Downloads erscheinen hier.')}
		</p>
	</div>
{:else}
	<p class="mb-3 text-sm text-muted">{total} {total === 1 ? t('Eintrag') : t('Einträge')}</p>
	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each items as d (d.id)}
			<article class="card group flex flex-col overflow-hidden">
				<button
					class="relative block aspect-video w-full bg-surface-2 text-left disabled:cursor-default"
					onclick={() => play(d)}
					disabled={d.status !== 'completed'}
					aria-label={t('Abspielen')}
				>
					<Thumb src={d.thumbnail} mode={d.mode} class="size-full rounded-none" />
					{#if d.status === 'completed'}
						<span class="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition group-hover:bg-black/35 group-hover:opacity-100">
							<span class="flex size-12 items-center justify-center rounded-full bg-white/90 text-black"><Icon name="play" size={20} /></span>
						</span>
					{/if}
					{#if d.duration}
						<span class="absolute right-2 bottom-2 rounded bg-black/75 px-1.5 py-0.5 text-xs font-medium text-white tabular-nums">{duration(d.duration)}</span>
					{/if}
					{#if d.mode === 'audio'}
						<span class="absolute top-2 left-2 rounded bg-black/75 p-1 text-white"><Icon name="music" size={14} /></span>
					{/if}
				</button>
				<div class="flex flex-1 flex-col p-3">
					<p class="line-clamp-2 text-sm font-medium" title={d.title}>
						{#if playlist != null && d.playlist_index}<span class="mr-1 text-muted tabular-nums">{d.playlist_index}.</span>{/if}{d.title}
					</p>
					<p class="mt-1 truncate text-xs text-muted">
						{#if admin && d.username}<span class="font-medium text-text">@{d.username}</span> · {/if}{d.uploader ?? ''}
					</p>
					{#if d.playlist_title && playlist == null}
						<p class="mt-1 flex items-center gap-1 truncate text-xs text-muted"><Icon name="folder" size={12} />{d.playlist_title}</p>
					{/if}
					<div class="mt-auto flex items-center gap-1 pt-3">
						{#if admin}<StatusBadge status={d.status} />{/if}
						<span class="text-xs text-muted">{d.status === 'completed' ? `${bytes(d.file_size)} · ${date(d.finished_at)}` : ''}</span>
						<span class="ml-auto"></span>
						<a class="btn-icon" href={d.url} target="_blank" rel="noopener noreferrer" title={t('Original öffnen')}><Icon name="external" size={16} /></a>
						{#if d.status === 'completed'}
							<a class="btn-icon" href="/api/downloads/{d.id}/file" title={t('Herunterladen')}><Icon name="download" size={16} /></a>
						{/if}
						<button class="btn-icon hover:text-danger" title={t('Löschen')} onclick={() => askDelete(d)} disabled={d.status === 'downloading' || d.status === 'processing'}>
							<Icon name="trash" size={16} />
						</button>
					</div>
				</div>
			</article>
		{/each}
	</div>
	{#if items.length < total}
		<div class="mt-6 flex justify-center">
			<button class="btn-secondary" disabled={loading} onclick={() => load(true)}>
				{#if loading}<Icon name="loader" size={16} />{/if}{t('Mehr laden')}
			</button>
		</div>
	{/if}
{/if}

<Modal bind:open={playerOpen} title={playing?.title ?? ''} size="xl">
	{#if playing}
		{#if playing.mode === 'audio'}
			<div class="flex flex-col items-center gap-4 py-4">
				<Thumb src={playing.thumbnail} mode="audio" class="aspect-video w-64" />
				<audio controls autoplay class="w-full" src="/api/downloads/{playing.id}/file?inline=1"></audio>
			</div>
		{:else}
			<!-- svelte-ignore a11y_media_has_caption -->
			<video controls autoplay playsinline class="aspect-video w-full rounded-lg bg-black" src="/api/downloads/{playing.id}/file?inline=1"></video>
		{/if}
		<p class="mt-3 text-xs text-muted">
			{playing.filename} · {bytes(playing.file_size)}. {t('Nicht jedes Format (z. B. MKV) kann jeder Browser abspielen – herunterladen geht immer.')}
		</p>
	{/if}
	{#snippet footer()}
		{#if playing}<a class="btn-primary" href="/api/downloads/{playing.id}/file"><Icon name="download" size={16} />{t('Herunterladen')}</a>{/if}
	{/snippet}
</Modal>

<Modal bind:open={deleteOpen} title={t('Download löschen?')} size="sm">
	<p class="text-sm">„{deleting?.title}“</p>
	{#if deleting?.status === 'completed'}
		<label class="mt-4 flex items-center gap-2 text-sm">
			<input type="checkbox" bind:checked={deleteFile} /> {t('Datei auch auf dem Speicher löschen')}
		</label>
	{/if}
	{#snippet footer()}
		<button class="btn-ghost" onclick={() => (deleteOpen = false)}>{t('Abbrechen')}</button>
		<button class="btn-danger" onclick={confirmDelete}>{t('Löschen')}</button>
	{/snippet}
</Modal>
