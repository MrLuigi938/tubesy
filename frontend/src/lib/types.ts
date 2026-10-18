export type Role = 'admin' | 'user';

export interface User {
	id: number;
	username: string;
	email: string | null;
	role: Role;
	is_active: boolean;
	quota_bytes: number | null;
	default_preset_id: number | null;
	created_at: string | null;
	last_login_at: string | null;
}

export type DownloadStatus = 'queued' | 'downloading' | 'processing' | 'completed' | 'failed' | 'canceled';

export interface Download {
	id: number;
	user_id: number;
	username: string | null;
	url: string;
	video_id: string | null;
	title: string | null;
	uploader: string | null;
	thumbnail: string | null;
	duration: number | null;
	preset_name: string | null;
	mode: 'video' | 'audio';
	playlist_title: string | null;
	playlist_index: number | null;
	status: DownloadStatus;
	progress: number;
	error: string | null;
	filename: string | null;
	file_size: number | null;
	created_at: string | null;
	started_at: string | null;
	finished_at: string | null;
	speed: number | null;
	eta: number | null;
	downloaded_bytes: number | null;
	total_bytes: number | null;
	stage: string | null;
}

export interface PresetOptions {
	mode: 'video' | 'audio';
	quality: string;
	container: string;
	audio_format: string;
	audio_quality: string;
	subtitles: boolean;
	auto_subtitles: boolean;
	sub_langs: string;
	embed_thumbnail: boolean;
	embed_metadata: boolean;
	embed_chapters: boolean;
	sponsorblock_remove: string[];
	output_template: string;
}

export interface Preset {
	id: number;
	name: string;
	options: PresetOptions;
	is_global: boolean;
}

export interface ProbeEntry {
	index: number;
	url: string;
	video_id: string | null;
	title: string;
	duration: number | null;
	thumbnail: string | null;
	uploader: string | null;
}

export interface ProbeResult {
	type: 'video' | 'playlist';
	url: string;
	title: string | null;
	uploader: string | null;
	thumbnail: string | null;
	extractor: string | null;
	video_id?: string | null;
	duration?: number | null;
	count?: number;
	entries?: ProbeEntry[];
}
