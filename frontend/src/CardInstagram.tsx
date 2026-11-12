import type { RecommendItem, FeedbackAction } from './types'
import { HeartIcon, ThumbDownIcon, CheckCircleIcon } from './icons'

type Props = {
  item: RecommendItem
  action: FeedbackAction | undefined
  onAction: (action: FeedbackAction) => void
  onOpen: () => void
}

export default function CardInstagram({ item, action, onAction, onOpen }: Props) {
  return (
    <div className="bg-white rounded-2xl shadow-sm overflow-hidden mb-4">
      <div className="relative aspect-square cursor-pointer" onClick={onOpen}>
        {item.image_url
          ? <img src={item.image_url} alt={item.title} className="w-full h-full object-cover" />
          : <div className="w-full h-full flex items-center justify-center text-gray-400 bg-gray-100">нет фото</div>}

        {item.badges && item.badges.length > 0 && (
          <div className="absolute top-3 left-3 flex flex-col gap-1">
            {item.badges.map((b) => (
              <span key={b.code} className="bg-black/70 text-white text-xs px-2 py-1 rounded-full">{b.label}</span>
            ))}
          </div>
        )}

        <div className="absolute bottom-3 left-0 right-0 flex justify-around" onClick={(e) => e.stopPropagation()}>
          <button onClick={() => onAction('dislike')}
                  className="w-12 h-12 rounded-full bg-white/90 flex items-center justify-center active:scale-95"
                  aria-label="Не подходит">
            <ThumbDownIcon filled={action === 'dislike'} className="text-gray-700" size={24} />
          </button>
          <button onClick={() => onAction('have')}
                  className="w-12 h-12 rounded-full bg-white/90 flex items-center justify-center active:scale-95"
                  aria-label="Уже есть">
            <CheckCircleIcon filled={action === 'have'} className="text-gray-700" size={24} />
          </button>
          <button onClick={() => onAction('like')}
                  className="w-12 h-12 rounded-full bg-white/90 flex items-center justify-center active:scale-95"
                  aria-label="Нравится">
            <HeartIcon filled={action === 'like'} className="text-gray-700" size={24} />
          </button>
        </div>
      </div>
      <div className="p-3">
        <div className="font-semibold text-sm">{item.title}</div>
        <div className="text-xs text-gray-500">{item.price_min ?? '?'}–{item.price_max ?? '?'} ₽</div>
      </div>
    </div>
  )
}