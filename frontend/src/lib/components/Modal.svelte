<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	let {
		open = $bindable(false),
		title,
		size = 'md',
		children,
		footer
	}: { open: boolean; title: string; size?: 'sm' | 'md' | 'lg' | 'xl'; children: Snippet; footer?: Snippet } = $props();

	let dialog: HTMLDialogElement | undefined = $state();
	const widths = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-4xl' };

	$effect(() => {
		if (!dialog) return;
		if (open && !dialog.open) dialog.showModal();
		if (!open && dialog.open) dialog.close();
	});
</script>

<dialog
	bind:this={dialog}
	onclose={() => (open = false)}
	onclick={(e) => e.target === dialog && (open = false)}
	class="m-auto w-[calc(100%-2rem)] {widths[size]} rounded-xl border border-border bg-surface p-0 text-text shadow-2xl backdrop:bg-black/60 backdrop:backdrop-blur-sm"
>
	{#if open}
		<div class="flex items-center justify-between border-b border-border px-5 py-3.5">
			<h2 class="text-base font-semibold">{title}</h2>
			<button class="btn-icon -mr-2" onclick={() => (open = false)} aria-label="Schließen"><Icon name="x" /></button>
		</div>
		<div class="max-h-[70vh] overflow-y-auto px-5 py-4">{@render children()}</div>
		{#if footer}
			<div class="flex flex-wrap justify-end gap-2 border-t border-border px-5 py-3">{@render footer()}</div>
		{/if}
	{/if}
</dialog>
