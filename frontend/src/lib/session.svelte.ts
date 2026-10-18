import { api } from './api';
import type { User } from './types';

export const session = $state<{ user: User | null; ready: boolean }>({ user: null, ready: false });

export async function refreshUser(): Promise<User | null> {
	try {
		session.user = await api.get<User>('/api/auth/me');
	} catch {
		session.user = null;
	}
	return session.user;
}
