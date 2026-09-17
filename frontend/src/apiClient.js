import axios from 'axios';

const BACKEND =
  process.env.REACT_APP_BACKEND_URL || 'http://127.0.0.1:8001';

/** Instance Axios : base /api + en-tête X-API-KEY si REACT_APP_DEXTERIO_API_KEY est défini */
const api = axios.create({
  baseURL: `${BACKEND}/api`,
});

api.interceptors.request.use((config) => {
  const key = process.env.REACT_APP_DEXTERIO_API_KEY;
  if (key) {
    config.headers = config.headers || {};
    config.headers['X-API-KEY'] = key;
  }
  return config;
});

// The pages only log a failed request, so without this the UI would sit on
// "Loading…" forever when the backend is not running. A request that never
// reaches a server (no HTTP response) raises a window event; Layout shows it.
export const BACKEND_STATUS_EVENT = 'dexterio:backend-status';
api.interceptors.response.use(
  (response) => {
    window.dispatchEvent(new CustomEvent(BACKEND_STATUS_EVENT, { detail: { reachable: true } }));
    return response;
  },
  (error) => {
    if (!error.response) {
      window.dispatchEvent(new CustomEvent(BACKEND_STATUS_EVENT, { detail: { reachable: false } }));
    }
    return Promise.reject(error);
  }
);

export default api;

export const backendBaseUrl = BACKEND;

/** Entêtes fetch (backtests et liens de téléchargement) */
export function buildFetchHeaders(includeJson = false) {
  const h = {};
  if (includeJson) h['Content-Type'] = 'application/json';
  const key = process.env.REACT_APP_DEXTERIO_API_KEY;
  if (key) h['X-API-KEY'] = key;
  return h;
}
