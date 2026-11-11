const TOKEN_KEY = 'coobee_jwt';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`/api/v1${path}`, { ...options, headers });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!res.ok) {
    const detail = data?.detail ?? res.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data as T;
}

export const api = {
  // auth A1
  authTelegram: (payload: Record<string, unknown>) =>
    request<{ access_token: string; user_id: string }>('/auth/telegram', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  // auth A2
  createSession: () =>
    request<{ session_id: string; deep_link: string; expires_at: string }>('/auth/session', {
      method: 'POST',
    }),
  getSession: (id: string) =>
    request<{ status: string; access_token?: string; user_id?: string }>(`/auth/session/${id}`),
  me: () => request<{ id: string; telegram_id: number; username: string | null }>('/auth/me'),
  // profile
  getProfile: () => request<Record<string, unknown> | null>('/profile/me'),
  putProfile: (payload: Record<string, unknown>) =>
    request<Record<string, unknown>>('/profile/me', { method: 'PUT', body: JSON.stringify(payload) }),
  // recipients
  listRecipients: () => request<Array<Record<string, unknown>>>('/recipients'),
  createRecipient: (payload: Record<string, unknown>) =>
    request<Record<string, unknown>>('/recipients', { method: 'POST', body: JSON.stringify(payload) }),
  updateRecipient: (id: string, payload: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/recipients/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteRecipient: (id: string) =>
    request<void>(`/recipients/${id}`, { method: 'DELETE' }),
};