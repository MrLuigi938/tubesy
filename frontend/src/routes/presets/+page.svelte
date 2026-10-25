<script lang="ts">
	import { t } from '#lib/i18n.svelte.ts';
	import { api, errorText } from '#lib/api.ts';
	import Icon from '#lib/components/Icon.svelte';
	import Modal from '#lib/components/Modal.svelte';
	import PresetForm from '#lib/components/PresetForm.svelte';
	import { session } from '#lib/session.svelte.ts';
	import { toast } from '#lib/toast.svelte.ts';
	import type { Preset, PresetOptions, User } from '#lib/types.ts';
	import { onMount } from 'svelte';

	let presets = $state<Preset[]>([]);
	let defaults = $state<PresetOptions | null>(null);
	let categories = $state<string[]>([]);
	let editing = $state<{ id: number | null; name: string; options: PresetOptions; is_global: boolean } | null>(null);
	let editorOpen = $state(false);
	let saving = $state(false);

	const isAdmin = $derived(session.user?.role === 'admin');

	async function load() {
		const res = await api.get<{ items: Preset[]; defaults: PresetOptions; sponsorblock_categories: string[] }>('/api/presets');
		presets = res.items;
		defaults = res.defaults;
		categories = res.sponsorblock_categories;
	}
	onMount(load);

	function summary(o: PresetOptions) {
		if (o.mode === 'audio') {
			const fmt = o.audio_format === 'best' ? t('Original-Audio') : o.audio_format.toUpperCase();
			return [fmt, o.audio_quality === 'best' ? t('beste Qualität') : `${o.audio_quality} kbit/s`];
		}
		const parts = [o.quality === 'best' ? t('Beste Auflösung') : t('bis {q}p', { q: o.quality }), o.container === 'any' ? t('Original-Container') : o.container.toUpperCase()];
		if (o.subtitles || o.auto_subtitles) parts.push(t('Untertitel ({langs})', { langs: o.sub_langs }));
		if (o.sponsorblock_remove.length) parts.push('SponsorBlock');
		return parts;
	}

	function create() {
		editing = { id: null, name: '', options: structuredClone($state.snapshot(defaults!)), is_global: false };
		editorOpen = true;
	}

	function edit(p: Preset) {
		editing = { id: p.id, name: p.name, options: structuredClone($state.snapshot(p.options)), is_global: p.is_global };
		editorOpen = true;
	}

	async function save() {
		if (!editing) return;
		saving = true;
		try {
			const body = { name: editing.name, options: editing.options, is_global: editing.is_global };
			if (editing.id) await api.put(`/api/presets/${editing.id}`, body);
			else await api.post('/api/presets', body);
			editorOpen = false;
			toast(t('Preset gespeichert'));
			await load();
		} catch (err) {
			toast(errorText(err), 'error');
		} finally {
			saving = false;
		}
	}

	async function remove(p: Preset) {
		if (!confirm(t('Preset „{name}“ löschen?', { name: p.name }))) return;
		try {
			await api.del(`/api/presets/${p.id}`);
			await load();
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}

	async function makeDefault(p: Preset) {
		try {
			session.user = await api.patch<User>('/api/account', { email: session.user?.email, default_preset_id: p.id });
			toast(t('„{name}“ ist jetzt dein Standard', { name: p.name }));
		} catch (err) {
			toast(errorText(err), 'error');
		}
	}
</script>

<div class="mb-6 flex items-end gap-4">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight">{t('Presets')}</h1>
		<p class="mt-1 text-sm text-muted">{t('Vorlagen für Qualität, Format und Nachbearbeitung.')}</p>
	</div>
	<button class="btn-primary ml-auto" onclick={create} disabled={!defaults}><Icon name="plus" size={16} />{t('Neues Preset')}</button>
</div>

<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
	{#each presets as p (p.id)}
		{@const isDefault = session.user?.default_preset_id === p.id}
		<div class="card flex flex-col p-4 {isDefault ? 'ring-2 ring-accent/50' : ''}">
			<div class="flex items-start gap-3">
				<div class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-surface-2 text-muted">
					<Icon name={p.options.mode === 'audio' ? 'music' : 'film'} />
				</div>
				<div class="min-w-0 flex-1">
					<p class="font-medium">{p.name}</p>
					<div class="mt-1 flex flex-wrap gap-1">
						{#if p.is_global}<span class="badge bg-info-soft text-info">{t('Global')}</span>{/if}
						{#if isDefault}<span class="badge bg-accent-soft text-accent">{t('Standard')}</span>{/if}
					</div>
				</div>
			</div>
			<ul class="mt-3 space-y-0.5 text-sm text-muted">
				{#each summary(p.options) as line, i (i)}<li>{line}</li>{/each}
			</ul>
			<div class="mt-auto flex items-center gap-1 pt-4">
				{#if !isDefault}
					<button class="btn-ghost h-8 px-2.5 py-1 text-xs" onclick={() => makeDefault(p)}><Icon name="star" size={14} />{t('Als Standard')}</button>
				{/if}
				<span class="ml-auto"></span>
				{#if !p.is_global || isAdmin}
					<button class="btn-icon" title={t('Bearbeiten')} onclick={() => edit(p)}><Icon name="edit" size={16} /></button>
					<button class="btn-icon hover:text-danger" title={t('Löschen')} onclick={() => remove(p)}><Icon name="trash" size={16} /></button>
				{/if}
			</div>
		</div>
	{/each}
</div>

<Modal bind:open={editorOpen} title={editing?.id ? t('Preset bearbeiten') : t('Neues Preset')} size="lg">
	{#if editing}
		<label class="mb-5 block">
			<span class="label">{t('Name')}</span>
			<input class="input" bind:value={editing.name} maxlength="64" placeholder={t('z. B. Musik für unterwegs')} />
		</label>
		<PresetForm bind:options={editing.options} {categories} />
		{#if isAdmin && !editing.id}
			<label class="mt-5 flex items-center gap-2 text-sm">
				<input type="checkbox" bind:checked={editing.is_global} /> {t('Für alle Benutzer verfügbar (global)')}
			</label>
		{/if}
	{/if}
	{#snippet footer()}
		<button class="btn-ghost" onclick={() => (editorOpen = false)}>{t('Abbrechen')}</button>
		<button class="btn-primary" disabled={saving || !editing?.name.trim()} onclick={save}>
			{#if saving}<Icon name="loader" size={16} />{/if}{t('Speichern')}
		</button>
	{/snippet}
</Modal>
