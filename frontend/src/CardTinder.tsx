import { motion, useMotionValue, useTransform } from 'framer-motion'
import { useState } from 'react'
import type { RecommendItem, FeedbackAction } from './types'
import { HeartIcon, ThumbDownIcon, CheckCircleIcon, ChevronRightIcon } from './icons'

type Props = {
  item: RecommendItem
  action: FeedbackAction | undefined
  onRate: (action: FeedbackAction) => void
  onNext: () => void
  onOpen: () => void
}

export default function CardTinder({ item, action, onRate, onNext, onOpen }: Props) {
  const x = useMotionValue(0)
  const rotate = useTransform(x, [-200, 200], [-10, 10])
  const [dragging, setDragging] = useState(false)

  function handleDragEnd(_: unknown, info: { offset: { x: number } }) {
    setDragging(false)
    if (Math.abs(info.offset.x) > 100) onNext()
  }

  return (
    <div className="relative w-full max-w-sm mx-auto">
      <motion.div
        drag="x"
        dragConstraints={{ left: 0, right: 0 }}
        dragElastic={0.6}
        onDragStart={() => setDragging(true)}
        onDragEnd={handleDragEnd}
        style={{ x, rotate }}
        className="relative w-full aspect-[3/4] bg-white rounded-2xl shadow-lg overflow-hidden cursor-grab select-none"
        onClick={() => { if (!dragging) onOpen() }}
      >
        {item.image_url
          ? <img src={item.image_url} alt={item.title} className="w-full h-full object-cover pointer-events-none" />
          : <div className="w-full h-full flex items-center justify-center text-gray-400 bg-gray-100">нет фото</div>}

        {item.badges && item.badges.length > 0 && (
          <div className="absolute top-3 left-3 flex flex-col gap-1">
            {item.badges.map((b) => (
              <span key={b.code} className="bg-black/70 text-white text-xs px-2 py-1 rounded-full">{b.label}</span>
            ))}
          </div>
        )}

        {/* иконки-оверлеи: контур → заливка при выборе */}
        <div className="absolute bottom-20 left-0 right-0 z-20 px-3">
          <div className="inline-block bg-black/55 text-white font-semibold text-sm px-2 py-1 rounded-md">
            {item.title}
          </div>
        </div>
        <div className="absolute bottom-0 left-0 right-0 p-3 flex justify-around bg-gradient-to-t from-black/60 to-transparent"
             onClick={(e) => e.stopPropagation()}>
          <button onClick={() => onRate('dislike')}
                  className="w-14 h-14 rounded-full bg-white/90 flex items-center justify-center active:scale-95"
                  aria-label="Не подходит">
            <ThumbDownIcon filled={action === 'dislike'} className="text-gray-700" />
          </button>
          <button onClick={() => onRate('have')}
                  className="w-14 h-14 rounded-full bg-white/90 flex items-center justify-center active:scale-95"
                  aria-label="Уже есть">
            <CheckCircleIcon filled={action === 'have'} className="text-gray-700" />
          </button>
          <button onClick={() => onRate('like')}
                  className="w-14 h-14 rounded-full bg-white/90 flex items-center justify-center active:scale-95"
                  aria-label="Нравится">
            <HeartIcon filled={action === 'like'} className="text-gray-700" />
          </button>
        </div>
      </motion.div>

      {/* переход к следующей карточке */}
      <button onClick={onNext}
              className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 w-12 h-12 rounded-full bg-white shadow flex items-center justify-center active:scale-95"
              aria-label="Следующая карточка">
        <ChevronRightIcon className="text-gray-700" />
      </button>
    </div>
  )
}