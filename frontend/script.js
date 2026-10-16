/* =============================================================
   Go Green — script.js
   Interactive behavior & Backend API Integration for Go Green:
   - Live sensor feed and stats synchronization
   - Real-time waste reporting with photo upload
   - Collection pickup booking with reference tracking
   - Interactive multi-tab dashboard with live user data
   - Dynamic Chart.js activity analytics
   - Gamified rewards & streak progress
============================================================= */

let activityChartInstance = null;

document.addEventListener('DOMContentLoaded', async () => {
  initIcons();
  initNavbar();
  initMobileMenu();
  initScrollReveal();
  initNavAuthState();
  initAuthPortal();
  
  // Connect with live Backend API
  await initCounters();
  await initHeroBins();
  await initRewardProgress();
  initActivityChart();
  initDashboardTabs();
  initReportForm();
  initDropZone();
  initScheduleForm();
  initSegLinks();
});

/* ---------------- Icons ---------------- */
function initIcons() {
  if (window.lucide && typeof lucide.createIcons === 'function') {
    lucide.createIcons();
  }
}

/* ---------------- Navbar Auth State ---------------- */
function initNavAuthState() {
  const user = typeof Session !== 'undefined' ? Session.getUser() : null;
  const desktop = document.getElementById('navAuthArea');
  const mobile = document.getElementById('mobileNavAuthArea');
  const navLinks = document.querySelectorAll('a[href="#dashboard"]');
  const heroCtaBtn = document.querySelector('#home a.btn-primary');

  if (user) {
    const firstName = user.name.split(' ')[0];
    const avatarHtml = user.avatarUrl
      ? `<img src="${user.avatarUrl}" alt="${user.name}" class="w-7 h-7 rounded-full object-cover border border-sprout" />`
      : `<span class="avatar-initials w-7 h-7 text-xs bg-sproutlight text-mossdeep font-bold">${user.initials || firstName[0]}</span>`;

    if (desktop) {
      desktop.innerHTML = `
        <div class="flex items-center gap-2.5">
          <a href="dashboard.html" class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-moss/10 hover:bg-moss/20 border border-moss/20 transition">
            ${avatarHtml}
            <span class="text-xs font-semibold text-mossdeep font-display">${firstName}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded-full bg-mossdeep text-paper font-mono font-bold">${user.ecoPoints || 0} pts</span>
          </a>
          <a href="dashboard.html" class="btn-primary text-xs py-1.5 px-3">
            <i data-lucide="layout-dashboard" class="w-3.5 h-3.5"></i> Dashboard
          </a>
          <button id="logoutBtn" class="btn-ghost text-xs py-1.5 px-2.5 hover:text-red-700" title="Log Out">
            <i data-lucide="log-out" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      `;
    }

    if (mobile) {
      mobile.innerHTML = `
        <div class="w-full space-y-2 p-2 bg-moss/5 rounded-xl border border-moss/10">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              ${avatarHtml}
              <div>
                <p class="text-xs font-bold text-mossdeep font-display">${user.name}</p>
                <p class="text-[10px] text-charcoal/60">${user.ecoPoints || 0} Eco Points · ${user.ward || 'Ward 7'}</p>
              </div>
            </div>
            <button id="logoutBtnMobile" class="text-xs text-red-600 font-semibold px-2 py-1">Log Out</button>
          </div>
          <a href="dashboard.html" class="btn-primary w-full justify-center text-xs py-2">
            <i data-lucide="layout-dashboard" class="w-3.5 h-3.5"></i> Launch Full Dashboard
          </a>
        </div>
      `;
    }

    // Update nav links to go to dashboard.html
    navLinks.forEach(link => {
      link.setAttribute('href', 'dashboard.html');
    });

    if (heroCtaBtn) {
      heroCtaBtn.setAttribute('href', 'dashboard.html');
      heroCtaBtn.innerHTML = '<i data-lucide="layout-dashboard" class="w-4 h-4"></i> Open My Dashboard';
    }
  } else {
    if (desktop) {
      desktop.innerHTML = `
        <a href="login.html" class="btn-ghost">Log In</a>
        <a href="signup.html" class="btn-primary">Sign Up</a>
      `;
    }
    if (mobile) {
      mobile.innerHTML = `
        <a href="login.html" class="btn-ghost flex-1 text-center">Log In</a>
        <a href="signup.html" class="btn-primary flex-1 text-center">Sign Up</a>
      `;
    }

    // Direct guest to login for dashboard
    navLinks.forEach(link => {
      link.setAttribute('href', 'login.html?redirect=dashboard');
    });
  }

  // Personalize overview greeting if present
  if (user) {
    const greetingEl = document.getElementById('dashGreeting');
    const subtitleEl = document.getElementById('dashSubtitle');
    const pointsEl = document.getElementById('dashUserPoints');
    if (greetingEl) {
      greetingEl.textContent = `Good Morning, ${user.name.split(' ')[0]} 👋`;
    }
    if (subtitleEl) {
      subtitleEl.textContent = `Here's what's happening in ${user.ward || 'Ward 7'} today.`;
    }
    if (pointsEl && user.ecoPoints !== undefined) {
      pointsEl.textContent = user.ecoPoints;
    }
  }

  const doLogout = (e) => {
    e.preventDefault();
    if (typeof Session !== 'undefined') {
      Session.clear();
    }
    showToast('You have been logged out.');
    setTimeout(() => {
      window.location.reload();
    }, 400);
  };

  document.getElementById('logoutBtn')?.addEventListener('click', doLogout);
  document.getElementById('logoutBtnMobile')?.addEventListener('click', doLogout);
  if (window.lucide) lucide.createIcons();
}

