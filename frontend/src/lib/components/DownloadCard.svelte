<script lang="ts">
	import { t, tServer } from '#lib/i18n.svelte.ts';
	import { api, errorText } from '#lib/api.ts';
	import { bytes, duration, eta, relative } from '#lib/format.ts';
	import { toast } from '#lib/toast.svelte.ts';
	import type { Download } from '#lib/types.ts';
	import Icon from './Icon.svelte';
	import StatusBadge from './StatusBadge.svelte';
	import Thumb from './Thumb.svelte';

	let { d, showUser = false }: { d: Download; showUser?: boolean } = $props();
	let busy = $state(false);

	const active = $derived(d.status === 'downloading' || d.status === 'processing');

	async function run(action: () => Promise<unknown>) {
		busy = true;
		try {
			await action();
		} catch (e) {
			toast(errorText(e), 'error');
		} finally {
			busy = false;
		}
	}
</script>

<div class="card flex gap-3 p-3">
	<Thumb src={d.thumbnail} mode={d.mode} class="aspect-video w-28 self-start sm:w-36" />
	<div class="min-w-0 flex-1">
		<div class="flex items-start justify-between gap-2">
			<div class="min-w-0">
				<p class="truncate font-medium" title={d.title ?? d.url}>{d.title ?? d.url}</p>
				<p class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted">
					{#if showUser && d.username}<span class="font-medium text-text">@{d.username}</span>{/if}
					{#if d.uploader}<span class="truncate">{d.uploader}</span>{/if}
					{#if d.duration}<span>{duration(d.duration)}</span>{/if}
					{#if d.preset_name}<span>{d.preset_name}</span>{/if}
					{#if d.playlist_title}<span class="inline-flex items-center gap-1"><Icon name="folder" size={12} />{d.playlist_title}</span>{/if}
				</p>
			</div>
			<div class="flex shrink-0 items-center gap-0.5">
				{#if d.status === 'queued' || active}
					<button class="btn-icon" title={t('Abbrechen')} disabled={busy} onclick={() => run(() => api.post(`/api/downloads/${d.id}/cancel`))}>
						<Icon name="x" />
					</button>
				{:else if d.status === 'failed' || d.status === 'canceled'}
					<button class="btn-icon" title={t('Erneut versuchen')} disabled={busy} onclick={() => run(() => api.post(`/api/downloads/${d.id}/retry`))}>
						<Icon name="retry" />
					</button>
					<button class="btn-icon" title={t('Aus Liste entfernen')} disabled={busy} onclick={() => run(() => api.del(`/api/downloads/${d.id}?delete_file=false`))}>
						<Icon name="trash" />
					</button>
				{/if}
			</div>
		</div>

		<div class="mt-2 flex items-center gap-2 text-xs">
			<StatusBadge status={d.status} />
			{#if active}
				<span class="text-muted">{tServer(d.stage ?? '')}</span>
				<span class="ml-auto tabular-nums text-muted">
					{#if d.status === 'downloading'}
						{d.progress.toFixed(1)} %
						{#if d.speed} · {bytes(d.speed)}/s{/if}
						{#if d.eta} · {t('noch {time}', { time: eta(d.eta) })}{/if}
					{/if}
				</span>
			{:else if d.status === 'queued'}
				<span class="text-muted">{t('hinzugefügt {when}', { when: relative(d.created_at) })}</span>
			{:else if d.status === 'completed'}
				<span class="text-muted">{bytes(d.file_size)} · {relative(d.finished_at)}</span>
			{/if}
		</div>

		{#if active}
			<div class="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-2">
				<div
					class="h-full rounded-full transition-[width] duration-500 {d.status === 'processing' ? 'animate-pulse bg-warn' : 'bg-accent'}"
					style="width: {d.status === 'processing' ? 100 : d.progress}%"
				></div>
			</div>
		{/if}
		{#if d.status === 'failed' && d.error}
			<p class="mt-2 line-clamp-2 text-xs break-words text-danger" title={tServer(d.error)}>{tServer(d.error)}</p>
		{/if}
	</div>
</div>
