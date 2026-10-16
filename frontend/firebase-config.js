/* =============================================================
   Go Green — firebase-config.js
   Standard Firebase Authentication with Google Popup Engine.
   Uses Firebase GoogleAuthProvider popup with 'select_account'
   to show the Google account chooser for all signed-in browser accounts,
   retrieves the verified Google user ID Token & profile,
   and synchronizes with the Flask backend (/api/auth/google).
============================================================= */
// Firebase Web API Key & Project Config:
const FIREBASE_MANUAL_CONFIG = {
  apiKey: "AIzaSyBf_anVktii3PIbmk8RcDpTSHuOxXVrdX0",
  authDomain: "go-green-bc487.firebaseapp.com",
  projectId: "go-green-bc487",
  storageBucket: "go-green-bc487.firebasestorage.app",
  messagingSenderId: "852086315506",
  appId: "1:852086315506:web:09e321eb5041cfbb70b36b",
  measurementId: "G-K2M3D84DJE"
};

const FirebaseAuth = (() => {
  let isInitialized = false;
  let authInstance = null;
  let googleProvider = null;
  let currentConfig = null;

  /* ---------------- Get Active Firebase Config ---------------- */
  async function resolveConfig() {
    let cfg = {
      apiKey: "AIzaSyBf_anVktii3PIbmk8RcDpTSHuOxXVrdX0",
      authDomain: "go-green-bc487.firebaseapp.com",
      projectId: "go-green-bc487",
      storageBucket: "go-green-bc487.firebasestorage.app",
      messagingSenderId: "852086315506",
      appId: "1:852086315506:web:09e321eb5041cfbb70b36b",
      measurementId: "G-K2M3D84DJE"
    };

    // 1. Check manual config in file
    if (FIREBASE_MANUAL_CONFIG.apiKey) {
      cfg = { ...cfg, ...FIREBASE_MANUAL_CONFIG };
    }

    // 2. Check localStorage
    try {
      const stored = localStorage.getItem('gogreen_firebase_config');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.apiKey) cfg = { ...cfg, ...parsed };
      }
      const storedKey = localStorage.getItem('gogreen_firebase_api_key');
      if (storedKey) {
        cfg.apiKey = storedKey;
      }
    } catch (e) { }

    // 3. Fetch config from Flask backend (/api/auth/config)
    if (typeof Session !== 'undefined' && (!cfg.apiKey || !cfg.projectId)) {
      try {
        const backendCfg = await Session.getAuthConfig();
        if (backendCfg && backendCfg.firebaseConfig) {
          if (backendCfg.firebaseConfig.apiKey) cfg.apiKey = backendCfg.firebaseConfig.apiKey;
          if (backendCfg.firebaseConfig.projectId) cfg.projectId = backendCfg.firebaseConfig.projectId;
          if (backendCfg.firebaseConfig.authDomain) cfg.authDomain = backendCfg.firebaseConfig.authDomain;
          if (backendCfg.firebaseConfig.appId) cfg.appId = backendCfg.firebaseConfig.appId;
        }
      } catch (e) { }
    }

    // 4. Default fallbacks if projectId or authDomain missing
    if (!cfg.projectId) cfg.projectId = 'gogreen-smart-waste';
    if (!cfg.authDomain) cfg.authDomain = `${cfg.projectId}.firebaseapp.com`;
    if (!cfg.storageBucket) cfg.storageBucket = `${cfg.projectId}.appspot.com`;

    return cfg;
  }

  /* ---------------- Initialize Firebase SDK ---------------- */
  async function init(forceConfig = null) {
    if (typeof firebase === 'undefined') {
      console.warn('[FirebaseAuth] Firebase SDK scripts not loaded on page.');
      return false;
    }

    try {
      const firebaseConfig = forceConfig || await resolveConfig();
      currentConfig = firebaseConfig;

      // Check if already initialized with the same API key
      if (firebase.apps.length > 0) {
        // If reconfiguring with a new valid API key, delete existing app
        if (forceConfig && firebase.app().options.apiKey !== forceConfig.apiKey) {
          await firebase.app().delete();
          firebase.initializeApp(firebaseConfig);
        }
      } else {
        firebase.initializeApp(firebaseConfig);
      }

      // Create Firebase Auth instance & GoogleAuthProvider
      authInstance = firebase.auth();
      googleProvider = new firebase.auth.GoogleAuthProvider();
      googleProvider.addScope('email');
      googleProvider.addScope('profile');

      // Set prompt: 'select_account' to show the Google account chooser
      googleProvider.setCustomParameters({
        prompt: 'select_account'
      });

      isInitialized = true;
      console.log('[FirebaseAuth] Standard Firebase GoogleAuthProvider initialized with prompt: select_account');
      return true;
    } catch (err) {
      console.warn('[FirebaseAuth] Init warning:', err.message);
      return false;
    }
  }

  /* ---------------- Interactive Firebase Config Modal ---------------- */
  function promptFirebaseConfig(reason = '') {
    return new Promise((resolve, reject) => {
      // Check if modal already exists
      let modal = document.getElementById('firebaseSetupModal');
      if (modal) modal.remove();

      modal = document.createElement('div');
      modal.id = 'firebaseSetupModal';
      modal.className = 'fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-charcoal/60 backdrop-blur-sm animate-fadeIn';
      modal.innerHTML = `
        <div class="bg-white rounded-2xl p-6 sm:p-7 max-w-md w-full shadow-2xl border border-charcoal/10 relative">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 rounded-xl bg-moss/10 flex items-center justify-center text-moss font-bold text-lg">
              🔥
            </div>
            <div>
              <h3 class="font-display font-bold text-lg text-charcoal">Firebase API Key Setup</h3>
              <p class="text-xs text-charcoal/60">Connect your Firebase project to enable Google Login</p>
            </div>
          </div>

          ${reason ? `<div class="mb-4 p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs leading-relaxed">${reason}</div>` : ''}

          <div class="space-y-3.5 mb-5 text-left">
            <div>
              <label class="block text-xs font-semibold text-charcoal/80 mb-1">Firebase Web API Key <span class="text-red-500">*</span></label>
              <input type="text" id="fbModalApiKey" placeholder="AIzaSy..." class="w-full px-3.5 py-2.5 rounded-xl border border-charcoal/20 text-sm focus:border-moss focus:ring-2 focus:ring-moss/20 outline-none font-mono" />
              <p class="text-[11px] text-charcoal/50 mt-1">Found in Firebase Console > Project Settings > General > Web API Key</p>
            </div>

            <div>
              <label class="block text-xs font-semibold text-charcoal/80 mb-1">Firebase Project ID (Optional)</label>
              <input type="text" id="fbModalProjectId" placeholder="e.g. gogreen-2026" class="w-full px-3.5 py-2.5 rounded-xl border border-charcoal/20 text-sm focus:border-moss focus:ring-2 focus:ring-moss/20 outline-none font-mono" />
            </div>
          </div>

          <div class="flex gap-2 justify-end">
            <button type="button" id="fbModalCancel" class="px-4 py-2.5 rounded-xl border border-charcoal/15 text-charcoal/70 text-xs font-semibold hover:bg-paperdim transition">
              Cancel
            </button>
            <button type="button" id="fbModalSave" class="px-5 py-2.5 rounded-xl bg-moss hover:bg-mossdeep text-white text-xs font-bold transition shadow-sm">
              Save & Sign In
            </button>
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      const apiKeyInput = modal.querySelector('#fbModalApiKey');
      const projIdInput = modal.querySelector('#fbModalProjectId');
      const saveBtn = modal.querySelector('#fbModalSave');
      const cancelBtn = modal.querySelector('#fbModalCancel');

      // Pre-fill existing key if any
      if (currentConfig && currentConfig.apiKey && !currentConfig.apiKey.includes('GoGreen-Auth-Key')) {
        apiKeyInput.value = currentConfig.apiKey;
      }
      if (currentConfig && currentConfig.projectId) {
        projIdInput.value = currentConfig.projectId;
      }

      apiKeyInput.focus();

      cancelBtn.addEventListener('click', () => {
        modal.remove();
        reject(new Error('Firebase setup cancelled by user.'));
      });

      saveBtn.addEventListener('click', async () => {
        const apiKey = apiKeyInput.value.trim();
        const projectId = projIdInput.value.trim() || 'gogreen-smart-waste';

        if (!apiKey) {
          apiKeyInput.classList.add('border-red-500');
          return;
        }

        const newConfig = {
          apiKey: apiKey,
          authDomain: `${projectId}.firebaseapp.com`,
          projectId: projectId,
          storageBucket: `${projectId}.firebasestorage.app`,
          messagingSenderId: '852086315506',
          appId: '1:852086315506:web:09e321eb5041cfbb70b36b',
        };

        try {
          localStorage.setItem('gogreen_firebase_config', JSON.stringify(newConfig));
          localStorage.setItem('gogreen_firebase_api_key', apiKey);
        } catch (e) { }

        modal.remove();
        await init(newConfig);
        resolve(newConfig);
      });
    });
  }

  /* ---------------- Standard Firebase Google Sign-In Function ---------------- */
  async function signInWithGoogle(options = {}) {
    const mode = (typeof options === 'object' && options && options.mode) ? options.mode : 'login';
    console.log(`[FirebaseAuth] Triggering Firebase signInWithPopup(googleProvider) with mode: ${mode}...`);

    if (!authInstance || !googleProvider) {
      await init();
    }

    if (!currentConfig || !currentConfig.apiKey || currentConfig.apiKey.includes('GoGreen-Auth-Key')) {
      // Prompt user to enter their Firebase Web API Key
      await promptFirebaseConfig('To authenticate with your real Google account via Firebase, please enter your Firebase Web API Key from the Firebase Console.');
    }

    // Ensure prompt: 'select_account' is set
    googleProvider.setCustomParameters({
      prompt: 'select_account'
    });

    try {
      // Step 1: Firebase Google Popup (opens Google Account Chooser)
      const result = await authInstance.signInWithPopup(googleProvider);

      // Step 2: Get Firebase user
      const fbUser = result.user;

      // Step 3: Get Firebase ID token
      const idToken = await fbUser.getIdToken();

      console.log('[FirebaseAuth] Google account selected via Firebase:', fbUser.email);

      // Step 4: Synchronize with Flask backend (/api/auth/google)
      const res = await Session.apiFetch('/api/auth/google', {
        method: 'POST',
        body: JSON.stringify({
          email: fbUser.email,
          name: fbUser.displayName || fbUser.email.split('@')[0],
          picture: fbUser.photoURL || '',
          googleId: fbUser.uid,
          credential: idToken,
          mode: mode,
        }),
      });

      // Step 5: Save JWT session
      Session.setAuth(res.token, res.user);

      if (typeof showToast === 'function') {
        showToast(`✅ Welcome, ${res.user.name}! Redirecting to dashboard...`);
      }

      // Step 6: Redirect to dashboard
      const urlParams = new URLSearchParams(window.location.search);
      const redirectParam = urlParams.get('redirect');
      const targetUrl = redirectParam
        ? (redirectParam.endsWith('.html') ? redirectParam : `dashboard.html?tab=${redirectParam}`)
        : 'dashboard.html';

      setTimeout(() => {
        window.location.replace(targetUrl);
      }, 500);

      return {
        success: true,
        user: res.user,
        isNew: res.isNew,
      };
    } catch (fbErr) {
      console.warn('[FirebaseAuth] Firebase popup / auth error:', fbErr);

      // Re-throw API conflicts (like already registered) directly to caller
      if (fbErr.status === 409 || (fbErr.data && fbErr.data.alreadyRegistered)) {
        throw fbErr;
      }

      if (fbErr.code === 'auth/api-key-not-valid' || (fbErr.message && fbErr.message.includes('api-key-not-valid'))) {
        // Interactive prompt to fix the invalid API key and retry
        await promptFirebaseConfig('⚠️ The Firebase Web API Key was not recognized. Please verify and enter your valid Web API Key from Firebase Console > Project Settings.');
        return await signInWithGoogle();
      }

      if (fbErr.code === 'auth/popup-closed-by-user') {
        throw new Error('Google Sign-In window was closed before completing login.');
      }

      if (fbErr.code === 'auth/cancelled-popup-request') {
        throw new Error('Another Google Sign-In popup is already open.');
      }

      if (fbErr.code === 'auth/unauthorized-domain') {
        throw new Error(
          `Domain "${window.location.hostname}" is not authorized in Firebase Console > Authentication > Settings > Authorized domains.`
        );
      }

      throw fbErr;
    }
  }

  async function signOut() {
    if (authInstance) {
      try {
        await authInstance.signOut();
      } catch (e) { }
    }
    if (typeof Session !== 'undefined') {
      Session.clear();
    }
  }

  // Auto-initialize on load
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => init());
    } else {
      init();
    }
  }

  return {
    init,
    signInWithGoogle,
    signOut,
    promptFirebaseConfig,
    isInitialized: () => isInitialized,
  };
})();

