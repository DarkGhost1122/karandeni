/* ══════════════════════════════════════════════════
   Karandeni Investment – Central API Configuration
   Set this to your deployed backend URL.

   Local development:
     const API_BASE = 'http://localhost:5001';

   Production:
     const API_BASE = 'https://YOUR-APP-BACKEND.hf.space';
══════════════════════════════════════════════════ */
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:')
  ? 'http://localhost:5001'
  : 'https://asindu2004-leshloan.hf.space';
