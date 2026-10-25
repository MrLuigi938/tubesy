<script lang="ts">
	import { i18n, setLang, t } from '#lib/i18n.svelte.ts';

	let { class: cls = '' }: { class?: string } = $props();
</script>

<div class="inline-flex overflow-hidden rounded-lg border border-border text-xs {cls}" role="group" aria-label={t('Sprache')}>
	{#each [['de', 'Deutsch'], ['en', 'English']] as [code, name] (code)}
		<button
			type="button"
			class="px-2.5 py-1 font-medium transition-colors {i18n.lang === code ? 'bg-accent text-white' : 'text-muted hover:text-text'}"
			aria-pressed={i18n.lang === code}
			onclick={() => setLang(code)}>{name}</button
		>
	{/each}
</div>
