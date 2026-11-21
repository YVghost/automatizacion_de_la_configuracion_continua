const $ = s => document.querySelector(s);
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw Error(typeof data.detail === 'string' ? data.detail : 'Revisa los campos y vuelve a intentarlo.');
  return data;
}
function message(text) { $('#status').textContent = text; }
async function refresh() {
  const [bikes, reviews, stats] = await Promise.all(['/api/bikes','/api/reviews','/api/stats'].map(p => api(p)));
  $('#bike-count').textContent = stats.bikes;
  $('#review-count').textContent = stats.reviews;
  $('#rating-average').textContent = stats.rating;
  $('#bike-select').innerHTML = '<option value="">Elige una bicicleta</option>' + bikes.map(b => `<option value="${b.id}">${escapeHTML(b.name)} · ${escapeHTML(b.owner)}</option>`).join('');
  $('#bikes').innerHTML = bikes.length ? bikes.map(b => `<article class="card bike-card"><span class="tag">${escapeHTML(b.category)}</span><h3>${escapeHTML(b.name)}</h3><span class="muted">Ciclista · ${escapeHTML(b.owner)}</span></article>`).join('') : '<p class="empty">Tu garaje está listo.<br>Registra la primera bicicleta para comenzar.</p>';
  $('#reviews').innerHTML = reviews.length ? reviews.map(r => `<article class="card review-card">${r.photo_url ? `<img src="${r.photo_url}" alt="Foto de ${escapeHTML(r.accessory)}" loading="lazy">` : ''}<div class="stars" aria-label="${r.rating} de 5">${'★'.repeat(r.rating)}${'☆'.repeat(5-r.rating)}</div><h3>${escapeHTML(r.accessory)}</h3><p>${escapeHTML(r.comment)}</p><small>${escapeHTML(r.owner)} · ${escapeHTML(r.bike)}</small></article>`).join('') : '<p class="empty">Cada kilómetro enseña algo.<br>Comparte tu primera reseña.</p>';
}
function bind(form, save, success) {
  $(form).addEventListener('submit', async event => {
    event.preventDefault(); const button = event.target.querySelector('button'); button.disabled = true;
    try { await save(new FormData(event.target)); event.target.reset(); await refresh(); message(success); }
    catch (error) { message(error.message); } finally { button.disabled = false; }
  });
}
bind('#bike-form', data => api('/api/bikes', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(data))}), 'Bicicleta registrada. ¡A rodar!');
bind('#review-form', data => api('/api/reviews', {method:'POST',body:data}), 'Tu reseña ya está en la comunidad.');
refresh().catch(() => message('No se pudo conectar con la API. Intenta recargar la página.'));
