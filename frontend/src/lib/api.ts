import { t, tServer } from './i18n.svelte';

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
	}
}

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

function detailMessage(detail: unknown): string {
	if (typeof detail === 'string') return tServer(detail);
	// FastAPI validation errors: [{loc, msg}, ...]
	if (Array.isArray(detail) && detail.length) {
		return detail
			.map((d) => tServer(String(d?.msg ?? d).replace(/^Value error, /, '')))
			.join(' · ');
	}
	return t('Unbekannter Fehler');
}

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) {
	onUnauthorized = fn;
}

async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
	const res = await fetch(path, {
		method,
		credentials: 'same-origin',
		headers: {
			'X-Requested-With': 'Tubesy',
			...(body !== undefined ? { 'Content-Type': 'application/json' } : {})
		},
		body: body !== undefined ? JSON.stringify(body) : undefined
	});
	if (res.status === 401 && !path.startsWith('/api/auth/')) onUnauthorized?.();
	const data = res.headers.get('content-type')?.includes('json') ? await res.json() : null;
	if (!res.ok) throw new ApiError(res.status, detailMessage(data?.detail ?? res.statusText));
	return data as T;
}

export const api = {
	get: <T>(path: string) => request<T>('GET', path),
	post: <T>(path: string, body: unknown = {}) => request<T>('POST', path, body),
	put: <T>(path: string, body: unknown) => request<T>('PUT', path, body),
	patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
	del: <T>(path: string) => request<T>('DELETE', path)
};

export function errorText(e: unknown): string {
	return e instanceof Error ? e.message : String(e);
}
