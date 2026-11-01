<script lang="ts">
	import Icon from './Icon.svelte';

	let {
		src,
		mode = 'video',
		masked = false,
		class: cls = ''
	}: { src: string | null; mode?: 'video' | 'audio'; masked?: boolean; class?: string } = $props();
	let broken = $state(false);
</script>

<div class="relative shrink-0 overflow-hidden rounded-lg bg-surface-2 {cls}">
	{#if masked}
		<!-- A hidden video: frosted surface instead of the thumbnail, which the server withholds. -->
		<div class="flex size-full items-center justify-center bg-gradient-to-br from-surface-2 via-border to-surface-2 text-muted">
			<div class="absolute inset-0 backdrop-blur-xl"></div>
			<Icon name="eye-off" size={22} class="relative" />
		</div>
	{:else if src && !broken}
		<img {src} alt="" loading="lazy" referrerpolicy="no-referrer" class="size-full object-cover" onerror={() => (broken = true)} />
	{:else}
		<div class="flex size-full items-center justify-center text-muted">
			<Icon name={mode === 'audio' ? 'music' : 'film'} size={22} />
		</div>
	{/if}
</div>
