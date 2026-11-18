import type { SantaDashboard, SantaGiftStatus } from '../types'

type Props = {
  dashboard: SantaDashboard
}

const GIFT_LABEL: Record<SantaGiftStatus, string> = {
  pending: 'Не отправлен',
  chosen: 'Выбран',
  shipped: 'Отправлен',
  delivered: 'Доставлен',
}

const GIFT_CLS: Record<SantaGiftStatus, string> = {
  pending: 'santa-badge-accent',
  chosen: 'santa-badge-primary',
  shipped: 'santa-badge-festive',
  delivered: 'santa-badge-success',
}

export default function SantaRoomDashboard({ dashboard }: Props) {
  const d = dashboard
  const sent = d.participants.filter(
    (p) => p.gift_status === 'shipped' || p.gift_status === 'delivered',
  ).length

  return (
    <div className="space-y-4">
      {/* Сводка */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat label="Всего" value={d.participants_total} />
        <Stat label="Полная анкета" value={d.participants_profile_full} />
        <Stat label="Минимум" value={d.participants_profile_min} />
        <Stat label="Не заполнили" value={d.participants_not_filled} />
      </div>

      {/* Прогресс подарков */}
      <div className="santa-card">
        <div className="flex justify-between text-sm mb-2">
          <span className="santa-muted">Отправили подарки</span>
          <span className="font-medium">
            {sent} / {d.participants_total}
          </span>
        </div>
        <div className="h-2 rounded-full bg-[var(--santa-border)] overflow-hidden">
          <div
            className="h-full bg-[var(--santa-success)] transition-all"
            style={{ width: `${d.participants_total ? (sent / d.participants_total) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* Участники и статусы */}
      <div className="santa-card">
        <h2 className="font-bold mb-3">Статусы</h2>
        <div className="divide-y divide-[var(--santa-border)]">
          {d.participants.map((p) => (
            <div key={p.participant_id} className="flex items-center justify-between py-2.5">
              <div className={p.is_deleted ? 'line-through santa-muted' : 'font-medium'}>
                {p.display_name}
              </div>
              {p.gift_status ? (
                <span className={`santa-badge ${GIFT_CLS[p.gift_status]}`}>
                  {GIFT_LABEL[p.gift_status]}
                </span>
              ) : (
                <span className="santa-muted text-xs">—</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="santa-card text-center">
      <div className="text-2xl font-bold">{value}</div>
      <div className="santa-muted text-xs mt-1">{label}</div>
    </div>
  )
}