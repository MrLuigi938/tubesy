<script lang="ts">
	import type { PresetOptions } from '#lib/types.ts';

	let { options = $bindable(), categories }: { options: PresetOptions; categories: string[] } = $props();

	const sbLabels: Record<string, string> = {
		sponsor: 'Sponsor',
		intro: 'Intro',
		outro: 'Outro / Abspann',
		selfpromo: 'Eigenwerbung',
		preview: 'Vorschau / Rückblick',
		filler: 'Füllmaterial',
		interaction: 'Abo-/Like-Aufrufe',
		music_offtopic: 'Musik: Nicht-Musik-Teile'
	};

	function toggleCategory(cat: string, on: boolean) {
		options.sponsorblock_remove = on
			? [...options.sponsorblock_remove, cat]
			: options.sponsorblock_remove.filter((c) => c !== cat);
	}
</script>

<div class="space-y-5">
	<div>
		<span class="label">Typ</span>
		<div class="inline-flex rounded-lg border border-border p-0.5">
			{#each [['video', 'Video'], ['audio', 'Nur Audio']] as [value, label] (value)}
				<button
					type="button"
					class="rounded-md px-4 py-1.5 text-sm font-medium {options.mode === value ? 'bg-accent text-white' : 'text-muted hover:text-text'}"
					onclick={() => (options.mode = value as 'video' | 'audio')}>{label}</button
				>
			{/each}
		</div>
	</div>

	{#if options.mode === 'video'}
		<div class="grid gap-4 sm:grid-cols-2">
			<label>
				<span class="label">Maximale Auflösung</span>
				<select class="input" bind:value={options.quality}>
					<option value="best">Beste verfügbare</option>
					<option value="2160">2160p (4K)</option>
					<option value="1440">1440p</option>
					<option value="1080">1080p</option>
					<option value="720">720p</option>
					<option value="480">480p</option>
					<option value="360">360p</option>
				</select>
			</label>
			<label>
				<span class="label">Container</span>
				<select class="input" bind:value={options.container}>
					<option value="mp4">MP4 (überall abspielbar)</option>
					<option value="mkv">MKV</option>
					<option value="webm">WebM</option>
					<option value="any">Original beibehalten</option>
				</select>
			</label>
		</div>
		<fieldset class="space-y-2">
			<legend class="label">Untertitel</legend>
			<label class="flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={options.subtitles} /> Untertitel einbetten</label>
			<label class="flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={options.auto_subtitles} /> Automatisch erzeugte Untertitel einbeziehen</label>
			{#if options.subtitles || options.auto_subtitles}
				<label class="block pt-1">
					<input class="input" bind:value={options.sub_langs} placeholder="de,en" />
					<span class="hint">Sprachcodes, durch Komma getrennt. <code>all</code> für alle, <code>de.*</code> für Varianten.</span>
				</label>
			{/if}
		</fieldset>
	{:else}
		<div class="grid gap-4 sm:grid-cols-2">
			<label>
				<span class="label">Format</span>
				<select class="input" bind:value={options.audio_format}>
					<option value="mp3">MP3</option>
					<option value="m4a">M4A (AAC)</option>
					<option value="opus">Opus</option>
					<option value="flac">FLAC</option>
					<option value="wav">WAV</option>
					<option value="best">Original (ohne Umwandlung)</option>
				</select>
			</label>
			<label>
				<span class="label">Qualität</span>
				<select class="input" bind:value={options.audio_quality}>
					<option value="best">Beste</option>
					<option value="320">320 kbit/s</option>
					<option value="256">256 kbit/s</option>
					<option value="192">192 kbit/s</option>
					<option value="128">128 kbit/s</option>
				</select>
			</label>
		</div>
	{/if}

	<fieldset class="space-y-2">
		<legend class="label">Einbetten</legend>
		<label class="flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={options.embed_thumbnail} /> Vorschaubild</label>
		<label class="flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={options.embed_metadata} /> Metadaten (Titel, Kanal, Datum, Beschreibung)</label>
		{#if options.mode === 'video'}
			<label class="flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={options.embed_chapters} /> Kapitelmarken</label>
		{/if}
	</fieldset>

	{#if options.mode === 'video'}
		<fieldset>
			<legend class="label">SponsorBlock: Abschnitte herausschneiden</legend>
			<div class="grid gap-1.5 sm:grid-cols-2">
				{#each categories as cat (cat)}
					<label class="flex items-center gap-2 text-sm">
						<input
							type="checkbox"
							checked={options.sponsorblock_remove.includes(cat)}
							onchange={(e) => toggleCategory(cat, e.currentTarget.checked)}
						/>
						{sbLabels[cat] ?? cat}
					</label>
				{/each}
			</div>
		</fieldset>
	{/if}

	<label class="block">
		<span class="label">Dateiname</span>
		<input class="input font-mono text-xs" bind:value={options.output_template} />
		<span class="hint">
			yt-dlp-Vorlage, z. B. <code>%(uploader)s/%(title)s.%(ext)s</code> (Unterordner erlaubt). Bei Playlists wird automatisch die Nummer vorangestellt.
		</span>
	</label>
</div>
