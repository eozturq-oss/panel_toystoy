import { StrictMode, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  Bell,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  ExternalLink,
  Filter,
  LayoutDashboard,
  Package,
  Plus,
  Search,
  Send,
  Settings,
  ShoppingBag,
  Sparkles,
  Truck,
  X,
} from 'lucide-react'
import './styles.css'

type ChannelStatus = 'Yayında' | 'Taslak' | 'Bekliyor'
type Product = {
  id: number
  name: string
  sku: string
  barcode: string
  image: string
  stock: number
  price: string
  age: string
  ce: boolean
  category: string
  trendyol: ChannelStatus
  hepsiburada: ChannelStatus
}

const products: Product[] = [
  { id: 1, name: 'Renkli Yapı Blokları', sku: 'TOY-BLOCK-001', barcode: '8690000000001', image: 'https://images.unsplash.com/photo-1587654780291-39c9404d746b?auto=format&fit=crop&w=160&q=80', stock: 25, price: '349,90 TL', age: '3–6 yaş', ce: true, category: 'Legolar & Yapı Oyuncakları', trendyol: 'Yayında', hepsiburada: 'Yayında' },
  { id: 2, name: 'Minik Mutfak Seti', sku: 'TOY-KITCHEN-014', barcode: '8690000000018', image: 'https://images.unsplash.com/photo-1594784056035-7f95fbcf6f5b?auto=format&fit=crop&w=160&q=80', stock: 8, price: '529,00 TL', age: '3+ yaş', ce: true, category: 'Rol Yapma Oyuncakları', trendyol: 'Bekliyor', hepsiburada: 'Taslak' },
  { id: 3, name: 'Ahşap Hayvanlar Puzzle', sku: 'TOY-PUZZLE-022', barcode: '8690000000025', image: 'https://images.unsplash.com/photo-1607453998774-d533f65dac99?auto=format&fit=crop&w=160&q=80', stock: 42, price: '189,50 TL', age: '2–5 yaş', ce: true, category: 'Puzzle & Eğitici', trendyol: 'Yayında', hepsiburada: 'Yayında' },
  { id: 4, name: 'Uzay Kaşifleri Roketi', sku: 'TOY-SPACE-008', barcode: '8690000000032', image: 'https://images.unsplash.com/photo-1560961911-ba7ef651a56c?auto=format&fit=crop&w=160&q=80', stock: 0, price: '749,90 TL', age: '6+ yaş', ce: false, category: 'Figür & Araç', trendyol: 'Taslak', hepsiburada: 'Bekliyor' },
]

