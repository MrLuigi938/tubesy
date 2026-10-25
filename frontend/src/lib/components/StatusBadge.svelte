<script lang="ts">
	import { t } from '#lib/i18n.svelte.ts';
	import type { DownloadStatus } from '#lib/types.ts';

	let { status }: { status: DownloadStatus } = $props();
	const map: Record<DownloadStatus, [string, string]> = {
		queued: ['Wartet', 'bg-surface-2 text-muted'],
		downloading: ['Lädt', 'bg-info-soft text-info'],
		processing: ['Verarbeitung', 'bg-warn-soft text-warn'],
		completed: ['Fertig', 'bg-ok-soft text-ok'],
		failed: ['Fehler', 'bg-danger-soft text-danger'],
		canceled: ['Abgebrochen', 'bg-surface-2 text-muted']
	};
</script>

<span class="badge {map[status][1]}">{t(map[status][0])}</span>