/* ---------------- Navbar shrink on scroll ---------------- */
function initNavbar() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;

  const applyState = () => {
    if (window.scrollY > 12) {
      navbar.classList.add('is-scrolled');
    } else {
      navbar.classList.remove('is-scrolled');
    }
  };

  applyState();
  window.addEventListener('scroll', applyState, { passive: true });
}

/* ---------------- Mobile menu ---------------- */
function initMobileMenu() {
  const toggle = document.getElementById('menuToggle');
  const menu = document.getElementById('mobileMenu');
  if (!toggle || !menu) return;

  toggle.addEventListener('click', () => {
    menu.classList.toggle('hidden');
    toggle.setAttribute('aria-expanded', String(!menu.classList.contains('hidden')));
  });

  menu.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => menu.classList.add('hidden'));
  });
}

/* ---------------- Scroll reveal ---------------- */
function initScrollReveal() {
  const targets = document.querySelectorAll('.reveal');
  if (!targets.length) return;

  if (!('IntersectionObserver' in window)) {
    targets.forEach((el) => el.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
  );

  targets.forEach((el) => observer.observe(el));
}

/* ---------------- Animated stat counters (Live API) ---------------- */
async function initCounters() {
  let statsData = null;
  try {
    if (typeof Session !== 'undefined') {
      statsData = await Session.apiFetch('/api/dashboard/stats');
    }
  } catch (err) {
    console.log('[Dashboard] Using fallback counter values');
  }

  const counters = document.querySelectorAll('.stat-num[data-count]');
  if (!counters.length) return;

  // Map API fields if available
  if (statsData) {
    const cards = document.querySelectorAll('.stat-card');
    if (cards.length >= 4) {
      cards[0].querySelector('.stat-num')?.setAttribute('data-count', statsData.wasteReports || 25000);
      cards[1].querySelector('.stat-num')?.setAttribute('data-count', statsData.successfulCollections || 18500);
      cards[2].querySelector('.stat-num')?.setAttribute('data-count', statsData.recycledKg || 12000);
      cards[3].querySelector('.stat-num')?.setAttribute('data-count', statsData.greenCitizens || 8000);
    }
  }

  const animate = (el) => {
    const target = parseInt(el.getAttribute('data-count'), 10) || 0;
    const suffix = el.getAttribute('data-suffix') || '';
    const duration = 1400;
    const start = performance.now();

    const step = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = Math.round(target * eased);
      el.textContent = value.toLocaleString() + suffix;
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };

  if (!('IntersectionObserver' in window)) {
    counters.forEach(animate);
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animate(entry.target);
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.3 }
  );
  counters.forEach((el) => observer.observe(el));
}

/* ---------------- Hero Live Bins Feed (Live API) ---------------- */
async function initHeroBins() {
  const container = document.querySelector('.hero-visual-inner .grid');
  if (!container) return;

  try {
    if (typeof Session !== 'undefined') {
      const res = await Session.apiFetch('/api/dashboard/bins');
      if (res.bins && res.bins.length > 0) {
        container.innerHTML = res.bins.slice(0, 6).map(bin => `
          <div class="bin-tile bin-tile--${bin.status}">
            <i data-lucide="trash-2" class="w-4 h-4"></i>
            <span>${bin.ward}</span>
            <b>${bin.fillLevel}%</b>
          </div>
        `).join('');
        initIcons();
      }
    }
  } catch (e) {
    /* default html tiles remain */
  }
}

/* ---------------- Reward progress bar (Live API) ---------------- */
async function initRewardProgress() {
  const bar = document.querySelector('.progress-fill');
  const pointsLabel = document.getElementById('ecoPointsLabel');
  const levelHeading = document.querySelector('.reward-progress .font-display.text-2xl');
  if (!bar) return;

  try {
    if (typeof Session !== 'undefined') {
      const res = await Session.apiFetch('/api/dashboard/rewards');
      if (res) {
        bar.setAttribute('data-target', res.progressToNextLevel || 85);
        if (pointsLabel) {
          pointsLabel.textContent = `${res.ecoPoints} / ${res.ecoPoints + (res.pointsToNext || 150)} Eco Points`;
        }
        if (levelHeading) {
          levelHeading.textContent = res.level || 'Recycling Hero';
        }
      }
    }
  } catch (e) {
    /* fallback defaults */
  }

  const fill = () => {
    const target = bar.getAttribute('data-target') || '0';
    bar.style.width = target + '%';
  };

  if (!('IntersectionObserver' in window)) {
    fill();
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          fill();
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.5 }
  );
  observer.observe(bar);
}

