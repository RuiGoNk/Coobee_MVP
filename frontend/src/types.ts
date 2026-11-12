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