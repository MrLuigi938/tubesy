<script lang="ts">
	import Icon from './Icon.svelte';

	let { src, mode = 'video', class: cls = '' }: { src: string | null; mode?: 'video' | 'audio'; class?: string } = $props();
	let broken = $state(false);
</script>

<div class="relative shrink-0 overflow-hidden rounded-lg bg-surface-2 {cls}">
	{#if src && !broken}
		<img {src} alt="" loading="lazy" referrerpolicy="no-referrer" class="size-full object-cover" onerror={() => (broken = true)} />
	{:else}
		<div class="flex size-full items-center justify-center text-muted">
			<Icon name={mode === 'audio' ? 'music' : 'film'} size={22} />
		</div>
	{/if}
</div>
