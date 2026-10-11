/**
 * 蕭苰栯 ♥ 洪韻雯 婚宴回覆表單後端（Google Apps Script）
 *
 * 部署步驟見 部署說明.md。
 * - 賓客送出回覆：以手機號碼辨識，同一支手機再次送出會「更新」原資料，不會重複新增
 * - 管理後台：新郎是擁有者，登入後可以在「權限管理」發放權限給其他人（新娘、婚禮秘書、媒人婆…），
 *   每個人有自己的密碼，可以設定「可編輯」或「只能看」，也可以隨時收回。每次修改會記錄是誰改的
 * - 排桌以「人」為單位：本人和每位同行親友可以各自排到不同桌（例如吃素的人排到素食桌）
 */

const SHEET_GUESTS = '賓客回覆';
const SHEET_TABLES = '桌次';

const COLS = ['id', 'createdAt', 'updatedAt', 'name', 'phone', 'side', 'relation', 'attend', 'count',
  'meat', 'veg', 'kids', 'selfveg', 'companions', 'paper', 'address', 'message', 'table',
  'edits', 'editedBy', 'data', 'seats'];
const HEADERS = ['編號', '首次填寫', '最後更新', '姓名', '手機', '男方／女方', '關係', '出席', '人數',
  '葷食', '素食', '兒童椅', '本人吃素', '同行親友', '紙本喜帖', '地址', '祝福', '桌號',
  '修改次數', '最後修改者', '同行親友資料（系統用，請勿修改）', '座位資料（系統用，請勿修改）'];

const SIDES = ['男方親友', '女方親友', '共同朋友'];
// 擁有者（新郎）的密碼存在指令碼屬性 KEY_OWNER；他發放出去的權限存在 USERS
const OWNER = { name: '蕭苰栯', role: '新郎' };
const LEVELS = ['edit', 'view'];   // 可編輯／只能看

// 共 12 桌：主桌 12 人、第 1–10 桌各 10 人、素食桌 10 人
const DEFAULT_TABLES = [
  { no: '主桌', cap: 12, note: '' },
  { no: '1', cap: 10, note: '' }, { no: '2', cap: 10, note: '' }, { no: '3', cap: 10, note: '' },
  { no: '4', cap: 10, note: '' }, { no: '5', cap: 10, note: '' }, { no: '6', cap: 10, note: '' },
  { no: '7', cap: 10, note: '' }, { no: '8', cap: 10, note: '' }, { no: '9', cap: 10, note: '' },
  { no: '10', cap: 10, note: '' },
  { no: '素食桌', cap: 10, note: '全素' },
];

/** 第一次部署前，在編輯器選 setup 按「執行」一次 */
function setup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let g = ss.getSheetByName(SHEET_GUESTS);
  if (!g) g = ss.insertSheet(SHEET_GUESTS);
  g.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]).setFontWeight('bold').setBackground('#F3EBE0');
  g.setFrozenRows(1);
  g.getRange(1, 1, g.getMaxRows(), HEADERS.length).setNumberFormat('@'); // 全部當文字存，手機開頭的 0 才不會不見

  let t = ss.getSheetByName(SHEET_TABLES);
  if (!t) {
    t = ss.insertSheet(SHEET_TABLES);
    t.getRange(1, 1, 1, 3).setValues([['桌號', '座位數', '備註']]).setFontWeight('bold').setBackground('#F3EBE0');
    t.getRange('A:A').setNumberFormat('@');
    t.getRange(2, 1, DEFAULT_TABLES.length, 3).setValues(DEFAULT_TABLES.map(x => [x.no, x.cap, x.note]));
    t.setFrozenRows(1);
  }

  // 產生新郎（擁有者）的密碼，已經有的不會被覆蓋。其他人的權限登入後台後再發放
  const props = PropertiesService.getScriptProperties();
  if (!props.getProperty('KEY_OWNER')) props.setProperty('KEY_OWNER', randKey());
  Logger.log('新郎（擁有者）的後台密碼：' + props.getProperty('KEY_OWNER'));
  Logger.log('要給新娘、婚禮秘書、媒人婆權限：用上面的密碼登入後台，到「權限管理」分頁發放。');
  Logger.log('要修改新郎的密碼：左側 ⚙️ 專案設定 → 指令碼屬性，修改 KEY_OWNER 的值');
}

