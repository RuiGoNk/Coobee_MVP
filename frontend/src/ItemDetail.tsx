import { useState } from 'react'
import { api } from './api'
import type { RecommendItem, FeedbackAction } from './types'
import { HeartIcon, ThumbDownIcon, CheckCircleIcon } from './icons'

type Props = {
  item: RecommendItem
  action: FeedbackAction | undefined
  onClose: () => void
  onAction: (action: FeedbackAction) => void
}

export default function ItemDetail({ item, action, onClose, onAction }: Props) {
  const [added, setAdded] = useState(false)
  const [error, setError] = useState('')

  const links = item.marketplaces && item.marketplaces.length > 0
    ? item.marketplaces
    : item.marketplace_url ? [{ name: 'Маркетплейс', url: item.marketplace_url }] : []

  async function addToWishlist() {
    try {
      await api.addToWishlist(item.external_id)
      setAdded(true)
      setError('')
    } catch (e) { setError(String(e)) }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4" onClick={onClose}>
      <div className="bg-white w-full sm:max-w-lg sm:rounded-2xl rounded-t-2xl max-h-[90vh] overflow-y-auto"
           onClick={(e) => e.stopPropagation()}>
        <div className="relative">
          {item.image_url
            ? <img src={item.image_url} alt={item.title} className="w-full max-h-72 object-cover" />
            : <div className="w-full h-48 flex items-center justify-center text-gray-400 bg-gray-100">нет фото</div>}
          <button onClick={onClose} className="absolute top-3 right-3 w-9 h-9 rounded-full bg-white/90 flex items-center justify-center">✕</button>
          {item.badges && item.badges.length > 0 && (
            <div className="absolute top-3 left-3 flex flex-col gap-1">
              {item.badges.map((b) => (
                <span key={b.code} className="bg-black/70 text-white text-xs px-2 py-1 rounded-full">{b.label}</span>
              ))}
            </div>
          )}
        </div>

        <div className="p-4 space-y-3">
          <h2 className="text-lg font-semibold">{item.title}</h2>
          <div className="text-xl font-bold">{item.price_min ?? '?'}–{item.price_max ?? '?'} ₽</div>
          {item.description && <p className="text-sm text-gray-600">{item.description}</p>}

          {item.why && (
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 text-sm text-blue-800">
              <span className="font-medium">Почему подойдёт: </span>{item.why}
            </div>
          )}

          <div className="flex gap-2">
            <button onClick={() => onAction('dislike')}
                    className={`flex-1 py-2 rounded-lg border flex items-center justify-center gap-1 active:scale-95 ${action === 'dislike' ? 'border-gray-500 bg-gray-100' : 'border-gray-300'}`}>
              <ThumbDownIcon filled={action === 'dislike'} size={20} className="text-gray-700" /> Не то
            </button>
            <button onClick={() => onAction('have')}
                    className={`flex-1 py-2 rounded-lg border flex items-center justify-center gap-1 active:scale-95 ${action === 'have' ? 'border-green-500 bg-green-50' : 'border-gray-300'}`}>
              <CheckCircleIcon filled={action === 'have'} size={20} className="text-gray-700" /> Есть
            </button>
            <button onClick={() => onAction('like')}
                    className={`flex-1 py-2 rounded-lg border flex items-center justify-center gap-1 active:scale-95 ${action === 'like' ? 'border-red-400 bg-red-50' : 'border-gray-300'}`}>
              <HeartIcon filled={action === 'like'} size={20} className="text-gray-700" /> Нравится
            </button>
          </div>

          <button onClick={addToWishlist} disabled={added}
                  className="w-full py-2 rounded-lg bg-amber-100 text-amber-800 font-medium active:scale-95 disabled:opacity-60">
            {added ? '✓ В вишлисте' : '⭐ Добавить в свой вишлист'}
          </button>

          {links.length > 0 && (
            <div className="space-y-2 pt-2">
              <div className="text-sm font-medium text-gray-700">Купить:</div>
              {links.map((l) => (
                <a key={l.url} href={l.url} target="_blank" rel="noreferrer"
                   className="block w-full py-2 rounded-lg bg-blue-600 text-white text-center active:scale-95">
                  {l.name}
                </a>
              ))}
            </div>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
      </div>
    </div>
  )
}