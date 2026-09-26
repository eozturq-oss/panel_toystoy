import { type FormEvent } from 'react'
import { X } from 'lucide-react'
import type { Product } from './main'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

type ProductFormProps = {
  product: Product
  onClose: () => void
  onSave: (product: Product) => void
}

export default function ProductForm({ product, onClose, onSave }: ProductFormProps) {
  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    const payload = {
      title: String(values.get('title') ?? product.name),
      description: String(values.get('description') ?? ''),
      brand: String(values.get('brand') ?? ''),
      material: String(values.get('material') ?? ''),
      age_group: String(values.get('age_group') ?? ''),
      min_age_months: Number(values.get('min_age_months') ?? 0),
      gender: String(values.get('gender') ?? ''),
      piece_count: Number(values.get('piece_count') ?? 1),
      ce_compliant: values.get('ce_compliant') === 'on',
      safety_warning: String(values.get('safety_warning') ?? ''),
      barcode: String(values.get('barcode') ?? ''),
      sale_price: Number(String(values.get('sale_price') ?? '0').replace(',', '.')),
      stock_quantity: Number(values.get('stock_quantity') ?? 0),
    }

    const response = await fetch(product.backendId ? `${API_BASE}/api/products/${product.backendId}` : `${API_BASE}/api/products`, {
      method: product.backendId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, product_code: product.sku, sku: product.sku, desi: 1 }),
    })
    if (!response.ok) throw new Error('Ürün kaydedilemedi')
    const saved = await response.json() as Record<string, unknown>
    onSave({
      ...product,
      backendId: String(saved.id),
      sku: String(saved.sku),
      name: String(saved.title),
      barcode: String(saved.barcode),
      stock: Number(saved.stock_quantity),
      price: `${Number(saved.sale_price).toFixed(2)} TL`,
      age: String(saved.age_group),
      ce: Boolean(saved.ce_compliant),
      material: String(saved.material),
      gender: String(saved.gender),
      safetyWarning: String(saved.safety_warning),
    })
  }

  return (
    <form onSubmit={handleSubmit}>
      <aside className="edit-panel">
        <div className="edit-head">
          <div><p className="eyebrow">ÜRÜN DETAYI</p><h2>{product.name}</h2><span className="edit-sku">{product.sku}</span></div>
          <button type="button" className="close-button" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="form-scroll">
          <div className="form-section">
            <div className="section-title"><span>01</span><div><h3>Temel bilgiler</h3><p>Ürünün pazaryerlerindeki ortak bilgileri.</p></div></div>
            <label>Ürün adı<input name="title" defaultValue={product.name} required /></label>
            <div className="two-fields"><label>Barkod<input name="barcode" defaultValue={product.barcode} required /></label><label>Marka<input name="brand" defaultValue={product.brand ?? 'ToyStore'} required /></label></div>
            <label>Açıklama<textarea name="description" defaultValue={product.description ?? ''} /></label>
          </div>
          <div className="form-section">
            <div className="section-title"><span>02</span><div><h3>Oyuncak özellikleri</h3><p>Trendyol zorunlu nitelikleri.</p></div></div>
            <div className="two-fields"><label>Yaş grubu<select name="age_group" defaultValue={(product.ageGroup ?? product.age).replace('–', '-').replace('Yaş', 'yaş')} required><option>0-3 yaş</option><option>2-5 yaş</option><option>3-6 yaş</option><option>6+ yaş</option></select></label><label>Cinsiyet<select name="gender" defaultValue={product.gender ?? 'Unisex'} required><option>Unisex</option><option>Kız</option><option>Erkek</option></select></label></div>
            <div className="two-fields"><label>Parça sayısı<input name="piece_count" type="number" min="1" defaultValue={product.pieceCount ?? 1} required /></label><label>Materyal<input name="material" defaultValue={product.material ?? 'ABS Plastik'} required /></label></div>
            <div className="two-fields"><label>Minimum yaş (ay)<input name="min_age_months" type="number" min="0" defaultValue={product.minAgeMonths ?? 36} required /></label><label>Stok<input name="stock_quantity" type="number" min="0" defaultValue={product.stock} required /></label></div>
            <label>Uyarı metinleri<textarea name="safety_warning" defaultValue={product.safetyWarning ?? '3 yaş altı çocuklar için uygun değildir. Küçük parça içerir.'} required /></label>
            <label>Satış fiyatı<input name="sale_price" type="number" min="0.01" step="0.01" defaultValue={product.price.replace(' TL', '').replace(',', '.')} required /></label>
            <label className="toggle-label"><span><b>CE uygunluk işareti</b><small>Ürün güvenlik standartlarına uygun.</small></span><input name="ce_compliant" type="checkbox" defaultChecked={product.ce} /><i className="toggle" /></label>
          </div>
          <div className="form-section mapping-section"><div className="section-title"><span>03</span><div><h3>Pazaryeri eşleme</h3><p>Kategoriyi her kanala ayrı tanımlayın.</p></div></div><div className="mapping-row"><div className="market-logo trendyol-logo">T</div><div><strong>Trendyol</strong><span>Oyuncak &gt; Yapı Oyuncakları</span></div><button type="button" className="mapping-edit">Düzenle</button></div><div className="mapping-row"><div className="market-logo hb-logo">H</div><div><strong>Hepsiburada</strong><span>Oyuncak &gt; Eğitici Oyuncaklar</span></div><button type="button" className="mapping-edit">Düzenle</button></div></div>
        </div>
        <div className="form-footer"><button type="button" className="secondary-button" onClick={onClose}>Vazgeç</button><button type="submit" className="save-button">Değişiklikleri kaydet</button></div>
      </aside>
    </form>
  )
}
