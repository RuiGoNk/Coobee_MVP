import { useEffect, useState } from 'react'
import { api } from './api'
import type { CatalogItemShort } from './api'

type Tab = 'feed' | 'wishlist'

export default function Tabs() {
  const [tab, setTab] = useState<Tab>('feed')
  const [items, setItems] = useState<CatalogItemShort[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function load(t: Tab) {
    setLoading(true); setError('')
    try {
      const data = t === 'feed' ? await api.feed() : await api.wishlist()
      setItems(data)
    } catch (e) { setError(String(e)) }
    finally { setLoading(false) }
  }

  useEffect(() => { load(tab) }, [tab])

  async function toggleWishlist(it: CatalogItemShort) {
    setError('')
    try {
      if (tab === 'wishlist') {
        await api.removeFromWishlist(it.external_id)
        setItems((xs) => xs.filter((x) => x.external_id !== it.external_id))
      } else {
        await api.addToWishlist(it.external_id)
        setItems((xs) => xs.filter((x) => x.external_id !== it.external_id))
      }
    } catch (e) { setError(String(e)) }
  }

  return (
    <div style={{ maxWidth: 960, margin: '24px auto', fontFamily: 'system-ui', padding: 16 }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button onClick={() => setTab('feed')}
                style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #ccc',
                         background: tab === 'feed' ? '#1f6feb' : '#fff', color: tab === 'feed' ? '#fff' : '#000' }}>
          Для себя
        </button>
        <button onClick={() => setTab('wishlist')}
                style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #ccc',
                         background: tab === 'wishlist' ? '#1f6feb' : '#fff', color: tab === 'wishlist' ? '#fff' : '#000' }}>
          Вишлист
        </button>
      </div>

      {loading && <p>Загрузка…</p>}
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p style={{ color: '#888' }}>{tab === 'feed' ? 'Пока нечего показать.' : 'Вишлист пуст. Лайкните товар в «Для себя».'}</p>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
        {items.map((it) => (
          <div key={it.external_id} style={{ border: '1px solid #eee', borderRadius: 12, padding: 12, background: '#fff' }}>
            {it.image_url
              ? <img src={it.image_url} alt={it.title} style={{ width: '100%', height: 140, objectFit: 'cover', borderRadius: 8 }} />
              : <div style={{ width: '100%', height: 140, background: '#f4f4f4', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>нет фото</div>}
            <div style={{ fontWeight: 600, marginTop: 8, fontSize: 14 }}>{it.title}</div>
            <div style={{ fontSize: 13, color: '#555', marginBottom: 8 }}>{it.price_min ?? '?'}–{it.price_max ?? '?'} ₽</div>
            <div style={{ display: 'flex', gap: 6 }}>
              {it.marketplace_url && (
                <a href={it.marketplace_url} target="_blank" rel="noreferrer"
                   style={{ flex: 1, background: '#1f6feb', color: '#fff', textAlign: 'center', padding: '6px', borderRadius: 8, textDecoration: 'none', fontSize: 13 }}>
                  Купить
                </a>
              )}
              <button onClick={() => toggleWishlist(it)}
                      style={{ flex: 1, padding: '6px', border: '1px solid #ccc', borderRadius: 8, background: '#fff', fontSize: 13 }}>
                {tab === 'wishlist' ? 'Убрать' : '⭐ В вишлист'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
