<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api, errorText } from '#lib/api.ts';
	import DownloadBrowser from '#lib/components/DownloadBrowser.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Modal from '#lib/components/Modal.svelte';
	import PlaylistGrid from '#lib/components/PlaylistGrid.svelte';
	import { toast } from '#lib/toast.svelte.ts';

	// Tab and open playlist live in the URL, so reload and the back button work.
	const tab = $derived(page.url.searchParams.get('tab') === 'playlists' ? 'playlists' : 'videos');
	const playlist = $derived(page.url.searchParams.get('playlist'));

	let deleteOpen = $state(false);
	let deleteFiles = $state(true);

	function navigate(params: Record<string, string>) {
		goto(`/library?${new URLSearchParams(params)}`, { reset: false });
	}

	async function removePlaylist() {
		if (!playlist) return;
		try {
			const res = await api.del<{ removed: number }>(
				`/api/playlists?title=${encodeURIComponent(playlist)}&delete_files=${deleteFiles}`
			);
			toast(`Playlist entfernt (${res.removed} Videos)`);
			deleteOpen = false;
			navigate({ tab: 'playlists' });
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}
</script>

{#if playlist}
	<button class="btn-ghost -ml-3 mb-2" onclick={() => navigate({ tab: 'playlists' })}><Icon name="back" size={16} />Alle Playlists</button>
	<div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end">
		<div class="min-w-0 flex-1">
			<p class="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-muted uppercase"><Icon name="folder" size={14} />Playlist</p>
			<h1 class="mt-1 text-2xl font-semibold tracking-tight break-words">{playlist}</h1>
		</div>
		<div class="flex gap-2">
			<a class="btn-primary" href="/api/playlists/zip?title={encodeURIComponent(playlist)}" download>
				<Icon name="download" size={16} />Alle herunterladen (ZIP)
			</a>
			<button class="btn-secondary hover:text-danger" title="Playlist löschen" onclick={() => ((deleteFiles = true), (deleteOpen = true))}>
				<Icon name="trash" size={16} />
			</button>
		</div>
	</div>
	{#key playlist}<DownloadBrowser {playlist} />{/key}
{:else}
	<div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end">
		<div class="flex-1">
			<h1 class="text-2xl font-semibold tracking-tight">Bibliothek</h1>
			<p class="mt-1 text-sm text-muted">Deine fertigen Downloads: direkt im Browser abspielen oder herunterladen.</p>
		</div>
		<div class="inline-flex self-start rounded-lg border border-border bg-surface p-0.5 sm:self-auto" role="tablist">
			{#each [['videos', 'Videos', 'film'], ['playlists', 'Playlists', 'list']] as [value, label, icon] (value)}
				<button
					role="tab"
					aria-selected={tab === value}
					class="flex items-center gap-2 rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors {tab === value ? 'bg-accent text-white' : 'text-muted hover:text-text'}"
					onclick={() => navigate({ tab: value })}
				>
					<Icon name={icon as 'film' | 'list'} size={16} />{label}
				</button>
			{/each}
		</div>
	</div>
	{#if tab === 'playlists'}
		<PlaylistGrid onselect={(title) => navigate({ tab: 'playlists', playlist: title })} />
	{:else}
		<DownloadBrowser standalone />
	{/if}
{/if}

<Modal bind:open={deleteOpen} title="Playlist löschen?" size="sm">
	<p class="text-sm">Alle Videos der Playlist „{playlist}“ werden aus der Bibliothek entfernt.</p>
	<label class="mt-4 flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={deleteFiles} /> Dateien auch auf dem Speicher löschen</label>
	{#snippet footer()}
		<button class="btn-ghost" onclick={() => (deleteOpen = false)}>Abbrechen</button>
		<button class="btn-danger" onclick={removePlaylist}>Löschen</button>
	{/snippet}
</Modal>
