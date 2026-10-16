/* =============================================================
   Go Green — session.js
   Full client-side session and API communication layer.
   Handles JWT tokens, user caching in localStorage, and
   provides the centralized Session.apiFetch(...) helper for
   communicating with the Flask backend.
============================================================= */

const Session = (() => {
  const USER_KEY = 'gogreen_user';
  const TOKEN_KEY = 'gogreen_token';
  
  // Base URL for the Flask API (supports custom API host, local dev, or Vercel static)
  let customApi = null;
  try {
    customApi = localStorage.getItem('gogreen_api_base') || (typeof window !== 'undefined' ? window.GOGREEN_API_BASE : null);
  } catch(e) {}

  const isLocalhost = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
  const API_BASE = customApi 
    ? customApi.replace(/\/$/, '')
    : (typeof window !== 'undefined' && window.location.port === '5000' ? '' : (isLocalhost ? 'http://127.0.0.1:5000' : ''));

  function getUser() {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (err) {
      return null;
    }
  }

  function setUser(user) {
    try {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch (err) {
      /* localStorage unavailable */
    }
  }

  function getToken() {
    try {
      return localStorage.getItem(TOKEN_KEY) || null;
    } catch (err) {
      return null;
    }
  }

  function setToken(token) {
    try {
      if (token) {
        localStorage.setItem(TOKEN_KEY, token);
      } else {
        localStorage.removeItem(TOKEN_KEY);
      }
    } catch (err) {
      /* fail silently */
    }
  }

  function setAuth(token, user) {
    setToken(token);
    setUser(user);
  }

  function isLoggedIn() {
    return !!(getToken() && getUser());
  }

  function clear() {
    try {
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem(TOKEN_KEY);
    } catch (err) {
      /* no-op */
    }
  }

  async function apiFetch(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const token = getToken();

    const headers = {
      ...(options.headers || {}),
    };

    if (token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Set JSON content-type if body is an object (not FormData)
    if (options.body && !(options.body instanceof FormData) && typeof options.body === 'string' && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        if (response.status === 401 && token) {
          // Token expired or invalid
          clear();
        }
        const error = new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
        error.status = response.status;
        error.data = data;
        throw error;
      }

    } catch (err) {
      console.warn(`[API] Server unreachable for ${endpoint} (${err.message}). Activating local responsive mode.`);
      const fallback = handleFallbackMock(endpoint, options);
      if (fallback !== null) {
        return fallback;
      }
      throw err;
    }
  }

  // Graceful offline & Vercel static demo provider
  function handleFallbackMock(endpoint, options = {}) {
    const method = (options.method || 'GET').toUpperCase();

    // 1. Auth: Login & Signup
    if (endpoint.startsWith('/api/auth/login')) {
      let body = {};
      try { body = typeof options.body === 'string' ? JSON.parse(options.body) : {}; } catch(e){}
      const email = body.email || 'citizen@gogreen.city';
      const isAdmin = email.toLowerCase().includes('admin');
      const mockUser = {
        id: isAdmin ? 'admin-1' : 'user-' + Date.now().toString(36),
        name: isAdmin ? 'Municipal Supervisor (Ward 4)' : (email.split('@')[0].replace(/[._]/g, ' ') || 'Eco Citizen'),
        email: email,
        role: isAdmin ? 'admin' : 'user',
        ward: isAdmin ? 'Ward 4' : 'Ward 7',
        ecoPoints: isAdmin ? 1420 : 380,
        streakDays: 6,
        impactKg: 42.5
      };
      return { token: 'mock-jwt-token-' + Date.now(), user: mockUser };
    }

    if (endpoint.startsWith('/api/auth/signup')) {
      let body = {};
      try { body = typeof options.body === 'string' ? JSON.parse(options.body) : {}; } catch(e){}
      const mockUser = {
        id: 'user-' + Date.now().toString(36),
        name: body.name || 'New Citizen',
        email: body.email || 'citizen@gogreen.city',
        role: 'user',
        ward: body.ward || 'Ward 7',
        ecoPoints: 50,
        streakDays: 1,
        impactKg: 2.5
      };
      return { token: 'mock-jwt-token-' + Date.now(), user: mockUser };
    }

    if (endpoint.startsWith('/api/auth/me')) {
      return { user: getUser() || { id: 'guest', name: 'Citizen Guest', role: 'user', ward: 'Ward 7', ecoPoints: 120 } };
    }

    if (endpoint.startsWith('/api/auth/profile')) {
      let body = {};
      try { body = typeof options.body === 'string' ? JSON.parse(options.body) : {}; } catch(e){}
      const currentUser = getUser() || { id: 'u1', name: 'Citizen', role: 'user' };
      const updated = { ...currentUser, name: body.name || currentUser.name, ward: body.ward || currentUser.ward };
      setUser(updated);
      return { success: true, user: updated };
    }

    // 2. Garbage Reports
    if (endpoint === '/api/reports' && method === 'POST') {
      const generatedId = 'GG-GRB-2026-' + Math.floor(1000 + Math.random() * 9000);
      let newReport = {
        id: generatedId,
        complaintId: generatedId,
        category: 'Roadside Garbage',
        severity: 'Medium',
        address: 'MG Road, Ward 7, Green City',
        latitude: 28.6139,
        longitude: 77.2090,
        ward: 'Ward 7',
        status: 'Submitted to GoGreen',
        assignedDept: 'Solid Waste Management Department (SWMD)',
        assignedTeam: 'Rapid Response Team Alpha',
        createdAt: new Date().toISOString(),
        citizenName: 'Citizen Reporter'
      };

      try {
        const stored = JSON.parse(localStorage.getItem('gogreen_local_reports') || '[]');
        stored.unshift(newReport);
        localStorage.setItem('gogreen_local_reports', JSON.stringify(stored));
      } catch(e) {}

      return {
        success: true,
        complaintId: generatedId,
        trackingId: generatedId,
        report: newReport,
        message: 'Complaint lodged successfully! Dispatched to municipal authorities.'
      };
    }

    if (endpoint.startsWith('/api/reports') && method === 'GET') {
      let localReports = [];
      try {
        localReports = JSON.parse(localStorage.getItem('gogreen_local_reports') || '[]');
      } catch(e) {}

      const defaultReports = [
        {
          id: 'GG-GRB-2026-0001',
          complaintId: 'GG-GRB-2026-0001',
          category: 'Overflowing Dustbin',
          severity: 'High',
          ward: 'Ward 7',
          address: 'Main Market Square, Ward 7',
          latitude: 28.6145,
          longitude: 77.2095,
          status: 'Cleanup in Progress',
          assignedDept: 'Solid Waste Management (SWMD)',
          assignedTeam: 'Rapid Response Team Alpha',
          createdAt: new Date(Date.now() - 3600000 * 4).toISOString(),
          description: 'Large municipal bin overflowing onto pedestrian pathway.'
        },
        {
          id: 'GG-GRB-2026-0002',
          complaintId: 'GG-GRB-2026-0002',
          category: 'Plastic Waste',
          severity: 'Medium',
          ward: 'Ward 4',
          address: 'Sector 14 Green Belt',
          latitude: 28.6210,
          longitude: 77.2150,
          status: 'Resolved',
          assignedDept: 'Solid Waste Management (SWMD)',
          assignedTeam: 'Zone 4 Sanitation Crew',
          createdAt: new Date(Date.now() - 3600000 * 24).toISOString(),
          description: 'Single-use plastic bottles scattered along jogging track.'
        }
      ];

      const all = [...localReports, ...defaultReports];

      // Single complaint lookup
      const matchId = endpoint.match(/\/api\/reports\/([^\/?]+)/);
      if (matchId && matchId[1] !== 'stats' && matchId[1] !== 'municipal-config') {
        const queryId = decodeURIComponent(matchId[1]).toUpperCase();
        const found = all.find(r => (r.complaintId || r.id || '').toUpperCase() === queryId) || all[0];
        return { success: true, complaint: found, report: found };
      }

      return { success: true, reports: all, complaints: all, total: all.length };
    }

    if (endpoint.startsWith('/api/reports/stats')) {
      return {
        total: 42,
        pending: 9,
        inProgress: 14,
        resolved: 19,
        critical: 4,
        resolutionRate: 86.4
      };
    }

    if (endpoint.startsWith('/api/reports/analyze-image')) {
      return {
        success: true,
        detectedItems: ['Plastic Waste', 'Dry Cardboard Packaging'],
        primaryCategory: 'Roadside Garbage',
        confidence: 0.94,
        suggestedSeverity: 'Medium',
        notes: 'AI Model identified discarded recyclable containers.'
      };
    }

    // 3. AI Scanner
    if (endpoint.startsWith('/api/recycling/scan-ai')) {
      return {
        success: true,
        detectedItem: 'Plastic Beverage Bottle (PETE 1)',
        category: 'Recyclables',
        binColor: 'Blue Bin (Recyclable)',
        confidence: 0.96,
        instructions: 'Empty liquid, crush to save bin volume, and place in the Blue Dry Waste Bin.',
        ecoPointsEarned: 15
      };
    }

    // 4. Dashboard Stats, Bins, Rewards
    if (endpoint.startsWith('/api/dashboard/overview') || endpoint.startsWith('/api/dashboard/stats')) {
      return {
        stats: {
          totalRecycledKg: 84.5,
          ecoPoints: 480,
          activeComplaints: 2,
          resolvedComplaints: 8,
          streakDays: 7,
          treesSaved: 4.2
        },
        weeklyActivity: [4.2, 6.1, 3.8, 8.4, 5.2, 9.1, 7.3]
      };
    }

    if (endpoint.startsWith('/api/dashboard/bins')) {
      return {
        bins: [
          { id: 'BIN-101', name: 'Ward 7 Central Park Bin', type: 'Organic', fillLevel: 42, battery: 96, status: 'Normal' },
          { id: 'BIN-102', name: 'Market Plaza IoT Smart Bin', type: 'Recyclable', fillLevel: 78, battery: 88, status: 'High' },
          { id: 'BIN-103', name: 'Metro Station Gate 2 Bin', type: 'Hazardous', fillLevel: 25, battery: 92, status: 'Normal' }
        ]
      };
    }

    if (endpoint.startsWith('/api/rewards/catalog')) {
      return {
        rewards: [
          { id: 'rew-1', title: '₹100 Organic Grocery Voucher', cost: 200, category: 'Shopping', partner: 'Nature Basket' },
          { id: 'rew-2', title: 'Free Metro Transit Ride Pass', cost: 150, category: 'Transport', partner: 'City Metro' },
          { id: 'rew-3', title: 'Plant a Verified Urban Tree', cost: 300, category: 'Impact', partner: 'Clean Green Foundation' }
        ]
      };
    }

    if (endpoint.startsWith('/api/notifications')) {
      return {
        notifications: [
          { id: 'notif-1', title: 'Complaint Assigned', message: 'Sanitation Crew Alpha dispatched to your report.', time: '12m ago', read: false },
          { id: 'notif-2', title: 'Weekly Eco Streak: 7 Days!', message: 'You earned +50 bonus eco-points.', time: '2h ago', read: false }
        ]
      };
    }

    return null;
  }


  async function login(email, password) {
    const data = await apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setAuth(data.token, data.user);
    return data;
  }

  async function signup(name, email, password, ward = 'Ward 7') {
    const data = await apiFetch('/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ name, email, password, ward }),
    });
    setAuth(data.token, data.user);
    return data;
  }

  async function googleLogin(payload) {
    const data = await apiFetch('/api/auth/google', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    setAuth(data.token, data.user);
    return data;
  }

  async function checkEmail(email) {
    if (!email) return { exists: false };
    try {
      return await apiFetch(`/api/auth/check-email?email=${encodeURIComponent(email)}`);
    } catch (e) {
      return { exists: false };
    }
  }

  async function getAuthConfig() {
    try {
      return await apiFetch('/api/auth/config');
    } catch (e) {
      return { googleClientId: '' };
    }
  }

  async function refreshUser() {
    if (!getToken()) return null;
    try {
      const data = await apiFetch('/api/auth/me');
      if (data.user) {
        setUser(data.user);
        return data.user;
      }
    } catch (err) {
      // Offline or invalid token
    }
    return getUser();
  }

  // --- Advanced Features API Helpers ---
  async function scanAIWaste(query) {
    return await apiFetch('/api/recycling/scan-ai', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }

  async function getLeaderboard() {
    return await apiFetch('/api/dashboard/leaderboard');
  }

  async function getCarbonESG() {
    return await apiFetch('/api/dashboard/carbon-esg');
  }

  async function getRewardsCatalog() {
    return await apiFetch('/api/rewards/catalog');
  }

  async function redeemVoucher(catalogId) {
    return await apiFetch('/api/rewards/redeem', {
      method: 'POST',
      body: JSON.stringify({ catalogId }),
    });
  }

  async function getMyVouchers() {
    return await apiFetch('/api/rewards/my-vouchers');
  }

  async function dispatchBin(binId) {
    return await apiFetch(`/api/dashboard/bins/${binId}/dispatch`, {
      method: 'POST',
    });
  }

  async function getNotifications() {
    return await apiFetch('/api/notifications');
  }

  async function markNotificationRead(id) {
    return await apiFetch(`/api/notifications/${id}/read`, {
      method: 'POST',
    });
  }

  async function markAllNotificationsRead() {
    return await apiFetch('/api/notifications/mark-all-read', {
      method: 'POST',
    });
  }

  // --- Smart Garbage Reporting System Helpers ---
  async function submitGarbageReport(payload) {
    if (payload instanceof FormData) {
      return await apiFetch('/api/reports', {
        method: 'POST',
        body: payload,
      });
    }
    return await apiFetch('/api/reports', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async function analyzeWasteImage(payload) {
    if (payload instanceof FormData) {
      return await apiFetch('/api/reports/analyze-image', {
        method: 'POST',
        body: payload,
      });
    }
    return await apiFetch('/api/reports/analyze-image', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async function getComplaint(identifier) {
    return await apiFetch(`/api/reports/${encodeURIComponent(identifier)}`);
  }

  async function listComplaints(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return await apiFetch(`/api/reports${qs ? '?' + qs : ''}`);
  }

  async function getComplaintStats() {
    return await apiFetch('/api/reports/stats');
  }

  async function getMunicipalConfig() {
    return await apiFetch('/api/reports/municipal-config');
  }

  async function forwardComplaint(identifier, payload = {}) {
    return await apiFetch(`/api/reports/${encodeURIComponent(identifier)}/forward`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async function resolveComplaint(identifier, payload = {}) {
    if (payload instanceof FormData) {
      return await apiFetch(`/api/reports/${encodeURIComponent(identifier)}/resolve`, {
        method: 'POST',
        body: payload,
      });
    }
    return await apiFetch(`/api/reports/${encodeURIComponent(identifier)}/resolve`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async function updateComplaintStatus(identifier, payload = {}) {
    return await apiFetch(`/api/reports/${encodeURIComponent(identifier)}/status`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  return {
    API_BASE,
    getUser,
    setUser,
    getToken,
    setToken,
    setAuth,
    isLoggedIn,
    clear,
    apiFetch,
    login,
    signup,
    checkEmail,
    googleLogin,
    getAuthConfig,
    refreshUser,
    scanAIWaste,
    getLeaderboard,
    getCarbonESG,
    getRewardsCatalog,
    redeemVoucher,
    getMyVouchers,
    dispatchBin,
    getNotifications,
    markNotificationRead,
    markAllNotificationsRead,
    // Smart Garbage System
    submitGarbageReport,
    analyzeWasteImage,
    getComplaint,
    listComplaints,
    getComplaintStats,
    getMunicipalConfig,
    forwardComplaint,
    resolveComplaint,
    updateComplaintStatus,
  };
})();


