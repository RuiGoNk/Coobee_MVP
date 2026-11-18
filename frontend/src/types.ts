export type FeedbackAction = 'like' | 'dislike' | 'have'

export type Badge = { code: string; label: string }

export type Marketplace = { name: string; url: string }

export type RecommendItem = {
  external_id: string
  title: string
  description: string | null
  price_min: number | null
  price_max: number | null
  image_url: string | null
  marketplace_url: string | null
  marketplaces: Marketplace[] | null
  badges: Badge[] | null
  why: string | null
}

// ===========================================================================
// Santa module
// ===========================================================================

export type SantaGender = 'male' | 'female' | 'other' | 'prefer_not_to_say'
export type SantaVisibilityMode = 'full' | 'general' | 'hidden'
export type SantaRoomStatus =
  | 'draft' | 'collecting' | 'drawn' | 'in_progress' | 'completed' | 'archived'
export type SantaParticipantStatus =
  | 'invited' | 'joined' | 'profile_min' | 'profile_full'
export type SantaGiftStatus = 'pending' | 'chosen' | 'shipped' | 'delivered'
export type SantaDrawStatus = 'generating' | 'ready'

export type SantaRoom = {
  id: string
  owner_id: string
  title: string
  description: string | null
  event_date: string | null
  budget_min: number
  budget_max: number
  currency: string
  tz: string
  status: SantaRoomStatus
  anonymity_mode: 'full' | 'reveal_after' | 'signed'
  join_policy: 'link' | 'code' | 'invite'
  visibility_policy: 'open' | 'balanced' | 'minimal'
  max_participants: number
  require_min_profile: boolean
  created_at: string
}

export type SantaPickupPoint = {
  market: 'ozon' | 'yandex' | 'other'
  point_id?: string | null
  city?: string | null
  address_hint?: string | null
}

export type SantaParticipant = {
  id: string
  room_id: string
  user_id: string
  display_name: string
  gender: SantaGender
  birth_date: string | null
  age: number | null
  interests: string[]
  hobbies: string | null
  antipathies: string | null
  allergies: string | null
  constraints: string | null
  brands: string | null
  sizes: Record<string, unknown> | null
  budget_pref_min: number | null
  budget_pref_max: number | null
  pickup_point: SantaPickupPoint | null
  visibility: Record<string, SantaVisibilityMode>
  profile_completeness: number
  status: SantaParticipantStatus
  is_deleted: boolean
  joined_at: string
}

export type SantaParticipantPublic = {
  id: string
  display_name: string
  status: SantaParticipantStatus
  is_deleted: boolean
}

export type SantaPrefill = {
  from_profile: Record<string, unknown>
  missing: string[]
  suggested_visibility: Record<string, SantaVisibilityMode>
}

export type SantaPreview = {
  display_name: string
  fields: Record<string, unknown>
  warnings: string[]
}

export type SantaInvite = {
  id: string
  room_id: string
  token: string
  telegram_id: number | null
  expires_at: string | null
  used_at: string | null
  created_at: string
  deep_link: string | null
}

export type SantaDraw = {
  id: string
  room_id: string
  drawn_at: string
  drawn_by: string | null
  algorithm_version: string
  status: SantaDrawStatus
}

export type SantaSanteeCard = {
  assignment_id: string
  participant: Record<string, unknown>
  budget_min: number
  budget_max: number
  currency: string
  gift_status: SantaGiftStatus
  viewed_at: string | null
  pickup_point: SantaPickupPoint | null
  hints: string[]
}

export type SantaSuggestionItem = {
  id: string
  external_id: string | null
  idea_title: string
  category: string | null
  tags: string[]
  price_min: number | null
  price_max: number | null
  reason: string | null
  score: number | null
  source: 'curated' | 'llm' | 'marketplace'
}

export type SantaSuggestions = {
  assignment_id: string
  generation: number
  items: SantaSuggestionItem[]
  can_regenerate: boolean
  regenerations_left: number
}

export type SantaRegenerate = SantaSuggestions & { added: number }

export type SantaMessage = {
  id: string
  body: string
  is_revealed: boolean
  created_at: string
  from_role: 'santa' | 'santee'
}

export type SantaNotification = {
  id: string
  type: string
  payload: Record<string, unknown>
  read_at: string | null
  created_at: string
}

export type SantaDashboard = {
  room_id: string
  room_status: SantaRoomStatus
  participants_total: number
  participants_profile_min: number
  participants_profile_full: number
  participants_not_filled: number
  draw: SantaDraw | null
  participants: Array<{
    participant_id: string
    display_name: string
    status: SantaParticipantStatus
    profile_completeness: number
    is_deleted: boolean
    gift_status: SantaGiftStatus | null
  }>
}

export type SantaExclusion = {
  id: string
  room_id: string
  participant_a_id: string
  participant_b_id: string
}