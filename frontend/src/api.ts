const TOKEN_KEY = 'coobee_jwt'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`/api/v1${path}`, { ...options, headers })
  if (res.status === 204) return undefined as T
  const text = await res.text()
  const data = text ? JSON.parse(text) : undefined
  if (!res.ok) {
    const detail = data?.detail ?? res.statusText
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return data as T
}

export type FeedbackAction = 'like' | 'dislike' | 'have'
export type FeedbackContext = 'recipient' | 'self_wishlist'

export type FeedbackOut = {
  id: string
  external_id: string
  action: string
  context: string
  recipient_id: string | null
}

export type CatalogItemShort = {
  external_id: string
  title: string
  description: string | null
  price_min: number | null
  price_max: number | null
  image_url: string | null
  marketplace_url: string | null
  tags: string[] | null
}

export type RecommendItem = CatalogItemShort & {
  badge: 'match' | 'surprise'
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

  // recommend
  recommend: (recipientId: string) =>
    request<{ items: RecommendItem[] }>('/recommend', {
      method: 'POST',
      body: JSON.stringify({ recipient_id: recipientId }),
    }),

  // feedback (upsert + delete)
  feedback: (externalId: string, action: FeedbackAction, context: FeedbackContext, recipientId?: string) =>
    request<FeedbackOut>('/feedback', {
      method: 'POST',
      body: JSON.stringify({
        external_id: externalId,
        action,
        context,
        recipient_id: recipientId ?? null,
      }),
    }),
  removeFeedback: (externalId: string, context: FeedbackContext, recipientId?: string) => {
    const params = new URLSearchParams({ context })
    if (recipientId) params.set('recipient_id', recipientId)
    return request<void>(`/feedback/${externalId}?${params.toString()}`, { method: 'DELETE' })
  },

  // wishlist
  wishlist: () => request<CatalogItemShort[]>('/wishlist'),
  addToWishlist: (externalId: string) =>
    request<CatalogItemShort>(`/wishlist/${externalId}`, { method: 'POST' }),
  removeFromWishlist: (externalId: string) =>
    request<void>(`/wishlist/${externalId}`, { method: 'DELETE' }),

  // feed "для себя"
  feed: () => request<CatalogItemShort[]>('/feed'),
}