/**
 * 忘記新郎的後台密碼時用：在編輯器上方選 showMyPassword，按「執行」，下方的執行紀錄會顯示目前的密碼。
 * 不會更改任何資料。
 */
function showMyPassword() {
  const key = PropertiesService.getScriptProperties().getProperty('KEY_OWNER');
  Logger.log(key ? '新郎（擁有者）目前的後台密碼：' + key : '還沒有密碼，請先執行 setup');
}

function doGet() {
  return json({ ok: true, msg: '婚宴回覆 API 運作中' });
}

function doPost(e) {
  let body;
  try {
    body = JSON.parse(e.postData.contents);
  } catch (err) {
    return json({ ok: false, error: '資料格式錯誤' });
  }
  try {
    if (body.action === 'rsvp') return json(handleRsvp(body));
    const me = requireAdmin(body);
    const edit = () => { if (me.level === 'view') throw new Error('你的權限是「只能看」，不能修改'); };
    const owner = () => { if (me.level !== 'owner') throw new Error('只有新郎可以管理權限'); };
    switch (body.action) {
      case 'admin_list': return json(adminList(me));
      case 'admin_save': edit(); return json(adminSave(body.id, body.guest || {}, me.stamp));
      case 'admin_assign': edit(); return json(adminAssign(body.id, body.idx, body.table, me.stamp));
      case 'admin_delete': edit(); return json(adminDelete(body.id));
      case 'admin_tables': edit(); return json(adminSaveTables(body.tables));
      case 'admin_set_key': return json(setMyKey(me, body.newKey));
      case 'admin_users': owner(); return json({ ok: true, users: readUsers() });
      case 'admin_user_save': owner(); return json(userSave(body.user || {}));
      case 'admin_user_delete': owner(); return json(userDelete(body.uid));
      default: return json({ ok: false, error: '未知的動作' });
    }
  } catch (err) {
    return json({ ok: false, error: String(err.message || err) });
  }
}

// ------------------------------------------------------------ 資料整理（賓客填表和後台編輯共用）

/**
 * 把送進來的資料檢查、整理成固定格式。
 * admin=true（後台手動新增／編輯）時手機可以不填。
 */
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
    name: name, phone: phone, side: SIDES.indexOf(b.side) >= 0 ? b.side : '',
    attend: attend, selfveg: attend && !!b.selfveg, companions: companions, kids: kids,
    paper: paper, address: address, message: clean(b.message, 300),
  };
}

/** 資料更新後重新對齊座位：本人的座位保留；同一個位置、同一個名字的同行親友也保留 */
function fitSeats(old, g) {
  if (!g.attend) return [];
  const seats = [];
  for (let i = 0; i <= g.companions.length; i++) seats.push('');
  if (old && old.attend) {
    seats[0] = old.seats[0] || '';
    g.companions.forEach((c, i) => {
      const oc = old.companions[i];
      if (oc && oc.name === c.name) seats[i + 1] = old.seats[i + 1] || '';
    });
  }
  return seats;
}

// ------------------------------------------------------------ 賓客回覆

