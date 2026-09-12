// Dung khoi 3D cua may bang CSS transform, chay theo vi tri thuc cua 3 truc.
// Khong dung thu vien ngoai: Orange Pi va may tram xuong khong can tai them gi.
// Chi ve - khong goi API, khong quyet dinh gi.

const STAGE_H = 460;         // chieu cao khung, phai trung voi .viz3d trong CSS
const MARGIN_X = 80;         // chua cho phan khay thut ra sau khi xoay
const MARGIN_Y = 80;         // chua cho ray va so doc truc
const SCALE_MIN = 0.14;
const SCALE_MAX = 1.10;

// Kich thuoc ro va mam deu suy ra tu so THAT trong cau hinh, khong dat cung pixel.
// Nho vay doi buoc khay hay be rong khay tren web la hinh ve doi theo.
let dim = {};

function measure() {
  // Tat ca deu lay thang tu kich thuoc that trong cau hinh - khong con so pixel
  // dat cung nao o day nua. Doi kich thuoc ro tren web la hinh ve doi theo.
  dim = {
    basketLen: geometry.basket_length,
    basketDep: geometry.basket_depth,
    wallH: geometry.basket_height,
    // Mam treo CAO HON mieng ro nen duoc phep dai hon buoc khay - luc di ngang
    // no bay qua ben tren cac ro khac chu khong lot vao trong.
    plateLen: geometry.tray_length,
    plateDep: geometry.tray_width,
  };
}

/** Buoc khay doc truc X. La so suy ra, khong nam trong cau hinh gui ve. */
const pitch = () => geometry.basket_length + geometry.basket_gap;

const VIEW_START = { azim: -32, elev: 16 };
const ELEV_RANGE = { min: -12, max: 74 };

let root = null;             // khung ngoai, noi bat su kien keo chuot
let scene = null;            // khoi xoay
let parts = {};              // cac mieng phai cap nhat moi vong
let geometry = null;
let scale = 1;
let view = { ...VIEW_START };

/* ============================================================ dung cay DOM */

function div(className, text = null) {
  const node = document.createElement('div');
  node.className = className;
  if (text !== null) node.textContent = text;
  return node;
}

/** mm thuc -> pixel tren man hinh. Moi cho dat kich thuoc deu di qua day. */
const mm = (value) => value * scale;

/** Ty le phai vua CA HAI chieu: het hanh trinh ngang va het hanh trinh cao.
 *
 *  Lay theo hanh trinh chu khong theo cho dat khay, vi dau cong tac chay duoc
 *  toi bat ky dau nao trong hanh trinh - ve theo khay thi no se lot ra ngoai.
 */
function spanX(slots) {
  const farthest = Math.max(...slots.map((s) => s.x), geometry.park_x ?? 0);
  return Math.max(geometry.x_travel, farthest + pitch());
}

function fitScale(container, slots) {
  const box = container.getBoundingClientRect();
  const usableW = Math.max(280, box.width - MARGIN_X * 2);
  const usableH = STAGE_H - MARGIN_Y * 2;

  return clamp(Math.min(usableW / spanX(slots), usableH / geometry.z_travel),
               SCALE_MIN, SCALE_MAX);
}

/** Nhan chu noi tren khong, tu xoay nguoc lai goc nhin nen luon doc duoc.
 *
 *  Khoi canh xoay rotateX(elev) roi rotateY(azim). Muon chu dung thang thi phai
 *  xoay nguoc dung thu tu dao lai: rotateY(-azim) truoc, rotateX(-elev) sau.
 *  Neu dan chu len mat phang nam ngang thi no nam up theo mat do, khong doc duoc.
 */