/* ---------------- Activity chart (Chart.js + Live API) ---------------- */
async function initActivityChart() {
  const canvas = document.getElementById('activityChart');
  if (!canvas || typeof Chart === 'undefined') return;

  let labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  let collected = [12, 19, 14, 22, 18, 9, 15];
  let recycled = [8, 13, 10, 17, 14, 6, 11];

  try {
    if (typeof Session !== 'undefined') {
      const act = await Session.apiFetch('/api/dashboard/activity');
      if (act && act.labels) {
        labels = act.labels;
        collected = act.collected || collected;
        recycled = act.recycled || recycled;
      }
    }
  } catch (e) {
    /* use fallback */
  }

  if (activityChartInstance) {
    activityChartInstance.destroy();
  }

  activityChartInstance = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Collected (kg)',
          data: collected,
          borderColor: '#2F5D42',
          backgroundColor: 'rgba(47, 93, 66, 0.12)',
          tension: 0.4,
          fill: true,
          pointRadius: 3,
          pointBackgroundColor: '#2F5D42',
        },
        {
          label: 'Recycled (kg)',
          data: recycled,
          borderColor: '#B8703A',
          backgroundColor: 'rgba(184, 112, 58, 0.1)',
          tension: 0.4,
          fill: true,
          pointRadius: 3,
          pointBackgroundColor: '#B8703A',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { boxWidth: 10, font: { size: 11 }, color: '#1C2620' },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#1C2620', font: { size: 11 } } },
        y: {
          grid: { color: 'rgba(28, 38, 32, 0.08)' },
          ticks: { color: '#1C2620', font: { size: 11 } },
          beginAtZero: true,
        },
      },
    },
  });
}

/* ---------------- Dynamic Dashboard Tabs ---------------- */
function initDashboardTabs() {
  const tabs = document.querySelectorAll('.dash-nav-item[data-tab]');
  const mainContainer = document.querySelector('.dash-shell .p-6');
  if (!tabs.length || !mainContainer) return;

  const originalOverviewHTML = mainContainer.innerHTML;

  tabs.forEach((tab) => {
    tab.addEventListener('click', async () => {
      tabs.forEach((t) => t.classList.remove('is-active'));
      tab.classList.add('is-active');

      const tabName = tab.getAttribute('data-tab');
      await renderDashboardTab(tabName, mainContainer, originalOverviewHTML);
    });
  });
}