function handleRsvp(b) {
  if (b.website) return { ok: true, updated: false }; // 防機器人的隱藏欄位
  const inp = normInput(b, false);

  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    const sh = sheet(SHEET_GUESTS);
    const found = readGuests(sh).find(g => g.phone && g.phone === inp.phone);
    if (found) {
      const seats = fitSeats(found, inp);
      // 後台已經標過男方／女方的話，以後台為準，不被賓客重填蓋掉
      Object.assign(found, inp, { side: found.side || inp.side, seats: seats, updatedAt: now(), edits: found.edits + 1 });
      writeGuest(sh, found._row, found);
      return { ok: true, updated: true, name: inp.name };
    }
    const g = Object.assign({ id: newId(), createdAt: now(), updatedAt: now(), relation: '', edits: 0, editedBy: '' },
      inp, { seats: fitSeats(null, inp) });
    writeGuest(sh, sh.getLastRow() + 1, g);
    return { ok: true, updated: false, name: inp.name };
  } finally {
    lock.releaseLock();
  }
}

// ------------------------------------------------------------ 管理後台

/** 檢查密碼，回傳登入的人：{ name, role, level（owner／edit／view）, stamp（記錄修改者用） } */
function requireAdmin(b) {
  const key = String(b.key || '');
  let me = null;
  if (key && key === PropertiesService.getScriptProperties().getProperty('KEY_OWNER')) {
    me = { name: OWNER.name, role: OWNER.role, level: 'owner' };
  } else if (key) {
    const u = readUsers().find(x => x.key === key);
    if (u) me = { uid: u.uid, name: u.name, role: u.role, level: u.level };
  }
  if (!me) {
    Utilities.sleep(1200); // 減緩猜密碼
    throw new Error('密碼錯誤，或權限已被收回');
  }
  me.stamp = me.name + '（' + me.role + '）';
  return me;
}

function adminList(me) {
  const guests = readGuests(sheet(SHEET_GUESTS)).map(g => { delete g._row; return g; });
  return { ok: true, me: { name: me.name, role: me.role, level: me.level }, guests: guests, tables: readTables() };
}

// ------------------------------------------------------------ 權限管理（只有新郎可以用）

function readUsers() {
  const list = parseJson(PropertiesService.getScriptProperties().getProperty('USERS'), []);
  return list.filter(u => u && u.uid && u.key);
}

function writeUsers(list) {
  PropertiesService.getScriptProperties().setProperty('USERS', JSON.stringify(list));
}

/** 檢查自訂密碼：6–40 個字、不能有空白，而且不能和別人的密碼一樣（exceptUid 是自己，不用和自己比） */
function checkKey(k, exceptUid) {
  k = String(k === undefined || k === null ? '' : k).trim();
  if (k.length < 6 || k.length > 40) throw new Error('密碼長度要 6 到 40 個字');
  if (/\s/.test(k)) throw new Error('密碼不能有空白');
  const ownerKey = PropertiesService.getScriptProperties().getProperty('KEY_OWNER');
  if (exceptUid !== 'OWNER' && k === ownerKey) throw new Error('這組密碼已經有人使用，請換一組');
  if (readUsers().some(u => u.key === k && u.uid !== exceptUid)) throw new Error('這組密碼已經有人使用，請換一組');
  return k;
}

/** 修改自己的密碼（新郎或被發放權限的人都可以改自己的） */
function setMyKey(me, newKey) {
  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    if (me.level === 'owner') {
      PropertiesService.getScriptProperties().setProperty('KEY_OWNER', checkKey(newKey, 'OWNER'));
    } else {
      const k = checkKey(newKey, me.uid);
      const list = readUsers();
      const x = list.find(v => v.uid === me.uid);
      if (!x) throw new Error('找不到你的權限');
      x.key = k;
      writeUsers(list);
    }
    return { ok: true };
  } finally {
    lock.releaseLock();
  }
}

