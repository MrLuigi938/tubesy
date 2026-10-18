<script lang="ts">
	import { api, errorText } from '#lib/api.ts';
	import Icon from '#lib/components/Icon.svelte';
	import { bytes } from '#lib/format.ts';
	import { toast } from '#lib/toast.svelte.ts';
	import { onMount } from 'svelte';

	interface Settings {
		registration_mode: string;
		max_concurrent_downloads: number;
		max_concurrent_per_user: number;
		default_quota_gb: number | null;
		session_days: number;
		max_playlist_items: number;
	}
	interface System {
		ytdlp_version: string;
		ffmpeg: boolean;
		deno: boolean;
		download_dir: string;
		disk_total: number;
		disk_free: number;
		users: number;
		downloads_by_status: Record<string, number>;
	}

	let s = $state<Settings | null>(null);
	let quota = $state('');
	let sys = $state<System | null>(null);
	let saving = $state(false);
	let updating = $state(false);

	onMount(async () => {
		s = await api.get<Settings>('/api/admin/settings');
		quota = s.default_quota_gb != null ? String(s.default_quota_gb) : '';
		sys = await api.get<System>('/api/admin/system');
	});

	async function save(e: SubmitEvent) {
		e.preventDefault();
		if (!s) return;
		saving = true;
		try {
			s = await api.put<Settings>('/api/admin/settings', {
				...s,
				default_quota_gb: quota === '' ? null : Number(quota),
				clear_default_quota: quota === ''
			});
			toast('Einstellungen gespeichert');
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			saving = false;
		}
	}

	async function updateYtdlp() {
		updating = true;
		try {
			const res = await api.post<{ ytdlp_version: string }>('/api/admin/ytdlp/update');
			if (sys) sys.ytdlp_version = res.ytdlp_version;
			toast(`yt-dlp ist auf Version ${res.ytdlp_version}`);
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			updating = false;
		}
	}
</script>

<div class="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
	<form class="card p-5" onsubmit={save}>
		<h2 class="font-semibold">Einstellungen</h2>
		{#if s}
			<div class="mt-4 grid gap-4 sm:grid-cols-2">
				<label><span class="label">Gleichzeitige Downloads (gesamt)</span><input class="input" type="number" min="1" max="20" bind:value={s.max_concurrent_downloads} /></label>
				<label><span class="label">Gleichzeitige Downloads pro Benutzer</span><input class="input" type="number" min="1" max="20" bind:value={s.max_concurrent_per_user} /><span class="hint">Verhindert, dass eine große Playlist alle anderen blockiert.</span></label>
				<label><span class="label">Max. Einträge pro Playlist</span><input class="input" type="number" min="1" max="5000" bind:value={s.max_playlist_items} /></label>
				<label><span class="label">Standard-Kontingent neuer Benutzer (GB)</span><input class="input" type="number" min="0" step="0.5" bind:value={quota} placeholder="unbegrenzt" /></label>
				<label><span class="label">Anmeldung gültig (Tage)</span><input class="input" type="number" min="1" max="365" bind:value={s.session_days} /></label>
			</div>
			<button class="btn-primary mt-5" disabled={saving}>{#if saving}<Icon name="loader" size={16} />{/if}Speichern</button>
		{/if}
	</form>

	<section class="card self-start p-5">
		<h2 class="font-semibold">System</h2>
		{#if sys}
			{@const usedPct = ((sys.disk_total - sys.disk_free) / sys.disk_total) * 100}
			<dl class="mt-4 space-y-3 text-sm">
				<div class="flex items-center justify-between gap-2">
					<dt class="text-muted">yt-dlp</dt>
					<dd class="flex items-center gap-2 font-mono text-xs">
						{sys.ytdlp_version}
						<button type="button" class="btn-secondary h-7 px-2 py-0.5 text-xs" disabled={updating} onclick={updateYtdlp}>
							{#if updating}<Icon name="loader" size={12} />{:else}<Icon name="retry" size={12} />{/if}Aktualisieren
						</button>
					</dd>
				</div>
				<div class="flex justify-between"><dt class="text-muted">ffmpeg</dt><dd class={sys.ffmpeg ? 'text-ok' : 'text-danger'}>{sys.ffmpeg ? 'vorhanden' : 'fehlt'}</dd></div>
				<div class="flex justify-between"><dt class="text-muted">Deno (für YouTube)</dt><dd class={sys.deno ? 'text-ok' : 'text-warn'}>{sys.deno ? 'vorhanden' : 'fehlt'}</dd></div>
				<div class="flex justify-between gap-4"><dt class="text-muted">Download-Ordner</dt><dd class="truncate font-mono text-xs">{sys.download_dir}</dd></div>
				<div>
					<div class="flex justify-between"><dt class="text-muted">Speicherplatz</dt><dd class="tabular-nums">{bytes(sys.disk_free)} frei von {bytes(sys.disk_total)}</dd></div>
					<div class="mt-2 h-2 overflow-hidden rounded-full bg-surface-2"><div class="h-full rounded-full {usedPct > 90 ? 'bg-danger' : 'bg-info'}" style="width: {usedPct}%"></div></div>
				</div>
				<div class="flex justify-between"><dt class="text-muted">Benutzer</dt><dd>{sys.users}</dd></div>
				<div class="flex justify-between"><dt class="text-muted">Downloads</dt><dd class="text-right">{Object.entries(sys.downloads_by_status).map(([k, v]) => `${v} ${k}`).join(' · ') || '–'}</dd></div>
			</dl>
		{:else}
			<div class="flex justify-center py-8 text-muted"><Icon name="loader" /></div>
		{/if}
	</section>
</div>