async function renderDashboardTab(tabName, container, overviewHTML) {
  const user = typeof Session !== 'undefined' ? Session.getUser() : null;
  const userName = user ? user.name : 'Ananya Sharma';
  const userWard = user ? (user.ward || 'Ward 7') : 'Ward 7';

  if (tabName === 'overview') {
    container.innerHTML = overviewHTML;
    initIcons();
    initActivityChart();
    return;
  }

  if (tabName === 'reports') {
    container.innerHTML = `
      <div class="flex items-center justify-between mb-6">
        <div>
          <h3 class="font-display font-bold text-xl text-mossdeep">My Waste Reports</h3>
          <p class="text-sm text-charcoal/50 mt-1">Track status and updates on issues you've flagged</p>
        </div>
        <a href="#report" class="btn-primary text-xs py-2 px-4"><i data-lucide="plus" class="w-3.5 h-3.5"></i> New Report</a>
      </div>
      <div id="reportsListContainer" class="space-y-3">
        <div class="p-8 text-center text-charcoal/50 text-sm">Loading reports from server...</div>
      </div>
    `;
    initIcons();

    try {
      const res = await Session.apiFetch('/api/reports?mine=true');
      const listEl = document.getElementById('reportsListContainer');
      if (!listEl) return;

      if (!res.reports || res.reports.length === 0) {
        listEl.innerHTML = `
          <div class="p-8 rounded-2xl bg-paperdim text-center">
            <i data-lucide="file-check" class="w-8 h-8 text-moss mx-auto mb-2"></i>
            <p class="font-display font-semibold text-mossdeep">No reports yet</p>
            <p class="text-xs text-charcoal/60 mt-1">Spotted garbage or dumping? Submit a quick report.</p>
          </div>
        `;
      } else {
        listEl.innerHTML = res.reports.map(r => `
          <div class="p-4 rounded-xl bg-white border border-mossdeep/10 shadow-sm flex items-start justify-between gap-4">
            <div class="flex items-start gap-3">
              <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-moss/10 text-moss mt-0.5">
                <i data-lucide="flag" class="w-4 h-4"></i>
              </span>
              <div>
                <p class="font-display font-semibold text-mossdeep text-sm">${r.location}</p>
                <p class="text-xs text-charcoal/60 mt-0.5">${r.wasteType} · ${r.ward} · ${new Date(r.createdAt).toLocaleDateString()}</p>
                <p class="text-xs text-charcoal/80 mt-1.5">${r.description}</p>
              </div>
            </div>
            <span class="tag ${r.status === 'Resolved' ? 'tag--done' : (r.status === 'In Progress' ? 'tag--progress' : 'tag--pending')} shrink-0">
              ${r.status}
            </span>
          </div>
        `).join('');
      }
      initIcons();
    } catch (e) {
      document.getElementById('reportsListContainer').innerHTML = `<p class="text-xs text-red-600">Failed to load reports.</p>`;
    }
  }

  if (tabName === 'collection') {
    container.innerHTML = `
      <div class="flex items-center justify-between mb-6">
        <div>
          <h3 class="font-display font-bold text-xl text-mossdeep">Scheduled Collections</h3>
          <p class="text-sm text-charcoal/50 mt-1">Your upcoming and past waste pickup appointments</p>
        </div>
        <a href="#collection" class="btn-primary text-xs py-2 px-4"><i data-lucide="plus" class="w-3.5 h-3.5"></i> Book Pickup</a>
      </div>
      <div id="scheduleListContainer" class="space-y-3">
        <div class="p-8 text-center text-charcoal/50 text-sm">Loading pickup schedules...</div>
      </div>
    `;
    initIcons();

    try {
      const res = await Session.apiFetch('/api/schedule?mine=true');
      const listEl = document.getElementById('scheduleListContainer');
      if (!listEl) return;

      if (!res.schedules || res.schedules.length === 0) {
        listEl.innerHTML = `
          <div class="p-8 rounded-2xl bg-paperdim text-center">
            <i data-lucide="calendar" class="w-8 h-8 text-moss mx-auto mb-2"></i>
            <p class="font-display font-semibold text-mossdeep">No active collection scheduled</p>
            <p class="text-xs text-charcoal/60 mt-1">Book a convenient date & slot for recyclables or bulk waste.</p>
          </div>
        `;
      } else {
        listEl.innerHTML = res.schedules.map(s => `
          <div class="p-4 rounded-xl bg-white border border-mossdeep/10 shadow-sm flex items-start justify-between gap-4">
            <div class="flex items-start gap-3">
              <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-clay/10 text-clay mt-0.5">
                <i data-lucide="truck" class="w-4 h-4"></i>
              </span>
              <div>
                <div class="flex items-center gap-2">
                  <p class="font-display font-semibold text-mossdeep text-sm">${s.wasteType} Pickup</p>
                  <span class="text-[11px] font-mono text-charcoal/40 font-bold">#${s.reference}</span>
                </div>
                <p class="text-xs text-charcoal/60 mt-0.5">📅 ${s.date} · ⏰ ${s.timeSlot}</p>
                <p class="text-xs text-charcoal/70 mt-1">📍 ${s.address}</p>
                ${s.notes ? `<p class="text-xs text-charcoal/50 italic mt-0.5">Note: ${s.notes}</p>` : ''}
              </div>
            </div>
            <span class="badge-chip badge-chip--moss shrink-0">${s.status}</span>
          </div>
        `).join('');
      }
      initIcons();
    } catch (e) {
      document.getElementById('scheduleListContainer').innerHTML = `<p class="text-xs text-red-600">Failed to load schedule.</p>`;
    }
  }

  if (tabName === 'recycling') {
    container.innerHTML = `
      <div class="mb-6">
        <h3 class="font-display font-bold text-xl text-mossdeep">Recycling Guide & Tips</h3>
        <p class="text-sm text-charcoal/50 mt-1">Reference sheet for sorting materials correctly in ${userWard}</p>
      </div>
      <div class="grid sm:grid-cols-2 gap-4">
        <div class="p-4 rounded-xl bg-moss/5 border border-moss/20">
          <div class="flex items-center gap-2 text-moss font-bold text-sm"><i data-lucide="leaf" class="w-4 h-4"></i> Organic Waste</div>
          <p class="text-xs text-charcoal/70 mt-2">Food leftovers, fruit peels, compostable plant clippings. Keep separate from plastics.</p>
        </div>
        <div class="p-4 rounded-xl bg-clay/5 border border-clay/20">
          <div class="flex items-center gap-2 text-clay font-bold text-sm"><i data-lucide="recycle" class="w-4 h-4"></i> Dry Recyclables</div>
          <p class="text-xs text-charcoal/70 mt-2">Cardboard boxes, PET bottles, aluminium tins, clean glass containers.</p>
        </div>
        <div class="p-4 rounded-xl bg-red-500/5 border border-red-500/20">
          <div class="flex items-center gap-2 text-red-700 font-bold text-sm"><i data-lucide="triangle-alert" class="w-4 h-4"></i> Hazardous Materials</div>
          <p class="text-xs text-charcoal/70 mt-2">Chemicals, battery cells, aerosol cans, expired medicines. Keep in original packaging.</p>
        </div>
        <div class="p-4 rounded-xl bg-blue-500/5 border border-blue-500/20">
          <div class="flex items-center gap-2 text-blue-700 font-bold text-sm"><i data-lucide="cpu" class="w-4 h-4"></i> Electronic Waste</div>
          <p class="text-xs text-charcoal/70 mt-2">Old computers, broken phones, USB cables, adapters, circuit boards.</p>
        </div>
      </div>
    `;
    initIcons();
  }

  if (tabName === 'rewards') {
    let rewardsData = { ecoPoints: 850, level: 'Recycling Hero', streakDays: 14 };
    try {
      rewardsData = await Session.apiFetch('/api/dashboard/rewards');
    } catch (e) {}

    container.innerHTML = `
      <div class="mb-6">
        <h3 class="font-display font-bold text-xl text-mossdeep">Green Rewards & Achievements</h3>
        <p class="text-sm text-charcoal/50 mt-1">Earn eco-points and unlock badges for sustainable actions</p>
      </div>
      <div class="p-5 rounded-2xl bg-mossdeep text-paper mb-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs text-paper/60 uppercase tracking-wide">Current Tier</p>
            <p class="font-display font-extrabold text-2xl text-sprout mt-0.5">${rewardsData.level}</p>
          </div>
          <div class="text-right">
            <p class="text-xs text-paper/60 uppercase tracking-wide">Total Balance</p>
            <p class="font-display font-extrabold text-2xl text-paper mt-0.5">${rewardsData.ecoPoints} <span class="text-xs font-normal text-paper/70">Points</span></p>
          </div>
        </div>
        <div class="progress-track mt-4">
          <div class="progress-fill" style="width: ${rewardsData.progressToNextLevel || 85}%"></div>
        </div>
        <p class="text-xs text-paper/60 mt-2 text-right">${rewardsData.pointsToNext || 150} pts to ${rewardsData.nextLevel || 'Eco Warrior'}</p>
      </div>

      <h4 class="font-display font-bold text-sm text-mossdeep mb-3">Earned Badges</h4>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        ${(rewardsData.badges || [
          { name: 'Green Beginner', icon: '🌱', unlocked: true },
          { name: 'Recycling Hero', icon: '♻️', unlocked: true },
          { name: 'Eco Warrior', icon: '🌍', unlocked: rewardsData.ecoPoints >= 1000 },
          { name: 'Planet Protector', icon: '🏆', unlocked: rewardsData.ecoPoints >= 1500 },
        ]).map(b => `
          <div class="badge-tile ${b.unlocked ? '' : 'badge-tile--locked'}">
            <span class="text-2xl">${b.icon}</span>
            <p class="text-charcoal">${b.name}</p>
            <span class="text-[10px] ${b.unlocked ? 'text-moss font-semibold' : 'text-charcoal/40'}">${b.unlocked ? 'Unlocked' : 'Locked'}</span>
          </div>
        `).join('')}
      </div>
    `;
    initIcons();
  }

  if (tabName === 'settings') {
    container.innerHTML = `
      <div class="mb-6">
        <h3 class="font-display font-bold text-xl text-mossdeep">Account Settings</h3>
        <p class="text-sm text-charcoal/50 mt-1">Manage your profile and notification preferences</p>
      </div>
      <form id="profileSettingsForm" class="space-y-4 max-w-lg">
        <div class="field">
          <label>Full Name</label>
          <input type="text" id="profName" value="${userName}" required />
        </div>
        <div class="field">
          <label>Email Address</label>
          <input type="email" id="profEmail" value="${user ? user.email : 'ananya@example.com'}" disabled class="opacity-60 cursor-not-allowed" />
        </div>
        <div class="field">
          <label>Assigned Ward</label>
          <select id="profWard">
            <option ${userWard === 'Ward 1' ? 'selected' : ''}>Ward 1 (MG Road)</option>
            <option ${userWard === 'Ward 2' ? 'selected' : ''}>Ward 2 (Tech City)</option>
            <option ${userWard === 'Ward 4' ? 'selected' : ''}>Ward 4 (Market Road)</option>
            <option ${userWard === 'Ward 6' ? 'selected' : ''}>Ward 6 (Highland Park)</option>
            <option ${userWard === 'Ward 7' ? 'selected' : ''}>Ward 7 (Lakeview Colony)</option>
            <option ${userWard === 'Ward 9' ? 'selected' : ''}>Ward 9 (Greenfield Ave)</option>
          </select>
        </div>
        <button type="submit" class="btn-primary text-xs py-2.5 px-5">Save Changes</button>
      </form>
    `;

    document.getElementById('profileSettingsForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const newName = document.getElementById('profName').value.trim();
      const newWard = document.getElementById('profWard').value;

      try {
        if (typeof Session !== 'undefined' && Session.isLoggedIn()) {
          const res = await Session.apiFetch('/api/auth/profile', {
            method: 'PUT',
            body: JSON.stringify({ name: newName, ward: newWard }),
          });
          if (res.user) {
            Session.setUser(res.user);
            initNavAuthState();
          }
        }
        showToast('Profile updated successfully!');
      } catch (err) {
        showToast('Settings saved locally.');
      }
    });
  }
}

