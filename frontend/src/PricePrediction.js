import React, { useState, useEffect } from 'react';
import axios from 'axios';

// Human-readable labels for raw DB enum values
const GEAR_LABELS = { AT: 'Automatic', MT: 'Manual', DSG: 'Dual-clutch (DSG)', CVT: 'CVT' };
const COLOR_LABELS = {
  white: 'White', black: 'Black', silver: 'Silver', grey: 'Grey',
  blue: 'Blue', red: 'Red', green: 'Green', yellow: 'Yellow',
};
const BODY_LABELS = {
  'Седан': 'Sedan', 'Хэтчбек': 'Hatchback', 'Внедорожник': 'SUV',
  'Универсал': 'Wagon', 'Купе': 'Coupe', 'Минивэн': 'Minivan',
  'Пикап': 'Pickup', 'Кабриолет': 'Convertible', 'Другой': 'Other',
};

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: CURRENT_YEAR - 1989 }, (_, i) => CURRENT_YEAR - i);

const s = {
  page:    { padding: '24px 20px', maxWidth: 660, margin: '0 auto', fontFamily: 'Amazon Ember, Arial, sans-serif' },
  title:   { fontWeight: 700, fontSize: '1.5rem', marginBottom: 24, color: '#222' },
  grid:    { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 24px' },
  label:   { display: 'block', marginBottom: 5, fontSize: 14, fontWeight: 600, color: '#444' },
  req:     { color: '#c0392b', marginLeft: 2 },
  input:   { width: '100%', padding: '9px 12px', marginBottom: 16, borderRadius: 6, border: '1px solid #ccc', fontSize: 15, boxSizing: 'border-box' },
  inputErr:{ width: '100%', padding: '9px 12px', marginBottom: 4,  borderRadius: 6, border: '1px solid #c0392b', fontSize: 15, boxSizing: 'border-box' },
  errMsg:  { color: '#c0392b', fontSize: 12, marginBottom: 12 },
  btn:     { padding: '11px 32px', cursor: 'pointer', background: 'linear-gradient(90deg,#2874f0,#0057b8)', color: '#fff', border: 'none', borderRadius: 20, fontWeight: 700, fontSize: 15, boxShadow: '0 2px 6px rgba(40,116,240,.2)', transition: 'opacity .15s', marginTop: 8 },
  btnDisabled: { opacity: 0.6, cursor: 'not-allowed' },
  result:  { marginTop: 28, padding: 20, background: '#f0f7ff', borderRadius: 10, border: '1px solid #c3d9f7' },
  price:   { fontSize: '1.7rem', fontWeight: 800, color: '#0057b8', margin: '0 0 4px' },
  sub:     { fontSize: 13, color: '#666', marginBottom: 16 },
  similar: { marginTop: 12 },
  simTitle:{ fontWeight: 700, fontSize: 14, color: '#444', marginBottom: 8 },
  simRow:  { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #e0ecff', fontSize: 14 },
  simPrice:{ fontWeight: 700, color: '#0057b8', whiteSpace: 'nowrap', marginLeft: 12 },
  simMeta: { color: '#555' },
  simLink: { color: '#2874f0', textDecoration: 'none', fontSize: 12, marginLeft: 8 },
};

function Field({ label, required, error, children }) {
  return (
    <div>
      <label style={s.label}>{label}{required && <span style={s.req}>*</span>}</label>
      {children}
      {error && <p style={s.errMsg}>{error}</p>}
    </div>
  );
}

export default function PricePrediction() {
  const [form, setForm] = useState({
    year: '', mileage: '', brand: '', model: '',
    gear_type: '', color: '', fuel_type: '', body_type: '',
  });
  const [errors, setErrors]           = useState({});
  const [loading, setLoading]         = useState(false);
  const [prediction, setPrediction]   = useState(null);
  const [similar, setSimilar]         = useState([]);
  const [brandModels, setBrandModels] = useState({});
  const [dropdowns, setDropdowns]     = useState({ color: [], gear_type: [], fuel_type: [], body_type: [] });

  // Load brand→models map and other dropdown options on mount
  useEffect(() => {
    axios.get('/api/cars/brand-models/')
      .then(r => setBrandModels(r.data))
      .catch(e => console.error('brand-models fetch failed:', e));

    axios.get('/api/cars/dropdown-options/')
      .then(r => setDropdowns(r.data))
      .catch(e => console.error('dropdown-options fetch failed:', e));
  }, []);

  const brands  = Object.keys(brandModels).sort();
  const models  = form.brand ? (brandModels[form.brand] || []) : [];

  function handleChange(e) {
    const { name, value } = e.target;
    setForm(prev => {
      // When brand changes, reset model
      if (name === 'brand') return { ...prev, brand: value, model: '' };
      return { ...prev, [name]: value };
    });
    // Clear field-level error on change
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }));
  }

  function validate() {
    const e = {};
    if (!form.year)      e.year     = 'Required';
    if (!form.mileage)   e.mileage  = 'Required';
    if (!form.brand)     e.brand    = 'Required';
    if (!form.model)     e.model    = 'Required';
    if (form.year && (parseInt(form.year) < 1990 || parseInt(form.year) > CURRENT_YEAR))
      e.year = `Year must be 1990 – ${CURRENT_YEAR}`;
    if (form.mileage && parseInt(form.mileage) < 0)
      e.mileage = 'Mileage cannot be negative';
    return e;
  }

  async function handlePredict() {
    const e = validate();
    if (Object.keys(e).length) { setErrors(e); return; }

    setLoading(true);
    setPrediction(null);
    setSimilar([]);

    try {
      const body = {
        year:      parseInt(form.year),
        mileage:   parseInt(form.mileage),
        brand:     form.brand,
        model:     form.model,
        gear_type: form.gear_type  || 'Unknown',
        color:     form.color      || 'Unknown',
        fuel_type: form.fuel_type  || 'Unknown',
        body_type: form.body_type  || 'Unknown',
      };

      const [predRes, simRes] = await Promise.all([
        fetch('/predict2', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }),
        axios.get('/api/cars/filtered-list/', {
          params: {
            brand: form.brand,
            model: form.model,
            ...(form.year ? {
              year: `${Math.max(1990, parseInt(form.year) - 2)}-${parseInt(form.year) + 2}`
            } : {}),
          },
        }),
      ]);

      if (!predRes.ok) throw new Error(`predict2 returned ${predRes.status}`);
      const predData = await predRes.json();
      setPrediction(predData.predicted_price);

      // Pick up to 5 closest by mileage to what the user entered
      const allResults = simRes.data?.results || [];
      const userMileage = parseInt(form.mileage);
      const closest = [...allResults]
        .filter(c => c.price)
        .sort((a, b) =>
          Math.abs((a.mileage || 0) - userMileage) -
          Math.abs((b.mileage || 0) - userMileage)
        )
        .slice(0, 5);
      setSimilar(closest);

    } catch (err) {
      console.error(err);
      setErrors({ _global: 'Prediction failed — please try again.' });
    } finally {
      setLoading(false);
    }
  }

  function inputStyle(name) {
    return errors[name] ? s.inputErr : s.input;
  }

  const btnStyle = loading
    ? { ...s.btn, ...s.btnDisabled }
    : s.btn;

  return (
    <div style={s.page}>
      <h2 style={s.title}>Predict Car Price</h2>

      <div style={s.grid}>
        <Field label="Year" required error={errors.year}>
          <select name="year" value={form.year} onChange={handleChange} style={inputStyle('year')}>
            <option value="">Select year</option>
            {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </Field>

        <Field label="Mileage (km)" required error={errors.mileage}>
          <input
            type="number" name="mileage" value={form.mileage}
            onChange={handleChange} style={inputStyle('mileage')}
            placeholder="e.g. 75000" min="0"
          />
        </Field>

        <Field label="Brand" required error={errors.brand}>
          <select name="brand" value={form.brand} onChange={handleChange} style={inputStyle('brand')}>
            <option value="">Select brand</option>
            {brands.map(b => <option key={b} value={b}>{b}</option>)}
          </select>
        </Field>

        <Field label="Model" required error={errors.model}>
          <select
            name="model" value={form.model} onChange={handleChange}
            style={inputStyle('model')} disabled={!form.brand}
          >
            <option value="">{form.brand ? 'Select model' : 'Select brand first'}</option>
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </Field>

        <Field label="Gear type">
          <select name="gear_type" value={form.gear_type} onChange={handleChange} style={s.input}>
            <option value="">Any / Unknown</option>
            {(dropdowns.gear_type || []).map(v => (
              <option key={v} value={v}>{GEAR_LABELS[v] || v}</option>
            ))}
          </select>
        </Field>

        <Field label="Fuel type">
          <select name="fuel_type" value={form.fuel_type} onChange={handleChange} style={s.input}>
            <option value="">Any / Unknown</option>
            {(dropdowns.fuel_type || []).map(v => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </Field>

        <Field label="Color">
          <select name="color" value={form.color} onChange={handleChange} style={s.input}>
            <option value="">Any / Unknown</option>
            {(dropdowns.color || []).map(v => (
              <option key={v} value={v}>{COLOR_LABELS[v] || v}</option>
            ))}
          </select>
        </Field>

        <Field label="Body type">
          <select name="body_type" value={form.body_type} onChange={handleChange} style={s.input}>
            <option value="">Any / Unknown</option>
            {(dropdowns.body_type || []).map(v => (
              <option key={v} value={v}>{BODY_LABELS[v] || v}</option>
            ))}
          </select>
        </Field>
      </div>

      {errors._global && <p style={{ ...s.errMsg, fontSize: 14, marginBottom: 8 }}>{errors._global}</p>}

      <button onClick={handlePredict} disabled={loading} style={btnStyle}>
        {loading ? 'Predicting…' : 'Predict Price'}
      </button>

      {prediction !== null && (
        <div style={s.result}>
          <p style={s.price}>${prediction.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</p>
          <p style={s.sub}>Estimated market price · based on {form.brand} {form.model} listings</p>

          {similar.length > 0 && (
            <div style={s.similar}>
              <p style={s.simTitle}>Similar listings in database ({similar.length} shown)</p>
              {similar.map((car, i) => (
                <div key={i} style={s.simRow}>
                  <span style={s.simMeta}>
                    {car.year} · {car.mileage ? car.mileage.toLocaleString() + ' km' : '— km'}
                    {car.location ? ` · ${car.location}` : ''}
                    {car.created_at ? ` · ${car.created_at}` : ''}
                  </span>
                  <span>
                    <span style={s.simPrice}>${Number(car.price).toLocaleString('en-US', { maximumFractionDigits: 0 })}</span>
                    {car.reference_url && (
                      <a href={car.reference_url} target="_blank" rel="noreferrer" style={s.simLink}>view ↗</a>
                    )}
                  </span>
                </div>
              ))}
            </div>
          )}

          {similar.length === 0 && (
            <p style={{ ...s.sub, marginTop: 8 }}>No closely matching listings found in the database.</p>
          )}
        </div>
      )}
    </div>
  );
}
