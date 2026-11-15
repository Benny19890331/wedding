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

})();