/* ---------------- Shared form validation helpers ---------------- */
function validateField(field) {
  const input = field.querySelector('input, select, textarea');
  if (!input) return true;

  let valid = input.checkValidity();

  if (field.id === 'slotField') {
    valid = !!field.dataset.selectedSlot;
  }

  field.classList.toggle('is-invalid', !valid);
  return valid;
}

function showToast(message) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('is-visible');
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => toast.classList.remove('is-visible'), 3600);
}

/* ---------------- Report Waste form (Live API Submission) ---------------- */
function initReportForm() {
  const form = document.getElementById('reportForm');
  if (!form) return;

  const fields = form.querySelectorAll('.field');

  // Pre-fill user details if logged in
  if (typeof Session !== 'undefined' && Session.isLoggedIn()) {
    const user = Session.getUser();
    if (user) {
      const nameInp = document.getElementById('repName');
      const emailInp = document.getElementById('repEmail');
      if (nameInp && !nameInp.value) nameInp.value = user.name;
      if (emailInp && !emailInp.value) emailInp.value = user.email;
    }
  }

  fields.forEach((field) => {
    const input = field.querySelector('input, select, textarea');
    if (!input) return;
    input.addEventListener('blur', () => validateField(field));
    input.addEventListener('input', () => {
      if (field.classList.contains('is-invalid')) validateField(field);
    });
  });

  const pinBtn = document.getElementById('pinBtn');
  if (pinBtn) {
    pinBtn.addEventListener('click', () => {
      const locationInput = document.getElementById('repLocation');
      if (!navigator.geolocation) {
        showToast('Location services are not available on this device.');
        return;
      }
      pinBtn.disabled = true;
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const { latitude, longitude } = pos.coords;
          if (locationInput) {
            locationInput.value = `Near ${latitude.toFixed(4)}°N, ${longitude.toFixed(4)}°E (Ward 7)`;
          }
          pinBtn.disabled = false;
          showToast('Current GPS coordinates tagged.');
        },
        () => {
          pinBtn.disabled = false;
          showToast("Couldn't access GPS. Please type the location.");
        }
      );
    });
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    let allValid = true;
    fields.forEach((field) => {
      if (!validateField(field)) allValid = false;
    });

    if (!allValid) {
      showToast('Please fill in all required fields.');
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    const origBtnHTML = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="animate-spin inline-block mr-2">◌</span> Submitting...';

    const formData = new FormData(form);

    try {
      const res = await Session.apiFetch('/api/reports', {
        method: 'POST',
        body: formData,
      });

      const ptsNotice = res.pointsEarned ? ` +${res.pointsEarned} Eco Points earned!` : '';
      showToast(res.message || `Report submitted — your ward team has been notified.${ptsNotice}`);
      
      form.reset();
      fields.forEach((field) => field.classList.remove('is-invalid'));
      const fileName = document.getElementById('fileName');
      if (fileName) {
        fileName.textContent = '';
        fileName.classList.add('hidden');
      }

      // Update counters & session user points if present
      if (typeof Session !== 'undefined' && res.totalPoints) {
        const u = Session.getUser();
        if (u) {
          u.ecoPoints = res.totalPoints;
          Session.setUser(u);
          initNavAuthState();
        }
      }
      initCounters();
      initRewardProgress();
    } catch (err) {
      showToast(err.message || 'Failed to submit report. Please try again.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = origBtnHTML;
      if (window.lucide) lucide.createIcons();
    }
  });
}