function App() {
  const [selected, setSelected] = useState<number[]>([1, 2])
  const [query, setQuery] = useState('')
  const [activeProduct, setActiveProduct] = useState<Product>(products[0])
  const [toast, setToast] = useState('')
  const [showForm, setShowForm] = useState(true)
  const filteredProducts = useMemo(() => products.filter((product) => product.name.toLocaleLowerCase('tr').includes(query.toLocaleLowerCase('tr')) || product.barcode.includes(query)), [query])

  const toggleSelected = (id: number) => setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])
  const triggerSend = (channel: string) => {
    setToast(`${selected.length} ürün ${channel} kuyruğuna alındı`)
    window.setTimeout(() => setToast(''), 2800)
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark"><span className="brand-shape">✦</span><span>oyuncak<br /><b>akış</b></span></div>
        <div className="workspace-switcher"><span className="workspace-dot" /> ToyStore Türkiye <ChevronDown size={14} /></div>
        <nav>
          <p className="nav-label">ÇALIŞMA ALANI</p>
          <a className="nav-item active"><LayoutDashboard size={18} /> Genel Bakış</a>
          <a className="nav-item"><Package size={18} /> Ürünler <span className="nav-count">128</span></a>
          <a className="nav-item"><Truck size={18} /> Gönderim Kuyruğu <span className="nav-count orange">6</span></a>
          <a className="nav-item"><ShoppingBag size={18} /> Pazaryerleri</a>
          <p className="nav-label second">YÖNETİM</p>
          <a className="nav-item"><Settings size={18} /> Ayarlar</a>
          <a className="nav-item"><CircleHelp size={18} /> Yardım Merkezi</a>
        </nav>
        <div className="sidebar-bottom"><div className="sync-orb"><Sparkles size={15} /></div><div><strong>Her şey senkron</strong><span>Son kontrol 2 dk önce</span></div><ChevronRight size={16} /></div>
      </aside>

      <main className="main-content">
        <header className="topbar"><div className="breadcrumb"><span>Çalışma alanı</span><ChevronRight size={14} /><b>Ürünler</b></div><div className="top-actions"><button className="icon-button" title="Bildirimler"><Bell size={19} /><i /></button><div className="avatar">AY</div><div className="user-name">Ayşe Yılmaz <ChevronDown size={14} /></div></div></header>
        <section className="page-heading"><div><p className="eyebrow">KATALOG YÖNETİMİ</p><h1>Ürünler <span>·</span> <em>{products.length} kayıt</em></h1><p className="subheading">Oyuncak kataloğunuzu tek yerden yönetin, pazaryerlerine hazır tutun.</p></div><button className="primary-button" onClick={() => setShowForm(true)}><Plus size={18} /> Yeni ürün ekle</button></section>
        <section className="metrics"><div className="metric-card"><span className="metric-icon peach"><Package size={18} /></span><div><strong>128</strong><span>Toplam ürün</span></div><b className="metric-up">+12%</b></div><div className="metric-card"><span className="metric-icon mint"><Send size={18} /></span><div><strong>116</strong><span>Pazaryerinde aktif</span></div><b className="metric-up">+8%</b></div><div className="metric-card"><span className="metric-icon yellow"><Truck size={18} /></span><div><strong>6</strong><span>İşlem bekliyor</span></div><b className="metric-warn">İncele</b></div><div className="metric-card"><span className="metric-icon lilac"><Sparkles size={18} /></span><div><strong>2</strong><span>Dikkat gereken</span></div><b className="metric-warn">Düzelt</b></div></section>

        <section className="workspace-grid">
          <div className="catalog-panel">
            <div className="panel-toolbar"><div className="search-box"><Search size={17} /><input placeholder="Ürün, barkod veya SKU ara..." value={query} onChange={(event) => setQuery(event.target.value)} /></div><button className="filter-button"><Filter size={16} /> Filtrele <ChevronDown size={14} /></button><button className="more-button">•••</button></div>
            <div className="bulk-bar"><label><input type="checkbox" checked={selected.length === products.length} onChange={() => setSelected(selected.length === products.length ? [] : products.map((product) => product.id))} /> <span>{selected.length ? `${selected.length} ürün seçildi` : 'Ürün seç'}</span></label>{selected.length > 0 && <div className="bulk-actions"><button onClick={() => triggerSend('Trendyol')}><Send size={15} /> Trendyol'a gönder</button><button onClick={() => triggerSend('Hepsiburada')}><Send size={15} /> Hepsiburada'ya gönder</button></div>}</div>
            <div className="table-wrap"><table><thead><tr><th className="check-col" /><th>ÜRÜN</th><th>BARKOD / SKU</th><th>STOK</th><th>FİYAT</th><th>PAZARYERİ DURUMU</th><th /></tr></thead><tbody>{filteredProducts.map((product) => <tr key={product.id} className={activeProduct.id === product.id ? 'row-active' : ''} onClick={() => { setActiveProduct(product); setShowForm(true) }}><td onClick={(event) => event.stopPropagation()}><input type="checkbox" checked={selected.includes(product.id)} onChange={() => toggleSelected(product.id)} /></td><td><div className="product-cell"><img src={product.image} alt="" /><div><strong>{product.name}</strong><span>{product.category}</span></div></div></td><td><strong className="mono">{product.barcode}</strong><span className="table-muted">{product.sku}</span></td><td><span className={product.stock === 0 ? 'stock out' : product.stock < 10 ? 'stock low' : 'stock'}>{product.stock === 0 ? 'Tükendi' : `${product.stock} adet`}</span></td><td><strong>{product.price}</strong></td><td><div className="channel-status"><StatusPill status={product.trendyol} label="Trendyol" /><StatusPill status={product.hepsiburada} label="Hepsiburada" /></div></td><td><ChevronRight size={17} className="row-arrow" /></td></tr>)}</tbody></table></div><div className="table-footer"><span>1–{filteredProducts.length} / {products.length} ürün gösteriliyor</span><div><button disabled>‹</button><button className="page-active">1</button><button>2</button><button>›</button></div></div>
          </div>
          {showForm && <ProductForm product={activeProduct} onClose={() => setShowForm(false)} />}
        </section>
      </main>
      {toast && <div className="toast"><span>✓</span>{toast}</div>}
    </div>
  )
}