function buildTag(lines) {
  const node = div('viz3d__tag');
  // Nhan phai NAM GON trong mat ro chu khong phu kin no.
  //
  // Truoc day chi do theo be ngang ro. Voi may that - ro dai 350mm, hanh trinh
  // Z 1300mm - ca gian bi thu nho lai vua khung, nen nhan rong dung bang be
  // ngang ro va che kin mat ro, khong con nhin thay cai gi ben trong.
  //
  // Gio chan bang CA HAI chieu roi lay cai nho hon: ro thap thi chu nho theo
  // chieu cao, ro hep thi nho theo be ngang.
  // Van can giua diem neo theo ca hai truc (CSS translate(-50%,-50%)) nen nhan
  // nam giua long ro, giong drawTags cua app.
  const cellW = mm(dim.basketLen);
  const cellH = mm(dim.wallH);
  // KHONG dat width: nhan chi con mot con so nen de no tu co vua noi dung -
  // dat rong co dinh la lai thanh tam ban che mat ro nhu truoc.
  //
  // Con so an theo CAI HOP: ro to thi so to theo, ro nho thi so nho lai. Vi chi
  // con mot con so nen cho no chiem han nua mat ro van doc thoai mai ma khong
  // che - khac han hoi con keo theo ma don, luc do phai bop nho moi vua.
  const font = clamp(Math.min(cellW * 0.26, cellH * 0.32), 8, 24);
  node.style.fontSize = `${font}px`;
  lines.forEach(([cls, text]) => node.append(div(cls, text)));
  return node;
}

function place(node, x, y, z, extra = '') {
  node.style.transform = `translate3d(${mm(x)}px, ${-mm(y)}px, ${mm(z)}px) ${extra}`;
  return node;
}

/* ================================================================ tung mieng */

/** Goc toa do man hinh dat tai tram nap, nen moi khay deu nam ve phia duong. */
const fromPark = (x) => x - (geometry.park_x ?? 0);

function buildFloor() {
  const node = div('viz3d__floor');
  node.style.width = `${mm(geometry.x_travel) + 160}px`;
  node.style.height = `${mm((geometry.rack_offset || 95) * 2) + 220}px`;
  node.style.marginLeft = `${-80}px`;
  node.style.marginTop = `${-(mm((geometry.rack_offset || 95) * 2) + 220) / 2}px`;
  return node;
}

function buildRail() {
  const node = div('viz3d__rail');
  node.style.width = `${mm(geometry.x_travel)}px`;
  return node;
}

/** Tram nap = vi tri cho. Vien dut o goc toa do de doi chieu voi khay. */
function buildDock() {
  const node = div('viz3d__dock');
  node.append(div('viz3d__dock-pad'), buildTag([['viz3d__dock-text', 'HOME']]));
  return place(node, 0, geometry.park_z ?? 0, 0);
}

/** Mot thanh ro. Bon thanh quay quanh day tao thanh long ro rong mieng huong len. */
function buildWall(w, h, transform) {
  const node = div('viz3d__wall');
  node.style.width = `${w}px`;
  node.style.height = `${h}px`;
  // Mieng ro nam o goc neo, thanh ro thong XUONG duoi - nen margin-top = 0.
  node.style.margin = `0 0 0 ${-w / 2}px`;
  node.style.transform = transform;
  return node;
}

/** Tam phang nam ngang, dung cho day ro va cho mam. */
function buildPad(className, lenPx, depPx) {
  const node = div(className);
  node.style.width = `${lenPx}px`;
  node.style.height = `${depPx}px`;
  node.style.margin = `${-depPx / 2}px 0 0 ${-lenPx / 2}px`;
  return node;
}

/** Mot o khay: ro nam ngang, mieng huong len, dat cach ray dung bang rack_offset. */
function buildSlot(row) {
  const node = div('viz3d__slot');
  node.dataset.slot = row.slot;
  node.classList.toggle('is-lower', row.row === 'bottom');
  node.classList.toggle('is-full', !!row.full);

  const len = mm(dim.basketLen);
  const dep = mm(dim.basketDep);
  const wall = mm(dim.wallH);

  // Mieng ro o cao do rack_z, long ro thut XUONG duoi mieng dung bang chieu cao thanh.
  node.append(
    // Chi so khay. Ma don va so vat da co san tren luoi khay o tren, nhac lai
    // o day chi lam nhan phinh to che mat ro - ma khoi 3D la de nhin CHO, khong
    // phai de doc so lieu.
    buildTag([['viz3d__slot-num', row.slot]]),
    place(buildPad('viz3d__floorplate', len, dep), 0, -dim.wallH, 0, 'rotateX(90deg)'),
    buildWall(len, wall, `translate3d(0, 0, ${dep / 2}px)`),
    buildWall(len, wall, `translate3d(0, 0, ${-dep / 2}px)`),
    buildWall(dep, wall, `translate3d(${-len / 2}px, 0, 0) rotateY(90deg)`),
    buildWall(dep, wall, `translate3d(${len / 2}px, 0, 0) rotateY(90deg)`),
  );

  // rack_offset = khoang cach tu tam ray toi MEP TRONG cua ro (dung nhu phep kiem
  // goc lat dang hieu), nen tam ro nam xa hon nua be sau.
  const depth = row.dir * (geometry.rack_offset + dim.basketDep / 2);
  // row.rack_z la do cao MIENG RO. row.z cao hon chung ay drop_lift - do la cho
  // khay DUNG khi do, khong phai cho dat ro.
  return place(node, fromPark(row.x), row.rack_z ?? row.z, depth);
}

