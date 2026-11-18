import { useState } from 'react'
import { api } from '../api'
import type {
  SantaExclusion,
  SantaParticipantPublic,
  SantaRoom,
} from '../types'

type Props = {
  room: SantaRoom
  participants: SantaParticipantPublic[]
  exclusions: SantaExclusion[]
  canEdit: boolean
  onChanged: () => void
}

export default function SantaRoomSettings({
  room,
  participants,
  exclusions,
  canEdit,
  onChanged,
}: Props) {
  const [title, setTitle] = useState(room.title)
  const [eventDate, setEventDate] = useState(room.event_date ?? '')
  const [budgetMin, setBudgetMin] = useState(String(room.budget_min))
  const [budgetMax, setBudgetMax] = useState(String(room.budget_max))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const [inviteLink, setInviteLink] = useState('')
  const [inviteLoading, setInviteLoading] = useState(false)

  const [exclA, setExclA] = useState('')
  const [exclB, setExclB] = useState('')
  const [exclBusy, setExclBusy] = useState(false)

  const active = participants.filter((p) => !p.is_deleted)

  async function save() {
    setError('')
    setSaving(true)
    try {
      await api.santa.updateRoom(room.id, {
        title: title.trim(),
        event_date: eventDate || null,
        budget_min: Number(budgetMin),
        budget_max: Number(budgetMax),
      })
      onChanged()
    } catch (e) {
      setError(String(e))
    } finally {
      setSaving(false)
    }
  }

  async function generateInvite() {
    setInviteLoading(true)
    try {
      const inv = await api.santa.createInvite(room.id)
      setInviteLink(inv.deep_link ?? '')
    } catch (e) {
      setError(String(e))
    } finally {
      setInviteLoading(false)
    }
  }

  async function addExclusion() {
    if (!exclA || !exclB || exclA === exclB) return
    setExclBusy(true)
    setError('')
    try {
      await api.santa.createExclusion(room.id, exclA, exclB)
      setExclA('')
      setExclB('')
      onChanged()
    } catch (e) {
      setError(String(e))
    } finally {
      setExclBusy(false)
    }
  }

  async function removeExclusion(id: string) {
    setExclBusy(true)
    setError('')
    try {
      await api.santa.deleteExclusion(room.id, id)
      onChanged()
    } catch (e) {
      setError(String(e))
    } finally {
      setExclBusy(false)
    }
  }

  function nameById(id: string): string {
    return participants.find((p) => p.id === id)?.display_name ?? '—'
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 rounded-lg bg-[var(--santa-accent-soft)] text-[var(--santa-accent)] text-sm">
          {error}
        </div>
      )}

      {/* Invite */}
      <div className="santa-card">
        <h2 className="font-bold mb-2">Приглашение</h2>
        <p className="santa-muted text-sm mb-3">
          Отправьте ссылку участникам. Они вступят через Telegram-бота.
        </p>
        {inviteLink ? (
          <div className="flex gap-2">
            <input className="santa-input flex-1" readOnly value={inviteLink} />
            <button
              className="santa-btn santa-btn-secondary"
              onClick={() => navigator.clipboard.writeText(inviteLink)}
            >
              Скопировать
            </button>
          </div>
        ) : (
          <button
            className="santa-btn santa-btn-primary"
            onClick={generateInvite}
            disabled={inviteLoading}
          >
            {inviteLoading ? 'Генерируем…' : 'Сгенерировать ссылку'}
          </button>
        )}
      </div>

      {/* Параметры */}
      <div className="santa-card">
        <h2 className="font-bold mb-3">Параметры</h2>
        <label className="block mb-3">
          <span className="block text-sm font-medium mb-1">Название</span>
          <input
            className="santa-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={!canEdit}
          />
        </label>
        <label className="block mb-3">
          <span className="block text-sm font-medium mb-1">Дата обмена</span>
          <input
            type="date"
            className="santa-input"
            value={eventDate}
            onChange={(e) => setEventDate(e.target.value)}
            disabled={!canEdit}
          />
        </label>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <label className="block">
            <span className="block text-sm font-medium mb-1">Бюджет от</span>
            <input
              type="number"
              className="santa-input"
              value={budgetMin}
              onChange={(e) => setBudgetMin(e.target.value)}
              disabled={!canEdit}
            />
          </label>
          <label className="block">
            <span className="block text-sm font-medium mb-1">Бюджет до</span>
            <input
              type="number"
              className="santa-input"
              value={budgetMax}
              onChange={(e) => setBudgetMax(e.target.value)}
              disabled={!canEdit}
            />
          </label>
        </div>
        <button
          className="santa-btn santa-btn-primary"
          onClick={save}
          disabled={!canEdit || saving}
        >
          {saving ? 'Сохраняем…' : 'Сохранить'}
        </button>
        {!canEdit && (
          <p className="santa-muted text-xs mt-2">
            После жеребьёвки настройки заблокированы.
          </p>
        )}
      </div>

      {/* Исключения */}
      <div className="santa-card">
        <h2 className="font-bold mb-2">Исключения</h2>
        <p className="santa-muted text-sm mb-3">
          Запрещённые пары — например, супруги не дарят друг другу.
        </p>

        {exclusions.length === 0 ? (
          <p className="santa-muted text-sm mb-3">Пока нет исключений.</p>
        ) : (
          <div className="space-y-2 mb-3">
            {exclusions.map((ex) => (
              <div
                key={ex.id}
                className="flex items-center justify-between p-2 rounded-lg bg-[var(--santa-bg)]"
              >
                <span className="text-sm">
                  {nameById(ex.participant_a_id)} ↔ {nameById(ex.participant_b_id)}
                </span>
                <button
                  className="text-[var(--santa-danger)] text-sm underline"
                  onClick={() => removeExclusion(ex.id)}
                  disabled={!canEdit || exclBusy}
                >
                  Удалить
                </button>
              </div>
            ))}
          </div>
        )}

        {canEdit && (
          <div className="grid grid-cols-1 sm:grid-cols-[1fr_1fr_auto] gap-2">
            <select
              className="santa-input"
              value={exclA}
              onChange={(e) => setExclA(e.target.value)}
            >
              <option value="">Участник A</option>
              {active.map((p) => (
                <option key={p.id} value={p.id}>{p.display_name}</option>
              ))}
            </select>
            <select
              className="santa-input"
              value={exclB}
              onChange={(e) => setExclB(e.target.value)}
            >
              <option value="">Участник B</option>
              {active
                .filter((p) => p.id !== exclA)
                .map((p) => (
                  <option key={p.id} value={p.id}>{p.display_name}</option>
                ))}
            </select>
            <button
              className="santa-btn santa-btn-primary"
              onClick={addExclusion}
              disabled={!exclA || !exclB || exclBusy}
            >
              Добавить
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
