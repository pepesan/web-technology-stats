// Autor: David Vaquero <pepesan@gmail.com>
// Licencia: GPL-3.0-only
async function get(path, params = {}) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== '') query.set(key, value)
  }
  const qs = query.toString()
  const res = await fetch(`/api/${path}${qs ? `?${qs}` : ''}`)
  if (!res.ok) throw new Error(`Error ${res.status} al consultar /api/${path}`)
  return res.json()
}

export const fetchBatches = () => get('batches')
export const fetchOverview = (batch, maxPosition) => get('overview', { batch, max_position: maxPosition })
export const fetchTopic = (topic, { batch, limit, category, maxPosition }) =>
  get(`topics/${topic}`, { batch, limit, category, max_position: maxPosition })