/* ---------------- Drag & drop image upload ---------------- */
function initDropZone() {
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const fileName = document.getElementById('fileName');
  if (!dropZone || !fileInput) return;

  const showFile = (file) => {
    if (!file) return;
    if (fileName) {
      fileName.textContent = `Selected: ${file.name} (${Math.round(file.size / 1024)} KB)`;
      fileName.classList.remove('hidden');
    }
  };

  dropZone.addEventListener('click', () => fileInput.click());
  dropZone.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener('change', () => {
    showFile(fileInput.files && fileInput.files[0]);
  });

  ['dragenter', 'dragover'].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add('is-dragover');
    });
  });

  ['dragleave', 'drop'].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove('is-dragover');
    });
  });

  dropZone.addEventListener('drop', (event) => {
    const file = event.dataTransfer && event.dataTransfer.files[0];
    if (file) {
      fileInput.files = event.dataTransfer.files;
      showFile(file);
    }
  });
}

/* ---------------- Collection scheduling form (Live API Submission) ---------------- */
function initScheduleForm() {
  const form = document.getElementById('scheduleForm');
  if (!form) return;

  const slotGrid = document.getElementById('slotGrid');
  const slotError = document.getElementById('slotError');
  const confirmCard = document.getElementById('confirmCard');
  let selectedSlot = null;

  if (slotGrid) {
    slotGrid.querySelectorAll('.slot').forEach((slot) => {
      slot.addEventListener('click', () => {
        slotGrid.querySelectorAll('.slot').forEach((s) => s.classList.remove('is-selected'));
        slot.classList.add('is-selected');
        selectedSlot = slot.textContent.trim();
        if (slotError) slotError.style.display = 'none';
      });
    });
  }

  const requiredFields = form.querySelectorAll('.field');

  requiredFields.forEach((field) => {
    const input = field.querySelector('input, select, textarea');
    if (!input || !input.hasAttribute('required')) return;
    input.addEventListener('blur', () => validateField(field));
    input.addEventListener('input', () => {
      if (field.classList.contains('is-invalid')) validateField(field);
    });
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    let allValid = true;

    requiredFields.forEach((field) => {
      const input = field.querySelector('input, select, textarea');
      if (input && input.hasAttribute('required') && !validateField(field)) {
        allValid = false;
      }
    });

    if (!selectedSlot) {
      if (slotError) slotError.style.display = 'block';
      allValid = false;
    }

    if (!allValid) {
      showToast('Please complete the required fields and choose a time slot.');
      return;
    }

    const type = document.getElementById('schType')?.value || '';
    const date = document.getElementById('schDate')?.value || '';
    const address = document.getElementById('schAddress')?.value || '';
    const notes = document.getElementById('schNotes')?.value || '';

    const submitBtn = form.querySelector('button[type="submit"]');
    const origBtnHTML = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="animate-spin inline-block mr-2">◌</span> Booking...';

    try {
      const res = await Session.apiFetch('/api/schedule', {
        method: 'POST',
        body: JSON.stringify({
          wasteType: type,
          date: date,
          timeSlot: selectedSlot,
          address: address,
          notes: notes,
        }),
      });

      const formattedDate = date
        ? new Date(date + 'T00:00:00').toLocaleDateString(undefined, {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
          })
        : '';

      const reference = res.reference || (res.schedule && res.schedule.reference) || 'GG-8842';

      if (confirmCard) {
        confirmCard.classList.add('has-confirmation');
        confirmCard.innerHTML = `
          <div class="flex items-center justify-between w-full">
            <span class="badge-chip badge-chip--moss">Confirmed</span>
            <span class="text-xs font-mono font-bold text-mossdeep bg-moss/10 px-2.5 py-1 rounded-md">#${reference}</span>
          </div>
          <p class="font-display font-semibold text-mossdeep mt-3">${type} pickup scheduled</p>
          <p class="text-sm text-charcoal/70 mt-1">📅 ${formattedDate} · ⏰ ${selectedSlot}</p>
          <p class="text-sm text-charcoal/70">📍 ${address}</p>
          <p class="text-xs text-moss mt-3 font-semibold">Your pickup team has been assigned.</p>
        `;
      }

      const ptsEarned = res.pointsEarned ? ` +${res.pointsEarned} Eco Points!` : '';
      showToast(`Collection #${reference} scheduled successfully.${ptsEarned}`);

      form.reset();
      requiredFields.forEach((field) => field.classList.remove('is-invalid'));
      if (slotGrid) slotGrid.querySelectorAll('.slot').forEach((s) => s.classList.remove('is-selected'));
      selectedSlot = null;

      if (typeof Session !== 'undefined' && res.totalPoints) {
        const u = Session.getUser();
        if (u) {
          u.ecoPoints = res.totalPoints;
          Session.setUser(u);
          initNavAuthState();
        }
      }
      initCounters();
    } catch (err) {
      showToast(err.message || 'Failed to schedule collection.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = origBtnHTML;
      if (window.lucide) lucide.createIcons();
    }
  });
}

/* ---------------- Recycling guide "Learn more" details ---------------- */
function initSegLinks() {
  document.querySelectorAll('.seg-link').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const card = btn.closest('.seg-card');
      const title = card ? card.querySelector('h3')?.textContent : '';

      let catId = 'organic';
      if (title.toLowerCase().includes('recyclable')) catId = 'recyclable';
      else if (title.toLowerCase().includes('hazardous')) catId = 'hazardous';
      else if (title.toLowerCase().includes('e-waste')) catId = 'ewaste';

      try {
        const res = await Session.apiFetch(`/api/recycling/categories/${catId}`);
        if (res.category) {
          const itemsList = res.category.items.slice(0, 3).join(', ');
          showToast(`💡 ${res.category.name}: Includes ${itemsList}. ${res.category.disposalTips}`);
        } else {
          showToast(`More detail on ${title} is available in your dashboard guide.`);
        }
      } catch (e) {
        showToast(`Tip for ${title}: Sort items clean and dry before disposal.`);
      }
    });
  });
}

