(function () {
  'use strict';
  const CFG = window.WEDDING_CONFIG || {};
  const isLocal = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
  // 在自己電腦上預覽時一律用模擬後端，才不會把測試資料寫進正式的試算表
  const API = isLocal ? '/api' : (CFG.API_URL || '');
  const STORE_KEY = 'wedding-rsvp-draft';

  // ---------- 封面信封與開場動畫 ----------
  const root = document.documentElement;
  const cover = document.getElementById('cover');
  const clips = Array.from(document.querySelectorAll('video.clip'));
  // 喜帖的動畫是重點，不跟隨系統的「減少動態效果」設定（否則關閉 Windows 動畫的電腦會完全看不到）
  const calm = false;

  // 標題拆成一個個字，進場時逐字出現
  const title = document.querySelector('.hero-title');
  title.setAttribute('aria-label', title.textContent);
  title.innerHTML = Array.from(title.textContent).map((ch, i) =>
    '<span aria-hidden="true" style="--i:' + i + '">' + ch + '</span>').join('');

  // 花瓣碎片：點開信封時，信封碎成花瓣往四周散開，接著再飄落一陣
  function petals() {
    const env = document.getElementById('open-btn').getBoundingClientRect();
    const cv = document.createElement('canvas');
    cv.className = 'confetti';
    document.body.appendChild(cv);
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const W = cv.width = innerWidth * dpr, H = cv.height = innerHeight * dpr;
    const ctx = cv.getContext('2d');
    const colors = [['#F7C9C9', '#E58A93'], ['#F3A9A9', '#C9434A'], ['#D9565B', '#A3262A'], ['#FFF4EC', '#F2D4C4'], ['#F6E2B0', '#C9A45C']];
    const ps = [];
    const cx = (env.left + env.width / 2) * dpr, cy = (env.top + env.height / 2) * dpr;
    for (let i = 0; i < 130; i++) {              // 從信封的位置炸開
      const x = (env.left + Math.random() * env.width) * dpr, y = (env.top + Math.random() * env.height) * dpr;
      const a = Math.atan2(y - cy, x - cx) + (Math.random() - 0.5) * 0.9;
      const sp = (220 + Math.random() * 620) * dpr;
      ps.push({ x, y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp - 260 * dpr, t0: Math.random() * 0.12 });
    }
    for (let i = 0; i < 46; i++) {               // 從上方飄落的第二波
      ps.push({ x: Math.random() * W, y: -30 * dpr - Math.random() * H * 0.35, vx: (Math.random() - 0.5) * 60 * dpr, vy: (90 + Math.random() * 140) * dpr, t0: 0.5 + Math.random() * 0.9, soft: true });
    }
    ps.forEach((p, i) => {
      p.r = (7 + Math.random() * 11) * dpr * (i % 9 === 0 ? 0.45 : 1);
      p.rot = Math.random() * 6.28; p.vr = (Math.random() - 0.5) * 7;
      p.flip = Math.random() * 6.28; p.vf = 2.5 + Math.random() * 4;
      p.sway = Math.random() * 6.28; p.c = colors[i % colors.length];
    });
    const LIFE = 4.6;
    let last = performance.now(); const start = last;
    (function frame(now) {
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      const t = (now - start) / 1000;
      ctx.clearRect(0, 0, W, H);
      ps.forEach(p => {
        if (t < p.t0) return;
        const drag = Math.pow(p.soft ? 0.6 : 0.12, dt);          // 一開始衝得快，很快慢下來變成飄
        p.vx *= drag; p.vy = p.vy * drag + 420 * dpr * dt * (p.soft ? 0.25 : 0.55);
        p.x += (p.vx + Math.sin(t * 2.2 + p.sway) * 46 * dpr) * dt; p.y += p.vy * dt;
        p.rot += p.vr * dt; p.flip += p.vf * dt;
        const alpha = Math.max(0, Math.min(1, (t - p.t0) * 6, (LIFE - t) / 1.1));
        if (alpha <= 0 || p.y > H + 40 * dpr) return;
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.translate(p.x, p.y); ctx.rotate(p.rot); ctx.scale(1, 0.35 + 0.65 * Math.abs(Math.cos(p.flip)));
        const g = ctx.createLinearGradient(0, -p.r, 0, p.r);
        g.addColorStop(0, p.c[0]); g.addColorStop(1, p.c[1]);
        ctx.fillStyle = g;
        ctx.beginPath();                          // 花瓣形：上尖下圓，頂端有一個小缺口
        ctx.moveTo(0, p.r);
        ctx.bezierCurveTo(p.r * 0.95, p.r * 0.55, p.r * 0.85, -p.r * 0.75, p.r * 0.18, -p.r);
        ctx.quadraticCurveTo(0, -p.r * 0.72, -p.r * 0.18, -p.r);
        ctx.bezierCurveTo(-p.r * 0.85, -p.r * 0.75, -p.r * 0.95, p.r * 0.55, 0, p.r);
        ctx.fill();
        ctx.restore();
      });
      if (t < LIFE) requestAnimationFrame(frame); else cv.remove();
    })(last);
  }

  // ---------- 背景音樂 ----------
  const bgm = document.getElementById('bgm');
  const bgmBtn = document.getElementById('bgm-btn');
  bgm.volume = 0.45;
  let bgmWanted = false;                       // 使用者想不想聽（切到別的分頁會暫停，回來時依這個決定要不要繼續）
  function setBgm(on) {
    bgmWanted = on;
    if (on) bgm.play().catch(() => { bgmWanted = false; syncBgm(); }); else bgm.pause();
    syncBgm();
  }
  function syncBgm() {
    bgmBtn.classList.toggle('playing', bgmWanted);
    bgmBtn.setAttribute('aria-pressed', String(bgmWanted));
    bgmBtn.setAttribute('aria-label', bgmWanted ? '關閉背景音樂' : '播放背景音樂');
  }
  bgmBtn.addEventListener('click', () => setBgm(!bgmWanted));
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) bgm.pause(); else if (bgmWanted) bgm.play().catch(() => {});
  });

  function enter(delay) {
    setTimeout(() => root.classList.add('entered'), delay);
  }
  function openCover() {
    if (cover.classList.contains('open')) return;
    cover.classList.add('open');
    // 趁著這次點擊啟動主視覺影片（部分手機要有點擊才肯自動播放）
    if (clips[0]) clips[0].play().catch(() => {});
    bgmBtn.hidden = false;
    setBgm(true);                               // 點信封這一下同時啟動音樂（瀏覽器規定要有點擊才能出聲）
    // 封蠟彈開 → 信封碎成花瓣散開 → 主視覺逐一進場
    setTimeout(petals, 160);
    enter(750);
    setTimeout(() => root.classList.remove('locked'), 1000);
  }
  // 網址加上 ?nocover 可跳過信封（預覽、檢查版面用）
  if (location.search.indexOf('nocover') >= 0) {
    cover.classList.add('open', 'skip');
    bgmBtn.hidden = false;
    enter(0);
  } else {
    root.classList.add('locked');
    window.scrollTo(0, 0);
  }
  document.getElementById('open-btn').addEventListener('click', openCover);

  // ---------- 影片：進入畫面才播放，離開就暫停 ----------
  const vio = 'IntersectionObserver' in window && new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting && cover.classList.contains('open')) e.target.play().catch(() => {});
      else e.target.pause();
    });
  }, { threshold: 0.35 });
  clips.forEach(v => {
    if (vio) vio.observe(v);
    // 省電模式下不會自動播放，點一下影片可以手動播放
    v.addEventListener('click', () => { if (v.paused) v.play().catch(() => {}); });
    // 有劇情、頭尾接不起來的影片：播完停一下，淡出後再從頭播
    if (v.hasAttribute('data-fade')) {
      v.addEventListener('ended', () => {
        setTimeout(() => {
          v.classList.add('fading');
          setTimeout(() => { v.currentTime = 0; v.classList.remove('fading'); v.play().catch(() => {}); }, 500);
        }, 1200);
      });
    }
  });

  // ---------- 捲動進場：區塊內的元素依序浮現，詩句一行一行出現 ----------
  document.querySelectorAll('.poem').forEach(p => {
    p.innerHTML = p.innerHTML.split(/<br\s*\/?>/i).map((line, l) =>
      '<span class="line" style="--l:' + l + '">' + line.trim() + '</span>').join('');
  });
  document.querySelectorAll('.reveal').forEach(sec => {
    Array.from(sec.children).forEach((c, i) => c.style.setProperty('--i', i));
  });
  const io = 'IntersectionObserver' in window && new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('shown'); io.unobserve(e.target); } });
  }, { threshold: 0.15 });
  document.querySelectorAll('.reveal').forEach(el => io ? io.observe(el) : el.classList.add('shown'));

  // ---------- 交通分頁 ----------
  const wayTabs = Array.from(document.querySelectorAll('.way-tabs button'));
  wayTabs.forEach(tab => tab.addEventListener('click', () => {
    wayTabs.forEach(t => t.setAttribute('aria-selected', String(t === tab)));
    document.querySelectorAll('.way-panel').forEach(p => { p.hidden = p.dataset.panel !== tab.dataset.way; });
  }));

  // ---------- Google 日曆連結 ----------
  const gcal = new URL('https://calendar.google.com/calendar/render');
  gcal.searchParams.set('action', 'TEMPLATE');
  gcal.searchParams.set('text', '蕭苰栯 ♥ 洪韻雯 婚宴');
  gcal.searchParams.set('dates', '20261106T030000Z/20261106T060000Z');
  gcal.searchParams.set('location', '高雄日航酒店 三樓宴會廳，高雄市前鎮區林森四路268號');
  gcal.searchParams.set('details', '午宴 11:00 開始，三樓宴會廳。捷運三多商圈站（R8）2 號出口步行約 6 分鐘；婚宴賓客享 4 小時免費停車。');
  document.getElementById('gcal').href = gcal.toString();

  // ---------- 倒數計時 ----------
  const start = new Date(CFG.START || '2026-11-06T11:00:00+08:00').getTime();
  const cd = document.getElementById('countdown');
  const cells = {};
  cd.querySelectorAll('[data-k]').forEach(b => { cells[b.dataset.k] = b; });
  function tick() {
    let s = Math.max(0, Math.floor((start - Date.now()) / 1000));
    const d = Math.floor(s / 86400); s -= d * 86400;
    const h = Math.floor(s / 3600); s -= h * 3600;
    const m = Math.floor(s / 60); s -= m * 60;
    const vals = { d: String(d), h: String(h).padStart(2, '0'), m: String(m).padStart(2, '0'), s: String(s).padStart(2, '0') };
    Object.keys(vals).forEach(k => {
      if (cells[k].textContent === vals[k]) return;
      cells[k].textContent = vals[k];
      // 數字變動時跳一下
      cells[k].classList.remove('tick'); void cells[k].offsetWidth; cells[k].classList.add('tick');
    });
  }
  tick();
  setInterval(tick, 1000);

  // ---------- 出席表單 ----------
  const form = document.getElementById('rsvp-form');
  const f = form.elements;
  const attendBox = document.getElementById('attend-fields');
  const addrField = document.getElementById('address-field');
  const errBox = document.getElementById('form-error');
  const btn = document.getElementById('submit-btn');
  const thanks = document.getElementById('thanks');

  function fillSelect(sel, from, to, keep) {
    const prev = keep !== undefined ? keep : sel.value;
    sel.innerHTML = '';
    for (let i = from; i <= to; i++) {
      const o = document.createElement('option');
      o.value = i; o.textContent = i + ' 位';
      sel.appendChild(o);
    }
    sel.value = Math.min(Math.max(parseInt(prev, 10) || from, from), to);
  }
  // ---------- 同行親友：按「新增」就多一列，每列填姓名、電話、是否吃素 ----------
  const compList = document.getElementById('comp-list');
  const compAdd = document.getElementById('comp-add');
  const MAX_COMP = 9;
  let compSeq = 0;
  function addCompanion(data) {
    if (compList.children.length >= MAX_COMP) return null;
    const n = ++compSeq;
    const row = document.createElement('div');
    row.className = 'comp';
    row.innerHTML =
      '<input class="comp-name" id="comp-name-' + n + '" maxlength="30" placeholder="姓名" aria-label="同行親友姓名" autocomplete="off">' +
      '<input class="comp-phone" id="comp-phone-' + n + '" type="tel" inputmode="tel" maxlength="15" placeholder="連絡電話（選填）" aria-label="同行親友連絡電話" autocomplete="off">' +
      '<label class="check comp-veg"><input type="checkbox" id="comp-veg-' + n + '"><span>吃素</span></label>' +
      '<button type="button" class="comp-del" aria-label="移除這位同行親友">✕</button>';
    if (data) {
      row.querySelector('.comp-name').value = data.name || '';
      row.querySelector('.comp-phone').value = data.phone || '';
      row.querySelector('.comp-veg input').checked = !!data.veg;
    }
    compList.appendChild(row);
    return row;
  }
  const companions = () => Array.from(compList.children).map(r => ({
    name: r.querySelector('.comp-name').value.trim(),
    phone: r.querySelector('.comp-phone').value.trim(),
    veg: r.querySelector('.comp-veg input').checked,
    row: r,
  }));
  compAdd.addEventListener('click', () => {
    const row = addCompanion();
    if (row) row.querySelector('.comp-name').focus();
    syncCounts();
  });
  compList.addEventListener('click', e => {
    if (!e.target.classList.contains('comp-del')) return;
    e.target.closest('.comp').remove();
    syncCounts();
  });

  // 出席總人數 = 自己 + 同行親友；素食人數 = 有勾「吃素」的人數；兒童座椅只有選「需要」才算
  const headCount = () => 1 + compList.children.length;
  const vegCount = () => (f.selfveg.checked ? 1 : 0) + companions().filter(c => c.veg).length;
  const kidSeats = () => f.seat.value === 'yes' ? (parseInt(f.kids.value, 10) || 1) : 0;

  function syncCounts() {
    const n = headCount();
    fillSelect(f.kids, 1, n);
    const veg = vegCount();
    const kids = kidSeats();
    compAdd.hidden = compList.children.length >= MAX_COMP;
    document.getElementById('meal-calc').textContent =
      `共 ${n} 位：葷食 ${n - veg} 位・素食 ${veg} 位` + (kids ? `・嬰兒／兒童座椅 ${kids} 張` : '');
  }
  function syncVisibility() {
    attendBox.hidden = f.attend.value === 'no';      // 預設就顯示，只有選「無法出席」才收起來
    addrField.hidden = !f.paper.checked;
    document.getElementById('kids-field').hidden = f.seat.value !== 'yes';
    gift.hidden = f.attend.value !== 'no';          // 選「無法出席」才出現紅包轉帳區
  }
  form.addEventListener('change', () => { syncVisibility(); syncCounts(); });
  form.addEventListener('input', e => e.target.removeAttribute('aria-invalid'));   // 開始修改就拿掉紅框

  // ---------- 紅包轉帳區 ----------
  const gift = document.getElementById('gift');
  const giftBox = document.getElementById('gift-box');
  const giftToggle = document.getElementById('gift-toggle');
  giftToggle.addEventListener('click', () => {
    giftBox.hidden = !giftBox.hidden;
    giftToggle.setAttribute('aria-expanded', String(!giftBox.hidden));
    giftToggle.textContent = giftBox.hidden ? '顯示轉帳 QR Code' : '收起 QR Code';
  });
  document.getElementById('gift-copy').addEventListener('click', async e => {
    const no = document.getElementById('gift-no');
    try {
      await navigator.clipboard.writeText(no.textContent.trim());
      e.target.textContent = '已複製';
    } catch (err) {                              // 有些瀏覽器不給複製，改成把帳號選起來讓人手動複製
      const r = document.createRange(); r.selectNodeContents(no);
      const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
      e.target.textContent = '已選取帳號，請長按複製';
    }
    setTimeout(() => { e.target.textContent = '複製帳號'; }, 2500);
  });

  const normPhone = p => {
    let d = String(p || '').replace(/\D/g, '');
    if (d.startsWith('886')) d = '0' + d.slice(3);
    return /^0\d{8,9}$/.test(d) ? d : '';
  };

  function collect() {
    const count = headCount();
    const veg = vegCount();
    return {
      action: 'rsvp',
      name: f.name.value.trim(),
      phone: f.phone.value.trim(),
      side: f.side.value,
      attend: f.attend.value,
      count, veg, meat: count - veg,
      kids: kidSeats(),
      selfveg: f.selfveg.checked,
      companions: companions().map(c => ({ name: c.name, phone: c.phone, veg: c.veg })),
      paper: f.paper.checked,
      address: f.address.value.trim(),
      message: f.message.value.trim(),
      website: f.website.value,
    };
  }

  // 記住這台手機填過的內容，方便之後修改
  function saveDraft(d) {
    try { const c = Object.assign({}, d); delete c.website; delete c.action; localStorage.setItem(STORE_KEY, JSON.stringify(c)); } catch (e) {}
  }
  function loadDraft() {
    let d;
    try { d = JSON.parse(localStorage.getItem(STORE_KEY) || 'null'); } catch (e) { d = null; }
    if (!d) return false;
    f.name.value = d.name || '';
    f.phone.value = d.phone || '';
    form.querySelectorAll('input[name="side"]').forEach(r => { r.checked = r.value === d.side; });
    form.querySelectorAll('input[name="attend"]').forEach(r => { r.checked = r.value === d.attend; });
    const k = parseInt(d.kids, 10) || 0;
    form.querySelectorAll('input[name="seat"]').forEach(r => { r.checked = r.value === (k > 0 ? 'yes' : 'no'); });
    f.selfveg.checked = !!d.selfveg;
    compList.innerHTML = '';
    (Array.isArray(d.companions) ? d.companions : []).forEach(c => addCompanion(c));
    syncCounts();
    if (k > 0) f.kids.value = k;
    syncCounts();
    f.paper.checked = !!d.paper;
    f.address.value = d.address || '';
    f.message.value = d.message || '';
    return true;
  }

  function showError(msg, field) {
    errBox.textContent = msg;
    errBox.hidden = false;
    form.querySelectorAll('[aria-invalid]').forEach(el => el.removeAttribute('aria-invalid'));
    if (field) { field.setAttribute('aria-invalid', 'true'); field.focus(); }
  }

  function validate(d) {
    if (!d.name) return showError('請填寫姓名', f.name), false;
    if (!normPhone(d.phone)) return showError('手機號碼格式不正確，請填 09 開頭的號碼', f.phone), false;
    if (!d.attend) return showError('請選擇是否出席'), false;
    if (d.attend === 'yes') {
      for (const c of companions()) {
        if (!c.name) return showError('請填寫同行親友的姓名，或按 ✕ 移除這一列', c.row.querySelector('.comp-name')), false;
        if (c.phone && !normPhone(c.phone)) return showError('同行親友的電話格式不正確（沒有的話可以留空）', c.row.querySelector('.comp-phone')), false;
      }
    }
    if (d.paper && !d.address) return showError('需要紙本喜帖的話，請填寫寄送地址', f.address), false;
    return true;
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();
    errBox.hidden = true;
    const d = collect();
    if (!validate(d)) return;
    if (!API && !CFG.PREVIEW) return showError('表單尚未開放，請稍後再試或直接告訴新人 🙏');

    btn.disabled = true;
    btn.textContent = '送出中…';
    try {
      // 用 text/plain 送出，Apps Script 才不會觸發跨網域預檢
      // 預覽版（給新人自己先看的）不會真的送出資料，只示範送出後的畫面
      const out = CFG.PREVIEW ? { ok: true, updated: false }
        : await (await fetch(API, { method: 'POST', body: JSON.stringify(d) })).json();
      if (!out.ok) throw new Error(out.error || '送出失敗');
      saveDraft(d);
      document.getElementById('thanks-title').textContent =
        d.attend === 'yes' ? `${d.name}，期待與您相見！` : `${d.name}，謝謝您的祝福！`;
      document.getElementById('thanks-body').textContent = (out.updated ? '已更新您先前的回覆。' : '我們收到您的回覆了。') +
        (d.attend === 'yes' ? `共 ${d.count} 位（葷 ${d.meat}・素 ${d.veg}${d.kids ? `・嬰兒／兒童座椅 ${d.kids}` : ''}）。` : '') +
        (CFG.PREVIEW ? '（這是預覽版，資料沒有真的送出）' : '');
      // 無法出席的人送出後，紅包轉帳區移到感謝卡片裡繼續顯示
      if (d.attend === 'no') thanks.insertBefore(gift, document.getElementById('edit-again'));
      form.hidden = true;
      thanks.hidden = false;
      thanks.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } catch (err) {
      showError((err && err.message) || '網路好像不太穩，請再試一次');
    } finally {
      btn.disabled = false;
      btn.textContent = '送出回覆';
    }
  });

  document.getElementById('edit-again').addEventListener('click', () => {
    form.insertBefore(gift, form.querySelector('.check'));     // 紅包轉帳區放回表單原位
    thanks.hidden = true;
    form.hidden = false;
    form.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  syncCounts();
  loadDraft();
  syncVisibility();
})();
