/**
 * Service API client pour interroger les endpoints de l'Observatoire Énergétique
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

async function fetchJson(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        ...options.headers,
      },
      ...options,
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`Erreur lors de l'appel à ${endpoint}:`, err);
    throw err;
  }
}

export const energyApi = {
  getHealth: () => fetchJson('/api/v1/health'),
  getLatestMetrics: () => fetchJson('/api/v1/metrics/latest'),
  getMixHistory: (limit = 96, startDate, endDate) => {
    const params = new URLSearchParams({ limit });
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    return fetchJson(`/api/v1/mix/history?${params.toString()}`);
  },
  getMonthlyMix: (year, limit = 60) => {
    const params = new URLSearchParams({ limit });
    if (year) params.set('annee', year);
    return fetchJson(`/api/v1/mix/monthly?${params.toString()}`);
  },
  getRegionalCapacities: (regionCode, filiereCode, limit = 200) => {
    const params = new URLSearchParams({ limit });
    if (regionCode) params.set('code_region', regionCode);
    if (filiereCode) params.set('code_filiere', filiereCode);
    return fetchJson(`/api/v1/capacities/regional?${params.toString()}`);
  },
  getCapacitiesSummary: () => fetchJson('/api/v1/capacities/summary'),
  getInternationalAccess: (minYear, maxYear) => {
    const params = new URLSearchParams();
    if (minYear) params.set('annee_min', minYear);
    if (maxYear) params.set('annee_max', maxYear);
    const query = params.toString() ? `?${params.toString()}` : '';
    return fetchJson(`/api/v1/international/access${query}`);
  },
  getQualityReport: (refresh = false) => {
    return fetchJson(`/api/v1/quality/report?refresh=${refresh}`);
  },
};