function StatusPill({ status, label }: { status: ChannelStatus; label: string }) { return <span className={`status ${status === 'Yayında' ? 'live' : status === 'Taslak' ? 'draft' : 'waiting'}`}><i />{label}</span> }

function ProductForm({ product, onClose }: { product: Product; onClose: () => void }) {
  return <aside className="edit-panel"><div className="edit-head"><div><p className="eyebrow">ÜRÜN DETAYI</p><h2>{product.name}</h2><span className="edit-sku">{product.sku}</span></div><button className="close-button" onClick={onClose}><X size={18} /></button></div><div className="form-scroll"><div className="form-section"><div className="section-title"><span>01</span><div><h3>Temel bilgiler</h3><p>Ürünün pazaryerlerindeki ortak bilgileri.</p></div></div><label>Ürün adı<input defaultValue={product.name} /></label><div className="two-fields"><label>Barkod<input defaultValue={product.barcode} /></label><label>Marka<input defaultValue="ToyStore" /></label></div><label>Açıklama<textarea defaultValue="Çocukların yaratıcılığını geliştiren renkli yapı blokları." /></label></div><div className="form-section"><div className="section-title"><span>02</span><div><h3>Oyuncak özellikleri</h3><p>Eksiksiz alanlar, hızlı onay demek.</p></div></div><div className="two-fields"><label>Yaş grubu<select defaultValue={product.age}><option>2–5 yaş</option><option>3–6 yaş</option><option>6+ yaş</option></select></label><label>Cinsiyet<select defaultValue="Unisex"><option>Unisex</option><option>Kız</option><option>Erkek</option></select></label></div><div className="two-fields"><label>Parça sayısı<input type="number" defaultValue="60" /></label><label>Materyal<input defaultValue="ABS Plastik" /></label></div><label className="toggle-label"><span><b>CE uygunluk işareti</b><small>Ürün güvenlik standartlarına uygun.</small></span><input type="checkbox" defaultChecked={product.ce} /><i className="toggle" /></label></div><div className="form-section mapping-section"><div className="section-title"><span>03</span><div><h3>Pazaryeri eşleme</h3><p>Kategoriyi her kanala ayrı tanımlayın.</p></div></div><div className="mapping-row"><div className="market-logo trendyol-logo">T</div><div><strong>Trendyol</strong><span>Oyuncak &gt; Yapı Oyuncakları</span></div><button className="mapping-edit">Düzenle</button></div><div className="mapping-row"><div className="market-logo hb-logo">h</div><div><strong>Hepsiburada</strong><span>Oyuncak &gt; Yapı Setleri</span></div><button className="mapping-edit">Düzenle</button></div></div></div><div className="form-footer"><button className="secondary-button" onClick={onClose}>Vazgeç</button><button className="save-button">Değişiklikleri kaydet</button></div></aside>
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