/* ---------------- Embedded Auth Portal (Index.html) ---------------- */
function initAuthPortal() {
  const loggedInCard = document.getElementById('portalLoggedInCard');
  const guestCard = document.getElementById('portalGuestCard');
  if (!loggedInCard || !guestCard) return;

  const user = typeof Session !== 'undefined' ? Session.getUser() : null;

  if (user) {
    // Show active user state
    loggedInCard.classList.remove('hidden');
    guestCard.classList.add('hidden');

    const nameEl = document.getElementById('portalUserName');
    const detailsEl = document.getElementById('portalUserDetails');
    const avatarEl = document.getElementById('portalUserAvatar');
    const logoutBtn = document.getElementById('portalLogoutBtn');

    if (nameEl) nameEl.textContent = `Welcome back, ${user.name}!`;
    if (detailsEl) detailsEl.textContent = `Active in ${user.ward || 'Ward 7'} with ${user.ecoPoints || 0} Eco-Points (${user.level || 'Recycling Hero'}).`;
    if (avatarEl) {
      if (user.avatarUrl) {
        avatarEl.innerHTML = `<img src="${user.avatarUrl}" alt="${user.name}" class="w-full h-full object-cover rounded-full" />`;
      } else {
        avatarEl.textContent = user.initials || user.name.charAt(0);
      }
    }

    logoutBtn?.addEventListener('click', () => {
      Session.clear();
      showToast('Logged out successfully.');
      setTimeout(() => window.location.reload(), 400);
    });

  } else {
    // Show guest login / signup forms
    loggedInCard.classList.add('hidden');
    guestCard.classList.remove('hidden');

    const tabLogin = document.getElementById('portalTabLogin');
    const tabSignup = document.getElementById('portalTabSignup');
    const formLogin = document.getElementById('portalLoginForm');
    const formSignup = document.getElementById('portalSignupForm');
    const googleBtn = document.getElementById('portalGoogleBtn');

    // Tab switching
    tabLogin?.addEventListener('click', () => {
      tabLogin.classList.add('bg-white', 'text-mossdeep', 'shadow-xs');
      tabLogin.classList.remove('text-charcoal/60');
      tabSignup.classList.remove('bg-white', 'text-mossdeep', 'shadow-xs');
      tabSignup.classList.add('text-charcoal/60');

      formLogin?.classList.remove('hidden');
      formSignup?.classList.add('hidden');
    });

    tabSignup?.addEventListener('click', () => {
      tabSignup.classList.add('bg-white', 'text-mossdeep', 'shadow-xs');
      tabSignup.classList.remove('text-charcoal/60');
      tabLogin.classList.remove('bg-white', 'text-mossdeep', 'shadow-xs');
      tabLogin.classList.add('text-charcoal/60');

      formSignup?.classList.remove('hidden');
      formLogin?.classList.add('hidden');
    });

    // Demo user autofill
    document.querySelectorAll('.portal-demo-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const email = btn.getAttribute('data-email');
        const pass = btn.getAttribute('data-pass');
        const emailInp = document.getElementById('portalLoginEmail');
        const passInp = document.getElementById('portalLoginPassword');
        if (emailInp) emailInp.value = email;
        if (passInp) passInp.value = pass;
      });
    });

    // Login Form Submission
    formLogin?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = document.getElementById('portalLoginSubmitBtn');
      const email = document.getElementById('portalLoginEmail').value.trim();
      const password = document.getElementById('portalLoginPassword').value;

      btn.disabled = true;
      btn.innerHTML = '<span class="animate-spin mr-2">◌</span> Authenticating...';

      try {
        await Session.login(email, password);
        showToast('🎉 Login successful! Opening your Citizen Dashboard...');
        setTimeout(() => {
          window.location.replace('dashboard.html');
        }, 600);
      } catch (err) {
        showToast(`Sign in error: ${err.message}`);
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="log-in" class="w-4 h-4"></i> Sign In & Launch Dashboard →';
        if (window.lucide) lucide.createIcons();
      }
    });

    // Signup Form Submission
    formSignup?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = document.getElementById('portalSignupSubmitBtn');
      const name = document.getElementById('portalSignupName').value.trim();
      const email = document.getElementById('portalSignupEmail').value.trim().toLowerCase();
      const password = document.getElementById('portalSignupPassword').value;
      const ward = document.getElementById('portalSignupWard').value;

      btn.disabled = true;
      btn.innerHTML = '<span class="animate-spin mr-2">◌</span> Creating Account...';

      try {
        await Session.signup(name, email, password, ward);
        showToast('🎉 Account created! +100 Welcome Points awarded. Redirecting...');
        setTimeout(() => {
          window.location.replace('dashboard.html');
        }, 700);
      } catch (err) {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="user-plus" class="w-4 h-4"></i> Create Account & Claim +100 Points →';
        if (window.lucide) lucide.createIcons();

        const isAlreadyReg = err.status === 409 || 
                             (err.message && err.message.toLowerCase().includes('already registered')) || 
                             (err.data && err.data.alreadyRegistered);

        if (isAlreadyReg) {
          showToast('⚠️ You have already registered. Please log in.');
          // Switch to sign in tab and prefill email
          tabLogin?.click();
          const loginEmail = document.getElementById('portalLoginEmail');
          if (loginEmail) {
            loginEmail.value = email;
            document.getElementById('portalLoginPassword')?.focus();
          }
        } else {
          showToast(`Sign up error: ${err.message}`);
        }
      }
    });

    // Google Sign In from Portal
    googleBtn?.addEventListener('click', async () => {
      window.location.href = 'login.html';
    });
  }
}



