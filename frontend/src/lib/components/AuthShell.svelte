<script lang="ts">
	import type { Snippet } from 'svelte';

	let { title, subtitle, children }: { title: string; subtitle?: string; children: Snippet } = $props();
</script>

<div class="flex min-h-screen items-center justify-center px-4 py-10">
	<div class="w-full max-w-sm">
		<div class="mb-6 flex flex-col items-center text-center">
			<img src="/favicon.svg" alt="" class="mb-4 size-12" />
			<h1 class="text-xl font-semibold">{title}</h1>
			{#if subtitle}<p class="mt-1 text-sm text-muted">{subtitle}</p>{/if}
		</div>
		<div class="card p-6 shadow-sm">
			{@render children()}
		</div>
	</div>
</div>