/** 發放一份新權限（uid 留空），或修改既有的；regen=true 會換一組新密碼（舊密碼立刻失效）；key 有填就用自訂的密碼 */
function userSave(u) {
  const name = clean(u.name, 20), role = clean(u.role, 20);
  if (!name) throw new Error('請填寫稱呼');
  if (!role) throw new Error('請填寫身分');
  const level = LEVELS.indexOf(u.level) >= 0 ? u.level : 'view';
  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    const list = readUsers();
    if (u.uid) {
      const x = list.find(v => v.uid === u.uid);
      if (!x) throw new Error('找不到這份權限');
      x.name = name; x.role = role; x.level = level;
      if (u.key) x.key = checkKey(u.key, x.uid);
      else if (u.regen) x.key = randKey();
    } else {
      if (list.length >= 20) throw new Error('最多發放 20 份權限');
      list.push({ uid: 'U' + Date.now().toString(36).toUpperCase(), name: name, role: role, level: level, key: u.key ? checkKey(u.key, '') : randKey(), createdAt: now() });
    }
    writeUsers(list);
    return { ok: true, users: list };
  } finally {
    lock.releaseLock();
  }
}

/** 收回權限：那個人的密碼立刻失效 */
function userDelete(uid) {
  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    const list = readUsers().filter(v => v.uid !== uid);
    writeUsers(list);
    return { ok: true, users: list };
  } finally {
    lock.releaseLock();
  }
}

/** 後台新增（id 留空）或編輯一筆賓客資料 */
function adminSave(id, input, role) {
  const inp = normInput(input, true);
  inp.relation = clean(input.relation, 20);
  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    const sh = sheet(SHEET_GUESTS);
    const all = readGuests(sh);
    const stamp = role + ' ' + now();
    if (inp.phone && all.some(g => g.phone === inp.phone && g.id !== id)) throw new Error('這支手機號碼已經有另一筆回覆了');
    if (id) {
      const g = all.find(x => x.id === id);
      if (!g) throw new Error('找不到這位賓客');
      const seats = fitSeats(g, inp);
      Object.assign(g, inp, { seats: seats, updatedAt: now(), editedBy: stamp });
      writeGuest(sh, g._row, g);
      return { ok: true, id: id };
    }
    const g = Object.assign({ id: newId(), createdAt: now(), updatedAt: now(), edits: 0, editedBy: stamp }, inp, { seats: fitSeats(null, inp) });
    writeGuest(sh, sh.getLastRow() + 1, g);
    return { ok: true, id: g.id };
  } finally {
    lock.releaseLock();
  }
}

/** 排桌：idx 是第幾個人（0 = 本人，1 起 = 同行親友），傳 'all' 表示整組一起排 */
function adminAssign(id, idx, table, role) {
  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    const sh = sheet(SHEET_GUESTS);
    const g = readGuests(sh).find(x => x.id === id);
    if (!g) throw new Error('找不到這位賓客');
    if (!g.attend) throw new Error('這位賓客沒有要出席');
    const t = clean(table, 20);
    const n = 1 + g.companions.length;
    while (g.seats.length < n) g.seats.push('');
    g.seats.length = n;
    if (idx === 'all') {
      for (let i = 0; i < n; i++) g.seats[i] = t;
    } else {
      const i = int(idx);
      if (i < 0 || i >= n) throw new Error('找不到這個座位');
      g.seats[i] = t;
    }
    g.editedBy = role + ' ' + now();
    writeGuest(sh, g._row, g);
    return { ok: true };
  } finally {
    lock.releaseLock();
  }
}

function adminDelete(id) {
  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    const sh = sheet(SHEET_GUESTS);
    const g = readGuests(sh).find(x => x.id === id);
    if (!g) throw new Error('找不到這位賓客');
    sh.deleteRow(g._row);
    return { ok: true };
  } finally {
    lock.releaseLock();
  }
}

function adminSaveTables(tables) {
  if (!Array.isArray(tables) || tables.length > 60) throw new Error('桌次資料錯誤');
  const vals = tables.map(t => [clean(t.no, 20), Math.max(0, Math.min(30, int(t.cap))), clean(t.note, 40)])
    .filter(v => v[0]);
  const sh = sheet(SHEET_TABLES);
  if (sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, 3).clearContent();
  if (vals.length) sh.getRange(2, 1, vals.length, 3).setValues(vals);
  return { ok: true, tables: readTables() };
}

// ------------------------------------------------------------ 試算表讀寫

