import { useEffect, useState } from 'react'
import { api } from './api'
import Carousel from './Carousel'
import ItemDetail from './ItemDetail'
import type { RecommendItem } from './types'

type Recipient = {
  id: string
  name: string
  relationship: string
  gender: string
  birth_date: string | null
  age: number | null
  occasion: string | null
  relationship_level: string | null
  budget_range: string | null
  details: Record<string, unknown> | null
  notifications_enabled: boolean
}

type Props = {
  recipient: Recipient
  relationshipLabel: string
  onBack: () => void
  onUpdated: (r: Recipient) => void
}

const RELATIONSHIPS: Record<string, string> = {
  mother: 'мама', father: 'папа', wife: 'жена', husband: 'муж',
  boyfriend: 'парень', girlfriend: 'девушка', brother: 'брат', sister: 'сестра',
  friend_m: 'друг', friend_f: 'подруга', colleague: 'коллега', boss: 'начальник',
  child: 'ребёнок', other: 'другое',
}
const INTERESTS = ['tech', 'gaming', 'books_fiction', 'books_nonfiction', 'coffee', 'cooking', 'travel', 'sport', 'art', 'music', 'cinema', 'fashion', 'beauty', 'home', 'gardening', 'pets', 'photography', 'science']

export default function RecipientProfile({ recipient, relationshipLabel, onBack, onUpdated }: Props) {
  const [tab, setTab] = useState<'view' | 'edit' | 'likes'>('view')
  const [showCarousel, setShowCarousel] = useState(false)

  // форма редактирования
  const [name, setName] = useState(recipient.name)
  const [relationship, setRelationship] = useState(recipient.relationship)
  const [gender, setGender] = useState(recipient.gender)
  const [budget, setBudget] = useState(recipient.budget_range ?? 'standard')
  const [birthDate, setBirthDate] = useState(recipient.birth_date ?? '')
  const [age, setAge] = useState(recipient.age?.toString() ?? '')
  const [mode, setMode] = useState<'date' | 'age'>(recipient.birth_date ? 'date' : 'age')
  const [interests, setInterests] = useState<string[]>(((recipient.details?.interests as string[]) ?? []))
  const [notify, setNotify] = useState(recipient.notifications_enabled)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // история лайков
  const [likes, setLikes] = useState<RecommendItem[]>([])
  const [likesLoading, setLikesLoading] = useState(false)
  const [openItem, setOpenItem] = useState<RecommendItem | null>(null)

  useEffect(() => {
    if (tab !== 'likes') return
    setLikesLoading(true)
    api.recipientLikes(recipient.id)
      .then((rows) => setLikes(rows))
      .catch(() => setLikes([]))
      .finally(() => setLikesLoading(false))
  }, [tab, recipient.id])

  async function unlike(externalId: string) {
    try {
      await api.removeFeedback(externalId, 'recipient', recipient.id)
      setLikes((ls) => ls.filter((l) => l.external_id !== externalId))
      setOpenItem(null)
    } catch (e) { setError(String(e)) }
  }

  function toggleInterest(i: string) {
    setInterests((s) => s.includes(i) ? s.filter((x) => x !== i) : [...s, i])
  }

  async function save() {
    setError(''); setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        name, relationship, gender,
        budget_range: budget,
        notifications_enabled: notify,
        details: { ...(recipient.details ?? {}), interests },
      }
      if (mode === 'date' && birthDate) { payload.birth_date = birthDate; payload.age = null }
      else if (mode === 'age' && age) { payload.age = Number(age); payload.birth_date = null }
      else throw new Error('укажите дату или возраст')
      const r = await api.updateRecipient(recipient.id, payload)
      onUpdated(r as unknown as Recipient)
      setTab('view')
    } catch (e) { setError(String(e)) } finally { setSaving(false) }
  }

  if (showCarousel) {
    return <Carousel recipientId={recipient.id} recipientName={recipient.name} onBack={() => setShowCarousel(false)} />
  }

  return (
    <div className="max-w-2xl mx-auto p-4">
      <button onClick={onBack} className="text-sm text-gray-600 mb-4">← К получателям</button>

      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xl font-bold">
          {recipient.name.charAt(0).toUpperCase()}
        </div>
        <div>
          <h1 className="text-xl font-bold">{recipient.name}</h1>
          <div className="text-sm text-gray-500">{relationshipLabel}</div>
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        <button onClick={() => setTab('view')} className={`px-3 py-1.5 rounded-lg text-sm ${tab === 'view' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>Профиль</button>
        <button onClick={() => setTab('edit')} className={`px-3 py-1.5 rounded-lg text-sm ${tab === 'edit' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>Редактировать</button>
        <button onClick={() => setTab('likes')} className={`px-3 py-1.5 rounded-lg text-sm ${tab === 'likes' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>История лайков</button>
      </div>

      {tab === 'view' && (
        <div className="space-y-3">
          <div className="border border-gray-200 rounded-xl p-4 text-sm space-y-1">
            <div><span className="text-gray-500">Пол:</span> {recipient.gender}</div>
            <div><span className="text-gray-500">Возраст:</span> {recipient.birth_date ? `д.р. ${recipient.birth_date}` : recipient.age ?? '—'}</div>
            <div><span className="text-gray-500">Бюджет:</span> {recipient.budget_range ?? '—'}</div>
            <div><span className="text-gray-500">Интересы:</span> {((recipient.details?.interests as string[]) ?? []).join(', ') || '—'}</div>
            <div><span className="text-gray-500">Напоминания:</span> {recipient.notifications_enabled ? 'вкл' : 'выкл'}</div>
          </div>
          <button onClick={() => setShowCarousel(true)}
                  className="w-full py-3 rounded-xl bg-blue-600 text-white font-medium active:scale-95">
            Подобрать подарок
          </button>
        </div>
      )}

      {tab === 'edit' && (
        <div className="grid gap-3">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Имя"
                 className="border border-gray-300 rounded-lg px-3 py-2" />
          <select value={relationship} onChange={(e) => setRelationship(e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2">
            {Object.entries(RELATIONSHIPS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select value={gender} onChange={(e) => setGender(e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2">
            <option value="unisex">унисекс</option>
            <option value="male">мужской</option>
            <option value="female">женский</option>
          </select>
          <div className="flex gap-4 text-sm">
            <label><input type="radio" checked={mode === 'date'} onChange={() => setMode('date')} /> Дата рождения</label>
            <label><input type="radio" checked={mode === 'age'} onChange={() => setMode('age')} /> Только возраст</label>
          </div>
          {mode === 'date'
            ? <input type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2" />
            : <input type="number" min={0} max={120} value={age} onChange={(e) => setAge(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2" />}
          <select value={budget} onChange={(e) => setBudget(e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2">
            <option value="symbolic">символический (до 1000)</option>
            <option value="standard">стандартный (1000–5000)</option>
            <option value="solid">солидный (5000–15000)</option>
            <option value="premium">премиум (15000+)</option>
          </select>
          <fieldset className="border border-gray-200 rounded-xl p-3">
            <legend className="px-2 text-sm text-gray-600">Интересы</legend>
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              {INTERESTS.map((i) => (
                <label key={i} className="text-sm">
                  <input type="checkbox" checked={interests.includes(i)} onChange={() => toggleInterest(i)} /> {i}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="text-sm">
            <input type="checkbox" checked={notify} onChange={(e) => setNotify(e.target.checked)} /> Напоминать о праздниках
          </label>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <div className="flex gap-2">
            <button onClick={() => setTab('view')} className="flex-1 py-2 rounded-lg border border-gray-300">Отмена</button>
            <button onClick={save} disabled={saving}
                    className="flex-1 py-2 rounded-lg bg-blue-600 text-white disabled:opacity-60">
              {saving ? 'Сохраняем…' : 'Сохранить'}
            </button>
          </div>
        </div>
      )}

      {tab === 'likes' && (
        <div>
          {likesLoading && <p className="text-gray-500">Загрузка…</p>}
          {!likesLoading && likes.length === 0 && <p className="text-gray-500">Пока нет лайков.</p>}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {likes.map((l) => (
              <button key={l.external_id} onClick={() => setOpenItem(l)}
                      className="text-left border border-gray-200 rounded-xl overflow-hidden active:scale-95">
                {l.image_url
                  ? <img src={l.image_url} alt={l.title} className="w-full h-28 object-cover" />
                  : <div className="w-full h-28 bg-gray-100 flex items-center justify-center text-gray-400 text-xs">нет фото</div>}
                <div className="p-2 text-sm font-medium">{l.title}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {openItem && (
        <ItemDetail
          item={openItem}
          action="like"
          onClose={() => setOpenItem(null)}
          onAction={(a) => { if (a === 'like') unlike(openItem.external_id) }}
        />
      )}
    </div>
  )
}