<script lang="ts">
	import { t } from '#lib/i18n.svelte.ts';
	import type { UpdateInfo } from '#lib/appinfo.svelte.ts';

	// The quiet signature under the login box and at the bottom of every page.
	// Inside the app it also names the version and, when the server found one,
	// links a newer release.
	let { app = false, version = '', update = null }: { app?: boolean; version?: string; update?: UpdateInfo | null } = $props();
	const shownVersion = $derived(version && version !== 'dev' ? version : '');
</script>

<footer class="flex flex-wrap items-center justify-center gap-2 px-4 pt-7 pb-5 text-center text-sm text-muted">
	<span class="rounded-full px-3 py-1">
		{#if app}<b class="font-semibold text-text">Tubesy</b>{#if shownVersion}<span class="ml-1.5 tabular-nums">{shownVersion}</span>{/if}{' · '}{/if}{t('Erdacht mit')}
		<span class="text-[#e5484d]" aria-label={t('Liebe')}>♥</span> {t('von')}
		<a class="credit-link" href="https://github.com/MrLuigi938" target="_blank" rel="noopener noreferrer">Luis Blum</a> · {t('gebaut mit KI')} ✨
	</span>
	{#if app && update}
		<a
			class="rounded-full border border-accent/45 bg-accent/10 px-3 py-0.5 text-[13px] font-semibold text-accent hover:border-accent"
			href={update.url}
			target="_blank"
			rel="noopener noreferrer"
			title={t('Was ist neu in {v}?', { v: update.version })}
		>
			⬆ {t('Version {v} ist da', { v: update.version })}
		</a>
	{/if}
</footer>

<style>
	.credit-link {
		color: inherit;
		font-weight: 600;
		text-decoration: none;
		border-bottom: 1px dotted currentColor;
	}
	.credit-link:hover {
		color: var(--accent);
		border-bottom-color: var(--accent);
	}
</style>