/** Cot dung + dau cong tac + khay lat. Hai tam vuong goc nhau cho ra khoi 3D. */
function buildGantry() {
  const gantry = div('viz3d__gantry');

  const height = `${mm(geometry.z_travel)}px`;

  // Dau cong tac va cot khong co so do that trong cau hinh, nhung cung KHONG
  // duoc dat cung pixel: o ty le nho (may that cao 1300mm nen scale ~0.23) thanh
  // ngang 54px con to hon ca cai mam 51px no dang do, nhin nhu thung ra hai ben.
  //
  // Suy theo MAM - thu duy nhat o day co so do that. Ba he so duoi lay dung ty le
  // cu o may nho (mam 165px -> thanh 54px, day 14px, cot 9px) nen hinh ve giu
  // nguyen dang quen thuoc, chi khac la gio no co gian theo may.
  const plateLen = mm(dim.plateLen);
  const headW = Math.max(plateLen * 0.33, 8);
  const headH = Math.max(headW * 0.26, 3);
  // Cot truc Z day theo CHINH CHIEU CAO cua no chu khong theo cai mam: cot la
  // ket cau chiu luc, may cang cao thi cot cang phai to. Lay theo mam thi may
  // that (cao 1300mm, scale nho) ra cot 2.8px - mong nhu soi chi.
  const mastW = clamp(mm(geometry.z_travel) * 0.03, 5, 18);

  const mastA = div('viz3d__mast');
  const mastB = div('viz3d__mast viz3d__mast--b');
  mastA.style.height = mastB.style.height = height;
  mastA.style.marginTop = mastB.style.marginTop = `-${height}`;
  [mastA, mastB].forEach((mast) => {
    mast.style.width = `${mastW}px`;
    mast.style.marginLeft = `${-mastW / 2}px`;
  });

  parts.plate = buildPad('viz3d__plate', plateLen, mm(dim.plateDep));
  parts.plate.append(buildPad('viz3d__load', mm(dim.plateLen) * 0.42,
                                             mm(dim.plateDep) * 0.42));

  const head = (extra = '') => {
    const node = div(`viz3d__head${extra}`);
    node.style.width = `${headW}px`;
    node.style.height = `${headH}px`;
    node.style.margin = `${-headH / 2}px 0 0 ${-headW / 2}px`;
    return node;
  };

  parts.carriage = div('viz3d__carriage');
  parts.carriage.append(head(), head(' viz3d__head--b'), parts.plate);

  gantry.append(mastA, mastB, parts.carriage);
  parts.gantry = gantry;
  return gantry;
}

function buildHud() {
  parts.hud = {};
  const box = div('viz3d__hud');

  [['X', 'mm'], ['Y', '°'], ['Z', 'mm']].forEach(([axis, unit]) => {
    const cell = div(`viz3d__hud-cell viz3d__hud-cell--${axis.toLowerCase()}`);
    const value = div('viz3d__hud-val', '0');
    cell.append(div('viz3d__hud-key', `${axis} ${unit}`), value);
    parts.hud[axis.toLowerCase()] = value;
    box.append(cell);
  });

  return box;
}

/* ============================================================== keo de xoay */

function applyView() {
  scene.style.setProperty('--azim', `${view.azim}deg`);
  scene.style.setProperty('--elev', `${view.elev}deg`);
}

