<script lang="ts">
	import { t } from '#lib/i18n.svelte.ts';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api, errorText } from '#lib/api.ts';
	import DownloadBrowser from '#lib/components/DownloadBrowser.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Modal from '#lib/components/Modal.svelte';
	import PlaylistGrid from '#lib/components/PlaylistGrid.svelte';
	import { bytes } from '#lib/format.ts';
	import { toast } from '#lib/toast.svelte.ts';

	type Tab = 'videos' | 'playlists' | 'hidden';
	const TABS: [Tab, string, 'film' | 'list' | 'eye-off'][] = [
		['videos', 'Videos', 'film'],
		['playlists', 'Playlists', 'list'],
		['hidden', 'Ausgeblendet', 'eye-off']
	];

	// Tab and open playlist live in the URL, so reload and the back button work.
	const tab = $derived((TABS.find(([v]) => v === page.url.searchParams.get('tab'))?.[0] ?? 'videos') as Tab);
	const playlist = $derived(page.url.searchParams.get('playlist'));

	let deleteOpen = $state(false);
	let deleteFiles = $state(true);
	let busy = $state(false);

	// Clean up: first choose what, then confirm with the numbers.
	type Scope = 'videos' | 'playlists' | 'all';
	let cleanupOpen = $state(false);
	let cleanupScope = $state<Scope>('all');
	let cleanupFiles = $state(true);
	let cleanupCount = $state<{ videos: number; playlists: number; playlist_videos: number; bytes: number } | null>(null);
	// Bumped to reload the lists after a clean-up.
	let generation = $state(0);

	function navigate(params: Record<string, string>) {
		goto(`/library?${new URLSearchParams(params)}`, { reset: false });
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

	function removePlaylist() {
		if (!playlist) return;
		run(async () => {
			const res = await api.del<{ removed: number }>(
				`/api/playlists?title=${encodeURIComponent(playlist)}&delete_files=${deleteFiles}`
			);
			toast(t('Playlist entfernt ({n} Videos)', { n: res.removed }));
			deleteOpen = false;
			navigate({ tab: 'playlists' });
		});
	}

	function hidePlaylist() {
		if (!playlist) return;
		run(async () => {
			await api.post('/api/playlists/batch', { titles: [playlist], action: 'hide' });
			toast(t('Playlist ausgeblendet'));
			navigate({ tab: 'hidden' });
		});
	}

	function openCleanup() {
		cleanupScope = 'all';
		cleanupFiles = true;
		cleanupCount = null;
		cleanupOpen = true;
	}

	function countCleanup() {
		run(async () => {
			cleanupCount = await api.post('/api/downloads/cleanup', { scope: cleanupScope, dry_run: true });
		});
	}

	function confirmCleanup() {
		run(async () => {
			const res = await api.post<{ removed: number }>('/api/downloads/cleanup', {
				scope: cleanupScope,
				delete_files: cleanupFiles,
				dry_run: false
			});
			toast(t('Aufgeräumt: {n} Einträge gelöscht', { n: res.removed }));
			cleanupOpen = false;
			generation++;
		});
	}

	const nothingToClean = $derived(cleanupCount != null && cleanupCount.videos + cleanupCount.playlist_videos === 0);
</script>

{#if playlist}
	<button class="btn-ghost -ml-3 mb-2" onclick={() => navigate({ tab: 'playlists' })}><Icon name="back" size={16} />{t('Alle Playlists')}</button>
	<div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end">
		<div class="min-w-0 flex-1">
			<p class="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-muted uppercase"><Icon name="folder" size={14} />Playlist</p>
			<h1 class="mt-1 text-2xl font-semibold tracking-tight break-words">{playlist}</h1>
		</div>
		<div class="flex gap-2">
			<a class="btn-primary" href="/api/playlists/zip?title={encodeURIComponent(playlist)}" download>
				<Icon name="download" size={16} />{t('Alle herunterladen (ZIP)')}
			</a>
			<button class="btn-secondary" title={t('Playlist ausblenden')} disabled={busy} onclick={hidePlaylist}>
				<Icon name="eye-off" size={16} />
			</button>
			<button class="btn-secondary hover:text-danger" title={t('Playlist löschen')} onclick={() => ((deleteFiles = true), (deleteOpen = true))}>
				<Icon name="trash" size={16} />
			</button>
		</div>
	</div>
	{#key playlist}<DownloadBrowser {playlist} />{/key}
{:else}
	<div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end">
		<div class="flex-1">
			<h1 class="text-2xl font-semibold tracking-tight">{t('Bibliothek')}</h1>
			<p class="mt-1 text-sm text-muted">{t('Deine fertigen Downloads: direkt im Browser abspielen oder herunterladen.')}</p>
		</div>
		<div class="flex flex-wrap items-center gap-2 self-start sm:self-auto">
			<div class="inline-flex rounded-lg border border-border bg-surface p-0.5" role="tablist">
				{#each TABS as [value, label, icon] (value)}
					<button
						role="tab"
						aria-selected={tab === value}
						class="flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors {tab === value ? 'bg-accent text-white' : 'text-muted hover:text-text'}"
						onclick={() => navigate({ tab: value })}
					>
						<Icon name={icon} size={16} /><span class={value === 'hidden' ? 'hidden sm:inline' : ''}>{t(label)}</span>
					</button>
				{/each}
			</div>
			<button class="btn-secondary" onclick={openCleanup}><Icon name="sparkles" size={16} />{t('Aufräumen…')}</button>
		</div>
	</div>
	{#key generation}
		{#if tab === 'playlists'}
			<PlaylistGrid onselect={(title) => navigate({ tab: 'playlists', playlist: title })} />
		{:else if tab === 'hidden'}
			<DownloadBrowser hidden="only" />
		{:else}
			<DownloadBrowser standalone hidden="exclude" />
		{/if}
	{/key}
{/if}

<Modal bind:open={deleteOpen} title={t('Playlist löschen?')} size="sm">
	<p class="text-sm">{t('Alle Videos der Playlist „{name}“ werden aus der Bibliothek entfernt.', { name: playlist ?? '' })}</p>
	<label class="mt-4 flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={deleteFiles} /> {t('Dateien auch auf dem Speicher löschen')}</label>
	{#snippet footer()}
		<button class="btn-ghost" onclick={() => (deleteOpen = false)}>{t('Abbrechen')}</button>
		<button class="btn-danger" disabled={busy} onclick={removePlaylist}>{t('Löschen')}</button>
	{/snippet}
</Modal>

<Modal bind:open={cleanupOpen} title={t('Aufräumen')} size="sm">
	{#if !cleanupCount}
		<p class="text-sm">{t('Was soll gelöscht werden? Laufende und wartende Downloads bleiben.')}</p>
		<div class="mt-4 space-y-2">
			{#each [['videos', 'Alle einzelnen Videos'], ['playlists', 'Alle Playlists'], ['all', 'Alles (Videos und Playlists)']] as [value, label] (value)}
				<label class="flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm {cleanupScope === value ? 'border-accent bg-accent-soft/40' : 'border-border'}">
					<input type="radio" name="cleanup" checked={cleanupScope === value} onchange={() => (cleanupScope = value as Scope)} />
					{t(label)}
				</label>
			{/each}
		</div>
		<label class="mt-4 flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={cleanupFiles} /> {t('Dateien auch auf dem Speicher löschen')}</label>
		<p class="mt-2 text-xs text-muted">{t('Gilt auch für ausgeblendete Videos. Nur deine eigenen Downloads.')}</p>
	{:else if nothingToClean}
		<p class="text-sm">{t('Hier gibt es nichts aufzuräumen.')}</p>
	{:else}
		<div class="rounded-lg border border-danger/40 bg-danger-soft p-3 text-sm text-danger">
			<p class="font-semibold">
				{t('Wirklich {videos} Videos und {playlists} Playlists ({size}) löschen?', {
					videos: cleanupCount.videos + cleanupCount.playlist_videos,
					playlists: cleanupCount.playlists,
					size: bytes(cleanupCount.bytes)
				})}
			</p>
			<p class="mt-1">{cleanupFiles ? t('Die Dateien werden ebenfalls gelöscht. Das lässt sich nicht rückgängig machen.') : t('Die Dateien bleiben auf dem Speicher, nur die Einträge verschwinden.')}</p>
		</div>
	{/if}
	{#snippet footer()}
		<button class="btn-ghost" onclick={() => (cleanupOpen = false)}>{t('Abbrechen')}</button>
		{#if !cleanupCount}
			<button class="btn-primary" disabled={busy} onclick={countCleanup}>{t('Weiter')}</button>
		{:else if !nothingToClean}
			<button class="btn-ghost" onclick={() => (cleanupCount = null)}>{t('Zurück')}</button>
			<button class="btn-danger" disabled={busy} onclick={confirmCleanup}>{t('Ja, endgültig löschen')}</button>
		{/if}
	{/snippet}
</Modal>
