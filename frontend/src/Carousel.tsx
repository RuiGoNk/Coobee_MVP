import { useEffect, useState } from 'react'
import { api } from './api'
import type { RecommendItem, FeedbackAction } from './api'

type Props = {
  recipientId: string
  recipientName: string
  onBack: () => void
}

type FeedbackState = Record<string, FeedbackAction | undefined>

export default function Carousel({ recipientId, recipientName, onBack }: Props) {
  const [items, setItems] = useState<RecommendItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [state, setState] = useState<FeedbackState>({})

  useEffect(() => {
    setLoading(true)
    api.recommend(recipientId)
      .then((r) => setItems(r.items))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [recipientId])

  async function toggle(externalId: string, action: FeedbackAction) {
    const current = state[externalId]
    setError('')
    try {
      if (current === action) {
        // снять
        await api.removeFeedback(externalId, 'recipient', recipientId)
        setState((s) => ({ ...s, [externalId]: undefined }))
      } else {
        // поставить/переключить
        await api.feedback(externalId, action, 'recipient', recipientId)
        setState((s) => ({ ...s, [externalId]: action }))
      }
    } catch (e) {
      setError(String(e))
    }
  }

  async function addToWishlist(externalId: string) {
    try {
      await api.addToWishlist(externalId)
      setError('')
      alert('Добавлено в вишлист')
    } catch (e) {
      setError(String(e))
    }
  }

  if (loading) return <div style={{ padding: 40 }}>Подбираем подарки для {recipientName}…</div>
  if (error) return <div style={{ padding: 40, color: 'crimson' }}>{error}</div>
  if (!items.length) return <div style={{ padding: 40 }}>Нет рекомендаций. Попробуйте позже.</div>

  return (
    <div style={{ fontFamily: 'system-ui', padding: 16, maxWidth: 1200, margin: '0 auto' }}>
      <button onClick={onBack} style={{ marginBottom: 16 }}>← Назад</button>
      <h1 style={{ fontSize: 20, marginBottom: 12 }}>Подарки для {recipientName}</h1>
      <div style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 12 }}>
        {items.map((it) => {
          const fb = state[it.external_id]
          return (
            <div key={it.external_id} style={{
              minWidth: 220, maxWidth: 220, border: '1px solid #eee', borderRadius: 12,
              padding: 12, display: 'flex', flexDirection: 'column', gap: 8, background: '#fff'
            }}>
              <div style={{
                background: it.badge === 'surprise' ? '#ffe6b3' : '#d7f0d7',
                color: '#333', borderRadius: 8, padding: '2px 8px', fontSize: 12, alignSelf: 'flex-start'
              }}>
                {it.badge === 'surprise' ? 'Сюрприз' : 'Точно подойдёт'}
              </div>
              {it.image_url
                ? <img src={it.image_url} alt={it.title} style={{ width: '100%', height: 140, objectFit: 'cover', borderRadius: 8 }} />
                : <div style={{ width: '100%', height: 140, background: '#f4f4f4', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>нет фото</div>}
              <div style={{ fontWeight: 600, fontSize: 14 }}>{it.title}</div>
              <div style={{ fontSize: 13, color: '#555' }}>
                {it.price_min ?? '?'}–{it.price_max ?? '?'} ₽
              </div>
              {it.marketplace_url && (
                <a href={it.marketplace_url} target="_blank" rel="noreferrer"
                   style={{ background: '#1f6feb', color: '#fff', textAlign: 'center', padding: '8px', borderRadius: 8, textDecoration: 'none', fontSize: 14 }}>
                  Купить
                </a>
              )}
              <button onClick={() => addToWishlist(it.external_id)}
                      style={{ padding: '6px', border: '1px solid #ccc', borderRadius: 8, background: '#fff', fontSize: 13 }}>
                ⭐ В вишлист
              </button>
              <div style={{ display: 'flex', gap: 6 }}>
                <button onClick={() => toggle(it.external_id, 'like')}
                        title="Подходит"
                        style={{ flex: 1, padding: '6px', borderRadius: 8, border: '1px solid #ccc', background: fb === 'like' ? '#d7f0d7' : '#fff' }}>
                  👍
                </button>
                <button onClick={() => toggle(it.external_id, 'dislike')}
                        title="Не подходит"
                        style={{ flex: 1, padding: '6px', borderRadius: 8, border: '1px solid #ccc', background: fb === 'dislike' ? '#f8d7da' : '#fff' }}>
                  👎
                </button>
                <button onClick={() => toggle(it.external_id, 'have')}
                        title="Уже есть"
                        style={{ flex: 1, padding: '6px', borderRadius: 8, border: '1px solid #ccc', background: fb === 'have' ? '#fff3cd' : '#fff' }}>
                  ✅
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}