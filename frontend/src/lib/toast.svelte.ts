export interface Toast {
	id: number;
	kind: 'ok' | 'error' | 'info';
	text: string;
}

export const toasts = $state<Toast[]>([]);
let next = 1;

export function toast(text: string, kind: Toast['kind'] = 'ok', ms = 4000) {
	const id = next++;
	toasts.push({ id, kind, text });
	setTimeout(() => {
		const i = toasts.findIndex((t) => t.id === id);
		if (i !== -1) toasts.splice(i, 1);
	}, ms);
}
