import { useEffect, useState } from 'react'
import { api } from './api'
import type { RecommendItem, FeedbackAction } from './types'
import CardTinder from './CardTinder'
import CardInstagram from './CardInstagram'
import ItemDetail from './ItemDetail'
import { HeartIcon, ThumbDownIcon, CheckCircleIcon } from './icons'

type Props = {
  recipientId: string
  recipientName: string
  onBack: () => void
}

type Mode = 'tinder' | 'instagram'

export default function Carousel({ recipientId, recipientName, onBack }: Props) {
  const [items, setItems] = useState<RecommendItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [mode, setMode] = useState<Mode>('tinder')
  const [index, setIndex] = useState(0)
  const [actions, setActions] = useState<Record<string, FeedbackAction | undefined>>({})
  const [openItem, setOpenItem] = useState<RecommendItem | null>(null)

  async function load() {
    setLoading(true)
    try {
      const r = await api.recommend(recipientId)
      setItems(r.items)
      setIndex(0)
    } catch (e) { setError(String(e)) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [recipientId])

  async function rate(externalId: string, action: FeedbackAction) {
    const current = actions[externalId]
    const item = items.find((it) => it.external_id === externalId)
    try {
      if (current === action) {
        await api.removeFeedback(externalId, 'recipient', recipientId)
        setActions((s) => ({ ...s, [externalId]: undefined }))
      } else {
        await api.feedback(externalId, action, 'recipient', recipientId, action === 'like' ? item?.why : null)
        setActions((s) => ({ ...s, [externalId]: action }))
      }
    } catch (e) { setError(String(e)) }
  }

  function next() {
    setIndex((i) => (i + 1 < items.length ? i + 1 : i))
  }

  async function loadMore() {
    await load()
  }

  if (loading) return <div className="p-10 text-center text-gray-500">Подбираем подарки для {recipientName}…</div>
  if (error) return <div className="p-10 text-center text-red-600">{error}</div>
  if (!items.length) return <div className="p-10 text-center text-gray-500">Нет рекомендаций.</div>

  const current = items[index]

  return (
    <div className="max-w-5xl mx-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <button onClick={onBack} className="text-sm text-gray-600">← Назад</button>
        <div className="flex gap-1 bg-gray-200 rounded-lg p-1">
          <button onClick={() => setMode('tinder')}
                  className={`px-3 py-1 text-sm rounded-md ${mode === 'tinder' ? 'bg-white shadow' : ''}`}>Tinder</button>
          <button onClick={() => setMode('instagram')}
                  className={`px-3 py-1 text-sm rounded-md ${mode === 'instagram' ? 'bg-white shadow' : ''}`}>Instagram</button>
        </div>
      </div>

      <h1 className="text-lg font-semibold mb-3">Подарки для {recipientName}</h1>

      {mode === 'tinder' && (
        <>
          {/* мобильный: одна карточка */}
          <div className="md:hidden">
            <div className="text-center text-sm text-gray-500 mb-2">{index + 1} из {items.length}</div>
            <CardTinder
              key={current.external_id}
              item={current}
              action={actions[current.external_id]}
              onRate={(a) => rate(current.external_id, a)}
              onNext={next}
              onOpen={() => setOpenItem(current)}
            />
          </div>

          {/* десктоп: сетка 3 + 2 + «плюс» */}
          <div className="hidden md:grid grid-cols-3 gap-4">
            {items.slice(0, 5).map((it) => (
              <div key={it.external_id} className="relative aspect-[3/4] rounded-2xl overflow-hidden shadow">
                <button onClick={() => setOpenItem(it)} className="absolute inset-0">
                  {it.image_url
                    ? <img src={it.image_url} alt={it.title} className="w-full h-full object-cover" />
                    : <div className="w-full h-full flex items-center justify-center text-gray-400 bg-gray-100">нет фото</div>}
                </button>
                {it.badges && it.badges.length > 0 && (
                  <div className="absolute top-2 left-2 flex flex-col gap-1">
                    {it.badges.map((b) => (
                      <span key={b.code} className="bg-black/70 text-white text-xs px-2 py-1 rounded-full">{b.label}</span>
                    ))}
                  </div>
                )}
                <div className="absolute bottom-0 left-0 right-0 p-2 flex justify-around bg-gradient-to-t from-black/60 to-transparent">
                  <button onClick={() => rate(it.external_id, 'dislike')}
                          className="w-10 h-10 rounded-full bg-white/90 flex items-center justify-center">
                    <ThumbDownIcon filled={actions[it.external_id] === 'dislike'} size={20} className="text-gray-700" />
                  </button>
                  <button onClick={() => rate(it.external_id, 'have')}
                          className="w-10 h-10 rounded-full bg-white/90 flex items-center justify-center">
                    <CheckCircleIcon filled={actions[it.external_id] === 'have'} size={20} className="text-gray-700" />
                  </button>
                  <button onClick={() => rate(it.external_id, 'like')}
                          className="w-10 h-10 rounded-full bg-white/90 flex items-center justify-center">
                    <HeartIcon filled={actions[it.external_id] === 'like'} size={20} className="text-gray-700" />
                  </button>
                </div>
              </div>
            ))}
            {/* 6-я карточка — «+» */}
            <button onClick={loadMore}
                    className="aspect-[3/4] rounded-2xl border-2 border-dashed border-gray-300 flex flex-col items-center justify-center text-gray-400 hover:border-blue-400 hover:text-blue-500">
              <span className="text-5xl leading-none">+</span>
              <span className="text-xs mt-2 text-center px-2">Не понравилось?<br />Подберём ещё</span>
            </button>
          </div>
        </>
      )}

      {mode === 'instagram' && (
        <div>
          {items.map((it) => (
            <CardInstagram
              key={it.external_id}
              item={it}
              action={actions[it.external_id]}
              onAction={(a) => rate(it.external_id, a)}
              onOpen={() => setOpenItem(it)}
            />
          ))}
        </div>
      )}

      {openItem && (
        <ItemDetail
          item={openItem}
          action={actions[openItem.external_id]}
          onClose={() => setOpenItem(null)}
          onAction={(a) => rate(openItem.external_id, a)}
        />
      )}
    </div>
  )
}