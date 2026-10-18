<script lang="ts">
	import { toasts } from '#lib/toast.svelte.ts';
	import Icon from './Icon.svelte';

	const styles = {
		ok: 'border-ok/40 text-ok',
		error: 'border-danger/40 text-danger',
		info: 'border-info/40 text-info'
	};
	const icons = { ok: 'check', error: 'alert', info: 'download' } as const;
</script>

<div class="pointer-events-none fixed inset-x-4 bottom-4 z-50 flex flex-col items-end gap-2 sm:left-auto" aria-live="polite">
	{#each toasts as t (t.id)}
		<div class="card pointer-events-auto flex max-w-sm items-start gap-2.5 px-4 py-3 text-sm shadow-lg {styles[t.kind]}">
			<Icon name={icons[t.kind]} class="mt-0.5" />
			<span class="text-text">{t.text}</span>
		</div>
	{/each}
</div>