function bindDrag(stage) {
  let from = null;

  stage.addEventListener('pointerdown', (event) => {
    from = { mx: event.clientX, my: event.clientY, ...view };
    stage.setPointerCapture(event.pointerId);
    stage.classList.add('is-dragging');
  });

  stage.addEventListener('pointermove', (event) => {
    if (!from) return;
    view.azim = from.azim + (event.clientX - from.mx) * 0.4;
    view.elev = Math.min(ELEV_RANGE.max,
                Math.max(ELEV_RANGE.min, from.elev - (event.clientY - from.my) * 0.3));
    applyView();
  });

  ['pointerup', 'pointercancel', 'pointerleave'].forEach((name) =>
    stage.addEventListener(name, () => {
      from = null;
      stage.classList.remove('is-dragging');
    }));

  stage.addEventListener('dblclick', () => { view = { ...VIEW_START }; applyView(); });
}

/* =================================================================== ben ngoai */

export function initViz(container, geo, slotRows) {
  geometry = geo;
  scale = fitScale(container, slotRows);
  measure();
  parts = {};

  // Phoi canh duoc tinh tu tam khung. Neu de goc toa do o goc trai duoi thi phan
  // xa tam bi keo xien - nen dat mo hinh vao mot lop rieng va day tam no ve giua.
  const model = div('viz3d__model');
  model.style.transform =
    `translate3d(${-mm(spanX(slotRows)) / 2}px, ${mm(geometry.z_travel) / 2}px, 0)`;

  model.append(buildFloor(), buildRail(), buildDock());
  slotRows.forEach((row) => model.append(buildSlot(row)));
  model.append(buildGantry());

  scene = div('viz3d__scene');
  scene.append(model);

  root = div('viz3d');
  root.append(scene, buildHud());

  applyView();
  bindDrag(root);
  container.replaceChildren(root);

  // ve ngay mot lan o vi tri cho, khong doi goi trang thai dau tien
  updateViz({ x: geometry.park_x ?? 0, y: geometry.park_y ?? 0, z: geometry.park_z ?? 0 });
}

/** Cap nhat vi tri 3 truc va o dang duoc nham toi. Goi moi lan co trang thai moi. */
/** To sang cai ro vua bam tren luoi khay, de biet no nam CHO NAO tren gian.
 *
 *  Cung mau vang voi is-target, chi nhat hon: ro vua bam thuong chinh la ro may
 *  sap chay toi, doi mau giua chung thi mat dau cai dang theo doi. Xem ghi chu
 *  o .viz3d__slot.is-picked trong styles.css.
 */
export function markPickedSlot(slot) {
  if (!root) return;
  root.querySelectorAll('.viz3d__slot').forEach((node) => {
    node.classList.toggle('is-picked', Number(node.dataset.slot) === slot && slot > 0);
  });
}

export function updateViz(status, targetSlot = null) {
  if (!root || !geometry) return;

  const x = clamp(status.x ?? 0, 0, geometry.x_travel);
  const z = clamp(status.z ?? 0, 0, geometry.z_travel);
  const y = status.y ?? 0;

  place(parts.gantry, fromPark(x), 0, 0);
  place(parts.carriage, 0, z, 0);
  // Khay nam ngang khi nghi nen goc goc la 90 do. Dau TRU vi rotateX duong lat
  // ve phia xa nguoi xem, ma day PHAI (dir = +1) lai nam phia gan.
  parts.plate.style.transform = `rotateX(${90 - y}deg)`;

  parts.hud.x.textContent = Math.round(x);
  parts.hud.y.textContent = Math.round(y);
  parts.hud.z.textContent = Math.round(z);

  root.classList.toggle('is-busy', !!status.busy);
  root.classList.toggle('is-error', !!status.error);

  root.querySelectorAll('.viz3d__slot').forEach((node) => {
    node.classList.toggle('is-target', Number(node.dataset.slot) === targetSlot && targetSlot > 0);
  });
}

/** Ve lai khi ton kho hoac toa do doi. Giu nguyen goc nhin nguoi dung dang xoay. */
export function refreshViz(geo, slotRows) {
  const container = root?.parentNode;
  if (container) initViz(container, geo, slotRows);
}

function clamp(value, low, high) {
  return Math.min(Math.max(value, low), high);
}