function sheet(name) {
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
  if (!sh) throw new Error('找不到工作表「' + name + '」，請先執行 setup');
  return sh;
}

/** 讀出所有賓客，轉成程式好用的格式 */
function readGuests(sh) {
  const n = sh.getLastRow() - 1;
  if (n < 1) return [];
  return sh.getRange(2, 1, n, COLS.length).getDisplayValues().map((v, i) => {
    const r = {};
    COLS.forEach((c, j) => { r[c] = v[j]; });
    return {
      _row: i + 2, id: r.id, createdAt: r.createdAt, updatedAt: r.updatedAt,
      name: r.name, phone: normPhone(r.phone), side: r.side, relation: r.relation,
      attend: r.attend === '出席', selfveg: r.selfveg === '是', kids: int(r.kids),
      companions: parseJson(r.data, []), seats: parseJson(r.seats, []),
      paper: r.paper === '要', address: r.address, message: r.message,
      edits: int(r.edits), editedBy: r.editedBy,
    };
  }).filter(g => g.id);
}

/** 寫回試算表：人數、葷素、同行親友文字、桌號這些給人看的欄位都從資料算出來 */
function writeGuest(sh, row, g) {
  const count = g.attend ? 1 + g.companions.length : 0;
  const veg = g.attend ? (g.selfveg ? 1 : 0) + g.companions.filter(c => c.veg).length : 0;
  const tables = [];
  (g.seats || []).forEach(t => { if (t && tables.indexOf(t) < 0) tables.push(t); });
  const o = {
    id: g.id, createdAt: g.createdAt, updatedAt: g.updatedAt, name: g.name, phone: g.phone,
    side: g.side, relation: g.relation || '', attend: g.attend ? '出席' : '不克出席',
    count: count, meat: count - veg, veg: veg, kids: g.kids, selfveg: g.selfveg ? '是' : '',
    companions: g.companions.map(c => c.name + (c.phone ? ' ' + c.phone : '') + (c.veg ? '（素）' : '')).join('、'),
    paper: g.paper ? '要' : '不用', address: g.address, message: g.message,
    table: tables.join('、'), edits: g.edits, editedBy: g.editedBy || '',
    data: JSON.stringify(g.companions), seats: JSON.stringify(g.seats || []),
  };
  sh.getRange(row, 1, 1, COLS.length).setNumberFormat('@')
    .setValues([COLS.map(c => (o[c] === undefined || o[c] === null) ? '' : String(o[c]))]);
}

function readTables() {
  const sh = sheet(SHEET_TABLES);
  const n = sh.getLastRow() - 1;
  if (n < 1) return [];
  return sh.getRange(2, 1, n, 3).getDisplayValues()
    .filter(v => v[0]).map(v => ({ no: v[0], cap: int(v[1]), note: v[2] }));
}

// ------------------------------------------------------------ 工具

function now() {
  return Utilities.formatDate(new Date(), 'Asia/Taipei', 'yyyy/MM/dd HH:mm');
}

function randKey() {
  return Utilities.getUuid().replace(/-/g, '').slice(0, 10);
}

function newId() {
  return 'G' + Date.now().toString(36).toUpperCase() + Math.floor(Math.random() * 36).toString(36).toUpperCase();
}

function normPhone(p) {
  let d = String(p || '').replace(/\D/g, '');
  if (d.indexOf('886') === 0) d = '0' + d.slice(3);
  return /^0\d{8,9}$/.test(d) ? d : '';
}

/** 去除前後空白、限制長度，並避免被試算表當成公式 */
function clean(s, max) {
  s = String(s === undefined || s === null ? '' : s).replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, max);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function parseJson(s, fallback) {
  try {
    const v = JSON.parse(s);
    return Array.isArray(v) ? v : fallback;
  } catch (e) {
    return fallback;
  }
}

function int(x) {
  const n = parseInt(x, 10);
  return isNaN(n) ? 0 : n;
}

function json(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
