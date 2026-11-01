<script lang="ts">
	import { t, tServer } from '#lib/i18n.svelte.ts';
	import { page } from '$app/state';
	import { api, errorText } from '#lib/api.ts';
	import Icon from '#lib/components/Icon.svelte';
	import Modal from '#lib/components/Modal.svelte';
	import Thumb from '#lib/components/Thumb.svelte';
	import { relative } from '#lib/format.ts';
	import { session } from '#lib/session.svelte.ts';
	import { toast } from '#lib/toast.svelte.ts';
	import type { Preset, Subscription } from '#lib/types.ts';
	import { onMount } from 'svelte';

	const INTERVALS: [number, string][] = [
		[1, 'stündlich'],
		[3, 'alle 3 Stunden'],
		[6, 'alle 6 Stunden'],
		[12, 'alle 12 Stunden'],
		[24, 'täglich'],
		[72, 'alle 3 Tage'],
		[168, 'wöchentlich']
	];

	let subs = $state<Subscription[]>([]);
	let presets = $state<Preset[]>([]);
	let loading = $state(true);
	let busy = $state<number | 'new' | null>(null);

	// New subscription (a link from "Subscribe" on the download page fills in the URL).
	let url = $state(page.url.searchParams.get('url') ?? '');
	let presetId = $state<number | null>(null);
	let interval = $state(6);
	let ownFolder = $state(true);
	let hidden = $state(false);
	let backfill = $state(0);

	let editing = $state<Subscription | null>(null);
	let editOpen = $state(false);
	let deleting = $state<Subscription | null>(null);
	let deleteOpen = $state(false);

	onMount(async () => {
		try {
			const [s, p] = await Promise.all([
				api.get<Subscription[]>('/api/subscriptions'),
				api.get<{ items: Preset[] }>('/api/presets')
			]);
			subs = s;
			presets = p.items;
			presetId = presets.find((x) => x.id === session.user?.default_preset_id)?.id ?? presets[0]?.id ?? null;
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			loading = false;
		}
	});

	const intervalLabel = (h: number) => t(INTERVALS.find(([v]) => v === h)?.[1] ?? '{n} h', { n: h });

	async function create(e: SubmitEvent) {
		e.preventDefault();
		busy = 'new';
		try {
			const sub = await api.post<Subscription & { queued: number }>('/api/subscriptions', {
				url: url.trim(),
				preset_id: presetId,
				interval_hours: interval,
				own_folder: ownFolder,
				hidden,
				backfill
			});
			subs = [sub, ...subs];
			url = '';
			toast(sub.queued ? t('Abo angelegt – {n} Videos werden geladen', { n: sub.queued }) : t('Abo angelegt – ab jetzt kommen neue Videos von selbst'));
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			busy = null;
		}
	}

	async function act(sub: Subscription, fn: () => Promise<Subscription>, ok?: (s: Subscription) => string) {
		busy = sub.id;
		try {
			const next = await fn();
			subs = subs.map((s) => (s.id === sub.id ? next : s));
			if (ok) toast(ok(next));
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			busy = null;
		}
	}

	const checkNow = (sub: Subscription) =>
		act(sub, () => api.post<Subscription & { queued: number }>(`/api/subscriptions/${sub.id}/check`), (s) =>
			(s as Subscription & { queued: number }).queued ? t('{n} neue Videos eingereiht', { n: (s as Subscription & { queued: number }).queued }) : t('Nichts Neues')
		);
	const toggle = (sub: Subscription) => act(sub, () => api.patch<Subscription>(`/api/subscriptions/${sub.id}`, { enabled: !sub.enabled }));

	function openEdit(sub: Subscription) {
		editing = { ...sub };
		editOpen = true;
	}

	async function saveEdit() {
		if (!editing) return;
		const e = editing;
		await act(e, () =>
			api.patch<Subscription>(`/api/subscriptions/${e.id}`, {
				preset_id: e.preset_id,
				interval_hours: e.interval_hours,
				own_folder: e.own_folder,
				hidden: e.hidden
			}), () => t('Gespeichert')
		);
		editOpen = false;
	}

	async function confirmDelete() {
		if (!deleting) return;
		try {
			await api.del(`/api/subscriptions/${deleting.id}`);
			subs = subs.filter((s) => s.id !== deleting!.id);
			deleteOpen = false;
			toast(t('Abo beendet'));
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}
</script>

<div class="mb-6">
	<h1 class="text-2xl font-semibold tracking-tight">{t('Abos')}</h1>
	<p class="mt-1 text-sm text-muted">{t('Kanäle und Playlists, deren neue Videos Tubesy von selbst herunterlädt.')}</p>
</div>

<form class="card p-5" onsubmit={create}>
	<h2 class="font-semibold">{t('Neues Abo')}</h2>
	<div class="mt-4 flex flex-col gap-2 sm:flex-row">
		<div class="relative flex-1">
			<Icon name="rss" size={16} class="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted" />
			<input class="input pl-9" type="url" required bind:value={url} placeholder="https://www.youtube.com/@kanal" />
		</div>
		<button class="btn-primary" disabled={busy === 'new' || !url.trim()}>
			{#if busy === 'new'}<Icon name="loader" size={16} />{t('Wird geprüft…')}{:else}<Icon name="plus" size={16} />{t('Abonnieren')}{/if}
		</button>
	</div>
	<div class="mt-4 grid gap-3 sm:grid-cols-3">
		<label><span class="label text-xs">{t('Preset')}</span>
			<select class="input" bind:value={presetId}>{#each presets as p (p.id)}<option value={p.id}>{p.name}</option>{/each}</select>
		</label>
		<label><span class="label text-xs">{t('Nach neuen Videos sehen')}</span>
			<select class="input" bind:value={interval}>{#each INTERVALS as [h, label] (h)}<option value={h}>{t(label)}</option>{/each}</select>
		</label>
		<label><span class="label text-xs">{t('Gleich herunterladen')}</span>
			<select class="input" bind:value={backfill}>
				<option value={0}>{t('nichts – nur neue Videos')}</option>
				{#each [3, 5, 10, 25] as n (n)}<option value={n}>{t('die neuesten {n}', { n })}</option>{/each}
			</select>
		</label>
	</div>
	<div class="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted">
		<label class="flex items-center gap-2"><input type="checkbox" bind:checked={ownFolder} /> {t('Eigener Ordner')}</label>
		<label class="flex items-center gap-2"><input type="checkbox" bind:checked={hidden} /> <Icon name="eye-off" size={14} />{t('Ausblenden')}</label>
	</div>
	<p class="mt-3 text-xs text-muted">{t('Tubesy merkt sich jedes Video, das es schon kennt – auch gelöschte werden nicht noch einmal geladen.')}</p>
</form>

<section class="mt-8">
	{#if loading}
		<div class="flex justify-center py-12 text-muted"><Icon name="loader" /></div>
	{:else if !subs.length}
		<div class="card flex flex-col items-center px-6 py-12 text-center">
			<div class="mb-3 flex size-11 items-center justify-center rounded-full bg-surface-2 text-muted"><Icon name="rss" /></div>
			<p class="font-medium">{t('Noch keine Abos')}</p>
			<p class="mt-1 text-sm text-muted">{t('Füge oben einen Kanal oder eine Playlist hinzu.')}</p>
		</div>
	{:else}
		<div class="space-y-3">
			{#each subs as sub (sub.id)}
				<article class="card flex flex-col gap-3 p-3 sm:flex-row {sub.enabled ? '' : 'opacity-60'}">
					<Thumb src={sub.hidden ? null : sub.thumbnail} masked={sub.hidden} class="aspect-video w-full self-start sm:w-40" />
					<div class="min-w-0 flex-1">
						<div class="flex items-start gap-2">
							<div class="min-w-0 flex-1">
								<p class="truncate font-medium">{sub.title}</p>
								<a class="block truncate text-xs text-muted hover:text-accent" href={sub.url} target="_blank" rel="noopener noreferrer">{sub.url}</a>
							</div>
							{#if !sub.enabled}<span class="badge bg-surface-2 text-muted">{t('Pausiert')}</span>{/if}
							{#if sub.hidden}<span class="badge bg-surface-2 text-muted"><Icon name="eye-off" size={12} />{t('Ausgeblendet')}</span>{/if}
						</div>
						<p class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
							<span>{intervalLabel(sub.interval_hours)}</span>
							<span>{sub.preset_name ?? t('Standard-Preset')}</span>
							<span>{t('{n} Videos geladen', { n: sub.downloads })}</span>
							<span>{sub.last_checked_at ? t('zuletzt geprüft {when}', { when: relative(sub.last_checked_at) }) : t('noch nicht geprüft')}</span>
						</p>
						{#if sub.last_error}<p class="mt-1.5 line-clamp-2 text-xs text-danger">{tServer(sub.last_error)}</p>{/if}
						<div class="mt-2 flex flex-wrap gap-1">
							<button class="btn-ghost h-8 px-2.5 py-1 text-xs" disabled={busy === sub.id} onclick={() => checkNow(sub)}>
								{#if busy === sub.id}<Icon name="loader" size={14} />{:else}<Icon name="retry" size={14} />{/if}{t('Jetzt prüfen')}
							</button>
							<button class="btn-ghost h-8 px-2.5 py-1 text-xs" onclick={() => toggle(sub)}>{sub.enabled ? t('Pausieren') : t('Fortsetzen')}</button>
							<button class="btn-ghost h-8 px-2.5 py-1 text-xs" onclick={() => openEdit(sub)}><Icon name="edit" size={14} />{t('Bearbeiten')}</button>
							<button class="btn-ghost h-8 px-2.5 py-1 text-xs hover:text-danger" onclick={() => ((deleting = sub), (deleteOpen = true))}><Icon name="trash" size={14} />{t('Beenden')}</button>
						</div>
					</div>
				</article>
			{/each}
		</div>
	{/if}
</section>

<Modal bind:open={editOpen} title={t('Abo bearbeiten')}>
	{#if editing}
		<div class="space-y-4">
			<label class="block"><span class="label">{t('Preset')}</span>
				<select class="input" bind:value={editing.preset_id}>
					<option value={null}>{t('Standard-Preset')}</option>
					{#each presets as p (p.id)}<option value={p.id}>{p.name}</option>{/each}
				</select>
			</label>
			<label class="block"><span class="label">{t('Nach neuen Videos sehen')}</span>
				<select class="input" bind:value={editing.interval_hours}>{#each INTERVALS as [h, label] (h)}<option value={h}>{t(label)}</option>{/each}</select>
			</label>
			<label class="flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={editing.own_folder} /> {t('Eigener Ordner')}</label>
			<label class="flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={editing.hidden} /> {t('Neue Videos ausblenden')}</label>
		</div>
	{/if}
	{#snippet footer()}
		<button class="btn-ghost" onclick={() => (editOpen = false)}>{t('Abbrechen')}</button>
		<button class="btn-primary" onclick={saveEdit}>{t('Speichern')}</button>
	{/snippet}
</Modal>

<Modal bind:open={deleteOpen} title={t('Abo beenden?')} size="sm">
	<p class="text-sm">{t('Tubesy sucht bei „{name}“ nicht mehr nach neuen Videos. Bereits geladene Videos bleiben in der Bibliothek.', { name: deleting?.title ?? '' })}</p>
	{#snippet footer()}
		<button class="btn-ghost" onclick={() => (deleteOpen = false)}>{t('Abbrechen')}</button>
		<button class="btn-danger" onclick={confirmDelete}>{t('Beenden')}</button>
	{/snippet}
</Modal>
