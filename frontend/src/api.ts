import type {
  SantaDashboard,
  SantaDraw,
  SantaExclusion,
  SantaInvite,
  SantaMessage,
  SantaNotification,
  SantaParticipant,
  SantaParticipantPublic,
  SantaPrefill,
  SantaPreview,
  SantaRegenerate,
  SantaRoom,
  SantaSanteeCard,
  SantaSuggestions,
} from './types'

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

export type Badge = { code: string; label: string }
export type Marketplace = { name: string; url: string }

export type RecommendItem = CatalogItemShort & {
  marketplaces: Marketplace[] | null
  badges: Badge[] | null
  why: string | null
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
  recipientLikes: (recipientId: string) =>
    request<RecommendItem[]>(`/recipients/${recipientId}/likes`),
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
  feedback: (externalId: string, action: FeedbackAction, context: FeedbackContext, recipientId?: string, why?: string | null) =>
    request<FeedbackOut>('/feedback', {
      method: 'POST',
      body: JSON.stringify({
        external_id: externalId,
        action,
        context,
        recipient_id: recipientId ?? null,
        why: why ?? null,
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

  // feed
  feed: () => request<CatalogItemShort[]>('/feed'),

  // =========================================================================
  // Santa module
  // =========================================================================
  santa: {
    // --- Rooms ---
    createRoom: (payload: Record<string, unknown>) =>
      request<SantaRoom>('/santa/rooms', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    getRoom: (roomId: string) =>
      request<SantaRoom>(`/santa/rooms/${roomId}`),
    getRoomForParticipant: (roomId: string) =>
      request<SantaRoom>(`/santa/rooms/${roomId}/public`),
    updateRoom: (roomId: string, payload: Record<string, unknown>) =>
      request<SantaRoom>(`/santa/rooms/${roomId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),
      // --- Exclusions (только организатор, до draw) ---
    listExclusions: (roomId: string) =>
      request<SantaExclusion[]>(`/santa/rooms/${roomId}/exclusions`),
    createExclusion: (roomId: string, participantA: string, participantB: string) =>
      request<SantaExclusion>(`/santa/rooms/${roomId}/exclusions`, {
        method: 'POST',
        body: JSON.stringify({
          participant_a_id: participantA,
          participant_b_id: participantB,
        }),
      }),
    deleteExclusion: (roomId: string, exclusionId: string) =>
      request<void>(`/santa/rooms/${roomId}/exclusions/${exclusionId}`, {
        method: 'DELETE',
      }),
    listMyRooms: () =>
      request<SantaRoom[]>('/santa/rooms/my'),

    // --- Invite ---
    createInvite: (roomId: string, payload: { telegram_id?: number; expires_in_days?: number } = {}) =>
      request<SantaInvite>(`/santa/rooms/${roomId}/invite`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    // --- Join ---
    join: (token: string, payload: Record<string, unknown>) =>
      request<SantaParticipant>(`/santa/rooms/join/${token}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    // --- Participant (me) ---
    prefill: (roomId: string) =>
      request<SantaPrefill>(`/santa/rooms/${roomId}/participants/me/prefill`),
    updateMyProfile: (roomId: string, payload: Record<string, unknown>) =>
      request<SantaParticipant>(`/santa/rooms/${roomId}/participants/me`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),
    preview: (roomId: string) =>
      request<SantaPreview>(`/santa/rooms/${roomId}/participants/me/preview`),
    exportMyData: (roomId: string) =>
      request<Record<string, unknown>>(`/santa/rooms/${roomId}/participants/me/export`),

    // --- Participants list (public) ---
    listParticipants: (roomId: string) =>
      request<SantaParticipantPublic[]>(`/santa/rooms/${roomId}/participants`),

    // --- Draw ---
    startDraw: (roomId: string, mode: 'random' | 'chain' = 'random') =>
      request<SantaDraw>(`/santa/rooms/${roomId}/draw`, {
        method: 'POST',
        body: JSON.stringify({ mode }),
      }),
    getDraw: (roomId: string) =>
      request<SantaDraw>(`/santa/rooms/${roomId}/draw`),

    // --- Santee card (Санта) ---
    getMyAssignment: (roomId: string) =>
      request<SantaSanteeCard>(`/santa/rooms/${roomId}/assignment/me`),

    // --- Suggestions (Санта) ---
    getSuggestions: (assignmentId: string) =>
      request<SantaSuggestions>(`/santa/assignments/${assignmentId}/suggestions`),
    regenerate: (assignmentId: string) =>
      request<SantaRegenerate>(`/santa/assignments/${assignmentId}/suggestions/regenerate`, {
        method: 'POST',
      }),
    updateGiftStatus: (assignmentId: string, giftStatus: string) =>
      request<{ gift_status: string }>(`/santa/assignments/${assignmentId}/gift-status`, {
        method: 'PATCH',
        body: JSON.stringify({ gift_status: giftStatus }),
      }),

    // --- Messages ---
    sendMessage: (assignmentId: string, body: string) =>
      request<SantaMessage>(`/santa/assignments/${assignmentId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ body }),
      }),
    listMessages: (assignmentId: string) =>
      request<SantaMessage[]>(`/santa/assignments/${assignmentId}/messages`),

    // --- Dashboard (организатор) ---
    getDashboard: (roomId: string) =>
      request<SantaDashboard>(`/santa/rooms/${roomId}/dashboard`),

    // --- Notifications ---
    listNotifications: () =>
      request<SantaNotification[]>('/santa/notifications'),
    markNotificationRead: (id: string) =>
      request<SantaNotification>(`/santa/notifications/${id}/read`, { method: 'PATCH' }),
  },
}