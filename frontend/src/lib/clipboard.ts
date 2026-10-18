/**
 * Copies text to the clipboard. The async Clipboard API only exists on HTTPS
 * (or localhost); on plain http://nas-ip the legacy execCommand path is used.
 */
export async function copyText(text: string): Promise<boolean> {
	if (window.isSecureContext && navigator.clipboard) {
		try {
			await navigator.clipboard.writeText(text);
			return true;
		} catch {
			// fall through to the legacy path
		}
	}
	const area = document.createElement('textarea');
	area.value = text;
	area.setAttribute('readonly', '');
	area.style.position = 'fixed';
	area.style.opacity = '0';
	// Inside an open <dialog>, only its subtree is interactive.
	(document.querySelector('dialog[open]') ?? document.body).appendChild(area);
	area.select();
	area.setSelectionRange(0, text.length);
	let ok = false;
	try {
		ok = document.execCommand('copy');
	} catch {
		ok = false;
	}
	area.remove();
	return ok;
}
