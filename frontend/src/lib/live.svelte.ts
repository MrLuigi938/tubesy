import type { Download } from './types';

export type LiveEvent =
	| { event: 'download'; data: Download }
	| { event: 'download_removed'; data: { id: number } };

type Listener = (e: LiveEvent) => void;

const listeners = new Set<Listener>();
export const connection = $state({ online: false });

let socket: WebSocket | null = null;
let retry = 0;
let ping: ReturnType<typeof setInterval> | undefined;
let reconnect: ReturnType<typeof setTimeout> | undefined;
let wanted = false;

export function subscribe(fn: Listener): () => void {
	listeners.add(fn);
	return () => listeners.delete(fn);
}

function open() {
	const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
	socket = new WebSocket(`${proto}//${location.host}/api/ws`);
	socket.onopen = () => {
		connection.online = true;
		retry = 0;
		ping = setInterval(() => socket?.readyState === WebSocket.OPEN && socket.send('ping'), 25000);
	};
	socket.onmessage = (msg) => {
		const event = JSON.parse(msg.data) as LiveEvent;
		listeners.forEach((fn) => fn(event));
	};
	socket.onclose = (ev) => {
		connection.online = false;
		clearInterval(ping);
		socket = null;
		if (!wanted || ev.code === 4401) return;
		reconnect = setTimeout(open, Math.min(30000, 1000 * 2 ** retry++));
	};
}

export function connect() {
	wanted = true;
	if (!socket) open();
}

export function disconnect() {
	wanted = false;
	clearTimeout(reconnect);
	socket?.close();
}

/** Applies a live event to a list of downloads, keeping it in place. */
export function applyEvent(list: Download[], e: LiveEvent, accept: (d: Download) => boolean): Download[] {
	if (e.event === 'download_removed') return list.filter((d) => d.id !== e.data.id);
	const idx = list.findIndex((d) => d.id === e.data.id);
	if (!accept(e.data)) return idx === -1 ? list : list.filter((d) => d.id !== e.data.id);
	if (idx === -1) return [...list, e.data];
	const copy = list.slice();
	copy[idx] = e.data;
	return copy;
}
