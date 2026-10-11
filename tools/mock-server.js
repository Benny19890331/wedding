// 本機測試用：提供靜態檔案 + 模擬 Apps Script API（/api），資料存在 tools/mock-data.json
// 用法：node tools/mock-server.js  →  http://localhost:5173
// 測試用的新郎（擁有者）密碼：test-groom（只在本機有效，正式密碼在 Apps Script 的指令碼屬性 KEY_OWNER）
// 其他人的權限用新郎登入後，在後台「權限管理」分頁發放
// 這裡的邏輯要和 apps-script/Code.gs 保持一致。
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const DATA = path.join(__dirname, 'mock-data.json');
const PORT = 5173;
const OWNER_KEY = 'test-groom';
const OWNER = { name: '蕭苰栯', role: '新郎' };
const LEVELS = ['edit', 'view'];
const SIDES = ['男方親友', '女方親友', '共同朋友'];

const DEFAULT_TABLES = [{ no: '主桌', cap: 12, note: '' }]
  .concat(Array.from({ length: 10 }, (_, i) => ({ no: String(i + 1), cap: 10, note: '' })))
  .concat([{ no: '素食桌', cap: 10, note: '全素' }]);

function load() {
  try { const d = JSON.parse(fs.readFileSync(DATA, 'utf8')); d.users = d.users || []; return d; } catch { return { guests: [], tables: DEFAULT_TABLES, users: [] }; }
}
function save(db) { fs.writeFileSync(DATA, JSON.stringify(db, null, 2)); }
const int = x => { const n = parseInt(x, 10); return isNaN(n) ? 0 : n; };
const clean = (s, m) => String(s ?? '').replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, m);
function normPhone(p) {
  let d = String(p || '').replace(/\D/g, '');
  if (d.startsWith('886')) d = '0' + d.slice(3);
  return /^0\d{8,9}$/.test(d) ? d : '';
}
const now = () => new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false }).slice(0, -3);
const randKey = () => require('crypto').randomBytes(8).toString('hex').slice(0, 10);
const newId = () => 'G' + Date.now().toString(36).toUpperCase() + Math.floor(Math.random() * 36).toString(36).toUpperCase();

function normInput(b, admin) {
  const name = clean(b.name, 30);
  if (!name) throw new Error('請填寫姓名');
  const rawPhone = String(b.phone || '').trim();
  const phone = normPhone(rawPhone);
  if (!phone && (rawPhone || !admin)) throw new Error('手機號碼格式不正確');
  const attend = b.attend === 'yes' || b.attend === true;
  const companions = !attend ? [] : (Array.isArray(b.companions) ? b.companions : []).slice(0, 9).map(c => {
    const n = clean(c && c.name, 30);
    if (!n) throw new Error('請填寫同行親友的姓名');
    const ph = c.phone ? normPhone(c.phone) : '';
    if (c.phone && !ph) throw new Error('同行親友的電話格式不正確');
    return { name: n, phone: ph, veg: !!c.veg };
  });
  const kids = attend ? int(b.kids) : 0;
  if (kids < 0 || kids > 1 + companions.length) throw new Error('兒童座椅數量不可多於出席人數');
  const paper = b.paper === true || b.paper === 'yes';
  const address = paper ? clean(b.address, 120) : '';
  if (paper && !address) throw new Error('需要紙本喜帖請填寫地址');
  return {
    name, phone, side: SIDES.includes(b.side) ? b.side : '',
    attend, selfveg: attend && !!b.selfveg, companions, kids, paper, address, message: clean(b.message, 300),
  };
}

function fitSeats(old, g) {
  if (!g.attend) return [];
  const seats = Array(1 + g.companions.length).fill('');
  if (old && old.attend) {
    seats[0] = old.seats[0] || '';
    g.companions.forEach((c, i) => {
      const oc = old.companions[i];
      if (oc && oc.name === c.name) seats[i + 1] = old.seats[i + 1] || '';
    });
  }
  return seats;
}

function handle(b) {
  const db = load();
  if (b.action === 'rsvp') {
    if (b.website) return { ok: true, updated: false };
    const inp = normInput(b, false);
    const found = db.guests.find(g => g.phone && g.phone === inp.phone);
    if (found) {
      const seats = fitSeats(found, inp);
      Object.assign(found, inp, { side: found.side || inp.side, seats, updatedAt: now(), edits: found.edits + 1 });
      save(db); return { ok: true, updated: true, name: inp.name };
    }
    db.guests.push({ id: newId(), createdAt: now(), updatedAt: now(), relation: '', edits: 0, editedBy: '', ...inp, seats: fitSeats(null, inp) });
    save(db); return { ok: true, updated: false, name: inp.name };
  }
  let me = null;
  if (b.key && b.key === OWNER_KEY) me = { name: OWNER.name, role: OWNER.role, level: 'owner' };
  else if (b.key) { const u = db.users.find(x => x.key === b.key); if (u) me = { name: u.name, role: u.role, level: u.level }; }
  if (!me) throw new Error('密碼錯誤，或權限已被收回');
  const stamp = me.name + '（' + me.role + '） ' + now();
  const edit = () => { if (me.level === 'view') throw new Error('你的權限是「只能看」，不能修改'); };
  const owner = () => { if (me.level !== 'owner') throw new Error('只有新郎可以管理權限'); };
  if (['admin_save', 'admin_assign', 'admin_delete', 'admin_tables'].includes(b.action)) edit();
  if (['admin_users', 'admin_user_save', 'admin_user_delete'].includes(b.action)) owner();
  switch (b.action) {
    case 'admin_list': return { ok: true, me, guests: db.guests, tables: db.tables };
    case 'admin_users': return { ok: true, users: db.users };
    case 'admin_user_save': {
      const u = b.user || {};
      const name = clean(u.name, 20), role = clean(u.role, 20);
      if (!name) throw new Error('請填寫稱呼');
      if (!role) throw new Error('請填寫身分');
      const level = LEVELS.includes(u.level) ? u.level : 'view';
      if (u.uid) {
        const x = db.users.find(v => v.uid === u.uid); if (!x) throw new Error('找不到這份權限');
        Object.assign(x, { name, role, level }); if (u.regen) x.key = randKey();
      } else {
        if (db.users.length >= 20) throw new Error('最多發放 20 份權限');
        db.users.push({ uid: 'U' + Date.now().toString(36).toUpperCase(), name, role, level, key: randKey(), createdAt: now() });
      }
      save(db); return { ok: true, users: db.users };
    }
    case 'admin_user_delete': {
      db.users = db.users.filter(v => v.uid !== b.uid);
      save(db); return { ok: true, users: db.users };
    }
    case 'admin_save': {
      const inp = normInput(b.guest || {}, true);
      inp.relation = clean((b.guest || {}).relation, 20);
      if (inp.phone && db.guests.some(g => g.phone === inp.phone && g.id !== b.id)) throw new Error('這支手機號碼已經有另一筆回覆了');
      if (b.id) {
        const g = db.guests.find(x => x.id === b.id); if (!g) throw new Error('找不到這位賓客');
        const seats = fitSeats(g, inp);
        Object.assign(g, inp, { seats, updatedAt: now(), editedBy: stamp });
        save(db); return { ok: true, id: g.id };
      }
      const g = { id: newId(), createdAt: now(), updatedAt: now(), edits: 0, editedBy: stamp, ...inp, seats: fitSeats(null, inp) };
      db.guests.push(g); save(db); return { ok: true, id: g.id };
    }
    case 'admin_assign': {
      const g = db.guests.find(x => x.id === b.id); if (!g) throw new Error('找不到這位賓客');
      if (!g.attend) throw new Error('這位賓客沒有要出席');
      const t = clean(b.table, 20), n = 1 + g.companions.length;
      while (g.seats.length < n) g.seats.push('');
      g.seats.length = n;
      if (b.idx === 'all') g.seats.fill(t);
      else { const i = int(b.idx); if (i < 0 || i >= n) throw new Error('找不到這個座位'); g.seats[i] = t; }
      g.editedBy = stamp;
      save(db); return { ok: true };
    }
    case 'admin_delete': {
      const i = db.guests.findIndex(x => x.id === b.id); if (i < 0) throw new Error('找不到這位賓客');
      db.guests.splice(i, 1); save(db); return { ok: true };
    }
    case 'admin_tables': {
      db.tables = (b.tables || []).map(t => ({ no: clean(t.no, 20), cap: Math.max(0, Math.min(30, int(t.cap))), note: clean(t.note, 40) })).filter(t => t.no);
      save(db); return { ok: true, tables: db.tables };
    }
    default: throw new Error('未知的動作');
  }
}

const TYPES = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.gif': 'image/gif', '.png': 'image/png', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.ics': 'text/calendar',
  '.mp4': 'video/mp4', '.mp3': 'audio/mpeg', '.woff2': 'font/woff2',
};

http.createServer((req, res) => {
  if (req.url === '/api' && req.method === 'POST') {
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      let out;
      try { out = handle(JSON.parse(body)); } catch (e) { out = { ok: false, error: e.message }; }
      setTimeout(() => { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(out)); }, 300);
    });
    return;
  }
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p.endsWith('/')) p += 'index.html';
  const f = path.join(ROOT, p);
  if (!f.startsWith(ROOT)) { res.writeHead(403); return res.end(); }
  fs.readFile(f, (err, buf) => {
    if (err) { res.writeHead(404); return res.end('not found'); }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    res.end(buf);
  });
}).listen(PORT, () => console.log('http://localhost:5173'));
