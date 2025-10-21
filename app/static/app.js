// ===================== helpers =====================
async function getJSON(url){
  const r = await fetch(url);
  if(!r.ok) throw new Error(`Request failed ${r.status}`);
  return await r.json();
}
const TitleCase = s => (s||'').replace(/\b\w/g, c => c.toUpperCase());

// Fill for simple string arrays (token = value, label prettified or mapped)
function fillSelect(sel, values, placeholder, labelsMap){
  sel.innerHTML = '';
  const opt0 = document.createElement('option');
  opt0.value=''; opt0.textContent=placeholder||'Select';
  sel.appendChild(opt0);
  (values||[]).forEach(v=>{
    if(!v) return;
    const o=document.createElement('option');
    o.value=v; // submit the token
    o.textContent=(labelsMap && labelsMap[v]) ? labelsMap[v] : TitleCase(v);
    sel.appendChild(o);
  });
  sel.disabled=false;
}

// Fill using [{token,label}] and can show a visible "None"
function fillSelectWithObjects(sel, items, placeholder, includeNone = false){
  sel.innerHTML = '';
  const opt0 = document.createElement('option');
  opt0.value = '';
  opt0.textContent = placeholder || 'Select';
  sel.appendChild(opt0);

  if (includeNone) {
    const noneOpt = document.createElement('option');
    noneOpt.value = '';
    noneOpt.textContent = '— None —';
    sel.appendChild(noneOpt);
  }

  (items||[]).forEach(it=>{
    const token = (typeof it === 'string') ? it : it.token;
    const label = (typeof it === 'string') ? TitleCase(it) : (it.label || TitleCase(it.token));
    if(!token) return;
    const o=document.createElement('option');
    o.value = token;        // submit the model-aligned token
    o.textContent = label;  // show a nice label
    sel.appendChild(o);
  });
  sel.disabled=false;
}

function unique(arr){ return Array.from(new Set(arr||[])); }
function toItems(tokensArr, labelsMap){
  return (tokensArr || []).map(t => ({ token: t, label: (labelsMap && labelsMap[t]) ? labelsMap[t] : TitleCase(t) }));
}

// ===================== APPLY PAGE =====================
async function initApply(){
  const form = document.getElementById('applyForm');
  if(!form) return;

  // -------- DOM refs --------
  const firstProgram   = document.getElementById('firstProgram');
  const secondProgram  = document.getElementById('secondProgram');
  const currRegion     = document.getElementById('currRegion');
  const currProvince   = document.getElementById('currProvince');
  const currCity       = document.getElementById('currCity');
  const currBarangay   = document.getElementById('currBarangay');
  const perCountry     = document.getElementById('perCountry');
  const perRegion      = document.getElementById('perRegion');
  const perProvince    = document.getElementById('perProvince');
  const perCity        = document.getElementById('perCity');
  const perBarangay    = document.getElementById('perBarangay');
  const sameAsCurrent  = document.getElementById('sameAsCurrent');
  const studentType    = document.getElementById('studentType');
  const schoolType     = document.getElementById('schoolType');
  const dob            = document.getElementById('dob');
  const resultBox      = document.getElementById('result');

  // -------- Seed fallbacks (used if /api/options has nothing) --------
  const seedRegions = [
    'national capital region','ilocos region','western visayas',
    'negros island region','davao region','bangsamoro autonomous region in muslim mindanao'
  ];
  const seedCountries = ['philippines','others'];
  const COUNTRY_LABELS = { philippines: 'Philippines', others: 'Others' };

  // Build whitelist + label map for NU Lipa programs from your First Program HTML
  const domProgramTokens = Array.from(firstProgram.querySelectorAll('option'))
    .map(o => (o.value||'').trim().toLowerCase())
    .filter(v => v && v !== 'choose first program');
  const domProgramLabels = {};
  Array.from(firstProgram.querySelectorAll('option')).forEach(o=>{
    const v = (o.value||'').trim().toLowerCase();
    if(v && v !== 'choose first program') domProgramLabels[v] = (o.textContent||'').trim();
  });

  // -------- Load backend tokens (aligned to training_columns) --------
  let tokens = {};
  try { const opts = await getJSON('/api/options'); tokens = opts.tokens || {}; }
  catch(e){ console.warn('Failed to load /api/options:', e); tokens = {}; }

  const apiFirst  = Array.isArray(tokens['first program'])  ? tokens['first program']  : [];
  const apiSecond = Array.isArray(tokens['second program']) ? tokens['second program'] : [];
  const apiCountries = Array.isArray(tokens['permanent country']) ? tokens['permanent country'] : [];

  // Programs authoritative list:
  // prefer backend (alignment), filtered by NU Lipa whitelist; else use whitelist
  let allowedPrograms = [];
  if (apiFirst.length){
    if (domProgramTokens.length){
      const domSet = new Set(domProgramTokens);
      allowedPrograms = apiFirst.filter(t => domSet.has(t));
      if (!allowedPrograms.length) allowedPrograms = apiFirst.slice();
    } else {
      allowedPrograms = apiFirst.slice();
    }
  } else {
    allowedPrograms = domProgramTokens.slice();
  }
  allowedPrograms = unique(allowedPrograms);

  // Fill Program selects (Second mirrors First + visible None)
  const programItems = toItems(allowedPrograms, domProgramLabels);
  fillSelectWithObjects(firstProgram,  programItems, 'Choose first program',  /*includeNone*/ false);
  fillSelectWithObjects(secondProgram, programItems, 'Choose second program (optional)', /*includeNone*/ true);

  // -------- Student Type: Full-time / Working Student (tokens: 'full time'/'part time') --------
  const studentTypeItems = [
    { token: 'full time', label: 'Full-time' },
    { token: 'part time', label: 'Working Student' },
  ];
  fillSelectWithObjects(studentType, studentTypeItems, 'Student Type', /*includeNone*/ false);

  // -------- School Type: Private / Public --------
  const schoolTypeItems = [
    { token: 'private', label: 'Private' },
    { token: 'public',  label: 'Public'  },
  ];
  fillSelectWithObjects(schoolType, schoolTypeItems, 'School Type', /*includeNone*/ false);

  // -------- Country: always show options & default to Philippines --------
  const countryTokens = (apiCountries && apiCountries.length) ? apiCountries : seedCountries;
  fillSelect(perCountry, countryTokens, 'Country', COUNTRY_LABELS);
  const hasPH = [...perCountry.options].some(o => o.value === 'philippines');
  if (hasPH) {
    perCountry.value = 'philippines';
  } else if (perCountry.options.length > 1) {
    perCountry.selectedIndex = 1; // first non-placeholder
  }

  // -------- PSGC cascade (Region → Province → City/Mun → Barangay) --------
  const regionsResp   = await getJSON('/static/psgc/regions.json').catch(e=>{ console.warn('regions.json error', e); return []; });
  const provincesResp = await getJSON('/static/psgc/provinces.json').catch(e=>{ console.warn('provinces.json error', e); return []; });
  const citiesResp    = await getJSON('/static/psgc/cities.json').catch(e=>{ console.warn('cities.json error', e); return []; });
  const barangaysResp = await getJSON('/static/psgc/barangays.json').catch(e=>{ console.warn('barangays.json error', e); return []; });

  // Accept both shapes: {items:[...]} or flat [...]
  const REG  = Array.isArray(regionsResp)   ? regionsResp   : (regionsResp.items   || []);
  const PROV = Array.isArray(provincesResp) ? provincesResp : (provincesResp.items || []);
  const CITY = Array.isArray(citiesResp)    ? citiesResp    : (citiesResp.items    || []);
  const BRGY = Array.isArray(barangaysResp) ? barangaysResp : (barangaysResp.items || []);

  // Build label map for regions so UI shows numbers/acronyms from `name`
  const REG_LABELS = {};
  REG.forEach(r => { if (r && r.token && r.name) REG_LABELS[r.token] = r.name; });

  const regTokens = REG.length ? REG.map(r=>r.token) : seedRegions;
  fillSelect(currRegion, regTokens, 'Region', REG_LABELS);
  fillSelect(perRegion,  regTokens, 'Region', REG_LABELS);

  function onRegionChange(srcSel, provSel, citySel, brgySel){
    const regToken = srcSel.value;
    const reg = REG.find(r=>r.token===regToken);
    const regCode = reg ? reg.code : null;
    const provTokens = PROV.filter(p=>p.region_code===regCode).map(p=>p.token);
    fillSelect(provSel, provTokens, 'Province');
    citySel.disabled=true; brgySel.disabled=true;
    citySel.innerHTML = ''; brgySel.innerHTML = '';
  }
  function onProvinceChange(provSel, citySel, brgySel){
    const provToken = provSel.value;
    const prov = PROV.find(p=>p.token===provToken);
    const provCode = prov ? prov.code : null;
    const cityTokens = CITY.filter(c=>c.province_code===provCode).map(c=>c.token);
    fillSelect(citySel, cityTokens, 'City/Municipality');
    brgySel.disabled=true; brgySel.innerHTML = '';
  }
  function onCityChange(citySel, brgySel){
    const cityToken = citySel.value;
    const city = CITY.find(c=>c.token===cityToken);
    const cityCode = city ? city.code : null;
    const brgyTokens = BRGY.filter(b=>b.city_code===cityCode).map(b=>b.token);
    fillSelect(brgySel, brgyTokens, 'Barangay');
  }

  currRegion.addEventListener('change', ()=> onRegionChange(currRegion, currProvince, currCity, currBarangay));
  perRegion.addEventListener('change',  ()=> onRegionChange(perRegion,  perProvince,  perCity,  perBarangay));
  currProvince.addEventListener('change',()=> onProvinceChange(currProvince, currCity, currBarangay));
  perProvince.addEventListener('change', ()=> onProvinceChange(perProvince,  perCity,  perBarangay));
  currCity.addEventListener('change',   ()=> onCityChange(currCity,  currBarangay));
  perCity.addEventListener('change',    ()=> onCityChange(perCity,   perBarangay));

  // -------- Same as current --------
  sameAsCurrent.addEventListener('change', ()=>{
    if(!sameAsCurrent.checked) return;
    perCountry.value='philippines';
    perRegion.value=currRegion.value; perRegion.dispatchEvent(new Event('change'));
    setTimeout(()=>{ perProvince.value=currProvince.value; perProvince.dispatchEvent(new Event('change'));
      setTimeout(()=>{ perCity.value=currCity.value; perCity.dispatchEvent(new Event('change'));
        setTimeout(()=>{ perBarangay.value=currBarangay.value; },0);
      },0);
    },0);
  });

  // -------- Submit --------
  form.addEventListener('submit', async (e)=>{
    e.preventDefault();
    resultBox.textContent='Predicting...';
    const payload = {
      "first program": firstProgram.value,
      "second program": secondProgram.value || "",
      "current region": currRegion.value,
      "current province": currProvince.value,
      "current city/municipality": currCity.value,
      "permanent country": perCountry.value,     // defaults to 'philippines'
      "permanent region": perRegion.value,
      "permanent province": perProvince.value,
      "permanent city/municipality": perCity.value,
      "student type": studentType.value,         // 'full time' or 'part time'
      "school type": schoolType.value,           // 'private' or 'public'
      "dateofbirth": dob.value
    };
    const r = await fetch('/api/predict',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await r.json();
    if(!r.ok){ resultBox.textContent=`Error: ${data.message||'See console'}`; console.error(data); return; }
    const pct=(data.prob_enroll_pct*100).toFixed(2);
    const conf=(data.confidence*100).toFixed(2);
    resultBox.textContent=`Likelihood: ${pct}% • Confidence: ${conf}%`;
    localStorage.setItem('ai_last_result', JSON.stringify({ts:Date.now(),pct,conf}));
  });
}
document.addEventListener('DOMContentLoaded', initApply);

// ===================== ADMIN PAGE =====================
async function initAdmin(){
  const el = (id)=>document.getElementById(id);
  const latestPred = el('latestPred');
  const healthBox  = el('healthBox');

  const filterProgram = el('filterProgram');
  const filterRegion  = el('filterRegion');
  const filterBucket  = el('filterBucket');
  const filterMinConf = el('filterMinConf');
  const filterMinConfVal = el('filterMinConfVal');
  const filterDays = el('filterDays');
  const btnApply = el('applyFilters');
  const exportCsv = el('exportCsv');

  const kpiTotal   = el('kpiTotal');
  const kpiAvgProb = el('kpiAvgProb');
  const kpiAvgConf = el('kpiAvgConf');
  const kpiBuckets = el('kpiBuckets');

  const qCall = el('queueCallNow');
  const qWarm = el('queueWarm');
  const qNurt = el('queueNurture');

  // charts
  let chBuckets=null, chPrograms=null, chStudentType=null, chLocalForeign=null, chHistP=null, chHistC=null, chTrend=null, chHeat=null, chScatter=null;

  // table controls
  const tblSort  = el('tblSort');
  const tblDir   = el('tblDir');
  const tblSize  = el('tblSize');
  const tblApply = el('tblApply');
  const prevPage = el('prevPage');
  const nextPage = el('nextPage');
  const pageInfo = el('pageInfo');
  const tblMeta  = el('tblMeta');
  const tblBody  = document.querySelector('#topTable tbody');

  if (!filterDays) return; // not on this page

  // small helpers used by admin UI
  const titleize = TitleCase;
  const pct = x => `${(Number(x||0)*100).toFixed(1)}%`;
  const fmtDate = d => {
    if(!d) return '';
    const dt = new Date(d);
    if (isNaN(dt.getTime())) return String(d);
    return dt.toLocaleString();
  };
  function makeOrUpdateChart(ctx, existing, type, data, options){
    if(existing){ existing.data = data; existing.options = options || {}; existing.update(); return existing; }
    // global: rely on default colors; single chart per canvas
    // eslint-disable-next-line no-undef
    return new Chart(ctx, { type, data, options: options || {} });
  }

  // State
  let page = 1;
  let total = 0;

  // UI bindings
  filterMinConf.addEventListener('input', ()=> filterMinConfVal.textContent = Number(filterMinConf.value).toFixed(2));
  if (btnApply) btnApply.addEventListener('click', ()=> { page = 1; loadAll(); });
  if (tblApply) tblApply.addEventListener('click',  ()=> { page = 1; loadTable(); });
  if (prevPage) prevPage.addEventListener('click',  ()=> { if (page>1) { page--; loadTable(); }});
  if (nextPage) nextPage.addEventListener('click',  ()=> {
    const size = Number(tblSize?.value||25);
    const pages = Math.max(1, Math.ceil(total / size));
    if (page < pages) { page++; loadTable(); }
  });

  function buildQS(base){
    const days = Math.max(1, parseInt(filterDays.value||'30',10));
    const pc   = filterProgram.value || '';
    const rc   = filterRegion.value || '';
    const bkt  = filterBucket.value || '';
    const mc   = Number(filterMinConf.value || '0');
    const qs = new URLSearchParams({ days, min_conf: mc.toString() });
    if (pc) qs.set('program', pc);
    if (rc) qs.set('region', rc);
    if (bkt) qs.set('bucket', bkt);
    return `${base}?${qs.toString()}`;
  }

  async function loadAll(){
    const m = await getJSON(buildQS('/api/admin/metrics')).catch(()=>({ok:false}));
    if (!m || !m.ok) { console.warn('metrics failed', m); return; }

    // Filters
    const resetSel = (sel)=>{ if(sel) sel.innerHTML = '<option value="">All</option>'; };
    resetSel(filterProgram); resetSel(filterRegion);

    (m.program_tokens||[]).forEach(tok=>{
      const o = document.createElement('option'); o.value = tok; o.textContent = titleize(tok); filterProgram.appendChild(o);
    });
    (m.region_tokens||[]).forEach(tok=>{
      const o = document.createElement('option'); o.value = tok; o.textContent = titleize(tok); filterRegion.appendChild(o);
    });

    // KPIs
    if (kpiTotal)   kpiTotal.textContent   = String(m.summary?.n || 0);
    if (kpiAvgProb) kpiAvgProb.textContent = pct(m.summary?.avg_prob || 0);
    if (kpiAvgConf) kpiAvgConf.textContent = pct(m.summary?.avg_conf || 0);
    if (kpiBuckets) kpiBuckets.textContent = `${m.summary?.high || 0} / ${m.summary?.med || 0} / ${m.summary?.low || 0}`;

    // Queues
    const renderQueue = (ul, arr) => {
      if(!ul) return;
      ul.innerHTML = '';
      (arr||[]).forEach(r=>{
        const li = document.createElement('li');
        li.className = 'queue-row';
        li.innerHTML = `
          <span class="q-pri">${pct((r.prob||0)*(r.conf||0))}</span>
          <span class="q-prob">${pct(r.prob||0)}</span>
          <span class="q-conf">${pct(r.conf||0)}</span>
          <span class="q-prog">${titleize(r.first_program||'')}</span>
          <span class="q-seg">${titleize(r.student_type||'')}</span>
          <span class="q-reg">${titleize(r.curr_region||'')}</span>
        `;
        ul.appendChild(li);
      });
    };
    renderQueue(qCall, m.queues?.call_now || []);
    renderQueue(qWarm, m.queues?.warm || []);
    renderQueue(qNurt, m.queues?.nurture || []);

    // Charts
    const ctxB = document.getElementById('chartBuckets')?.getContext('2d');
    if (ctxB) chBuckets = makeOrUpdateChart(ctxB, chBuckets, 'doughnut', {
      labels: ['High','Medium','Low'],
      datasets: [{ data: [m.summary.high, m.summary.med, m.summary.low] }]
    });

    const ctxProg = document.getElementById('chartPrograms')?.getContext('2d');
    if (ctxProg){
      const progLab = (m.programs||[]).map(p=>titleize(p.program));
      const progCnt = (m.programs||[]).map(p=>p.count);
      chPrograms = makeOrUpdateChart(ctxProg, chPrograms, 'bar', {
        labels: progLab, datasets: [{ label:'Applicants', data: progCnt }]
      }, { indexAxis: 'y', scales: { x: { beginAtZero: true } } });
    }

    const ctxST = document.getElementById('chartStudentType')?.getContext('2d');
    if (ctxST){
      const stLab = (m.student_type||[]).map(x=>titleize(x.type));
      const stCnt = (m.student_type||[]).map(x=>x.count);
      chStudentType = makeOrUpdateChart(ctxST, chStudentType, 'pie', { labels: stLab, datasets: [{ data: stCnt }] });
    }

    const ctxLF = document.getElementById('chartLocalForeign')?.getContext('2d');
    if (ctxLF){
      const lfLab = (m.local_foreign||[]).map(x=>titleize(x.type));
      const lfCnt = (m.local_foreign||[]).map(x=>x.count);
      chLocalForeign = makeOrUpdateChart(ctxLF, chLocalForeign, 'bar', {
        labels: lfLab, datasets: [{ label:'Applicants', data: lfCnt }]
      });
    }

    const ctxHP = document.getElementById('chartHistProb')?.getContext('2d');
    if (ctxHP){
      chHistP = makeOrUpdateChart(ctxHP, chHistP, 'bar', {
        labels: Array.from({length:20}, (_,i)=>`${(i*5)}-${(i+1)*5}%`),
        datasets: [{ label:'Counts', data: (m.hist_prob||[]).map(x=>x||0) }]
      });
    }

    const ctxHC = document.getElementById('chartHistConf')?.getContext('2d');
    if (ctxHC){
      chHistC = makeOrUpdateChart(ctxHC, chHistC, 'bar', {
        labels: Array.from({length:20}, (_,i)=>`${(i*5)}-${(i+1)*5}%`),
        datasets: [{ label:'Counts', data: (m.hist_conf||[]).map(x=>x||0) }]
      });
    }

    const ctxT = document.getElementById('chartTrend')?.getContext('2d');
    if (ctxT){
      const tLab = (m.trend||[]).map(t=>t.date);
      const tProb = (m.trend||[]).map(t=>Number((t.avg_prob||0)*100).toFixed(2));
      const tConf = (m.trend||[]).map(t=>Number((t.avg_conf||0)*100).toFixed(2));
      chTrend = makeOrUpdateChart(ctxT, chTrend, 'line', {
        labels: tLab,
        datasets: [
          { label:'Avg Likelihood (%)', data: tProb, yAxisID:'y' },
          { label:'Avg Confidence (%)', data: tConf, yAxisID:'y1' },
        ]
      }, { scales: { y:{ beginAtZero:true, suggestedMax:100, position:'left' }, y1:{ beginAtZero:true, suggestedMax:100, position:'right', grid:{ drawOnChartArea:false } } } });
    }

    // Heatmap via bubble sizes on 10x10 grid
    const ctxH = document.getElementById('chartHeat')?.getContext('2d');
    if (ctxH){
      const bubbles = (m.heat||[]).map(pt=>({ x: pt.x, y: pt.y, r: Math.max(2, Math.sqrt(pt.count||1)*2) }));
      chHeat = makeOrUpdateChart(ctxH, chHeat, 'bubble', {
        datasets: [{ label:'Density', data: bubbles }]
      }, { scales: { x:{ min:0, max:100, title:{display:true, text:'Likelihood (%)'} }, y:{ min:0, max:100, title:{display:true, text:'Confidence (%)'} } } });
    }

    // Scatter
    const ctxS = document.getElementById('chartScatter')?.getContext('2d');
    if (ctxS){
      const pts = (m.top||[]).map(r=>({ x: Number((r.prob||0)*100), y: Number((r.conf||0)*100) }));
      chScatter = makeOrUpdateChart(ctxS, chScatter, 'scatter', {
        datasets: [{ label:'Applicants', data: pts }]
      }, { scales: { x:{ min:0, max:100, title:{display:true, text:'Likelihood (%)'} }, y:{ min:0, max:100, title:{display:true, text:'Confidence (%)'} } } });
    }

    // export link with filters
    if (exportCsv) exportCsv.href = buildQS('/api/admin/export.csv');

    // legacy boxes optional
    if (healthBox) healthBox.textContent = JSON.stringify({ models_loaded: true }, null, 2);
    if (latestPred && (m.top||[]).length){
      const r0 = m.top[0];
      latestPred.innerHTML = `<div class='pill'>${(r0.prob*100).toFixed(1)}%</div><div class='pill subtle'>conf ${(r0.conf*100).toFixed(1)}%</div>`;
    }

    // table
    page = 1;
    await loadTable();
  }

  async function loadTable(){
    const days = Math.max(1, parseInt(filterDays.value||'30',10));
    const qs = new URLSearchParams({
      days,
      page: String(page),
      page_size: String(Number(tblSize?.value||25)),
      sort: (document.getElementById('tblSort')?.value)||'priority',
      dir: (document.getElementById('tblDir')?.value)||'desc',
      min_conf: String(Number(filterMinConf.value||0))
    });
    if (filterProgram?.value) qs.set('program', filterProgram.value);
    if (filterRegion?.value)  qs.set('region', filterRegion.value);
    if (filterBucket?.value)  qs.set('bucket', filterBucket.value);

    const res = await getJSON(`/api/admin/table?${qs.toString()}`).catch(()=>({ok:false}));
    if (!res || !res.ok){ console.warn('table failed', res); return; }
    total = res.total || 0;

    // meta
    const size = Number(tblSize?.value||25);
    const pages = Math.max(1, Math.ceil(total / size));
    if (pageInfo) pageInfo.textContent = `Page ${res.page} of ${pages}`;
    if (tblMeta)  tblMeta.textContent  = `${total} records`;

    // rows
    if (tblBody){
      tblBody.innerHTML = '';
      (res.rows||[]).forEach(r=>{
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${pct(r.priority||0)}</strong></td>
          <td>${pct(r.prob||0)}</td>
          <td>${pct(r.conf||0)}</td>
          <td>${titleize(r.first_program||'')}</td>
          <td>${titleize(r.student_type||'')}</td>
          <td>${titleize(r.curr_region||'')}</td>
          <td>${fmtDate(r.created_at)}</td>
        `;
        tblBody.appendChild(tr);
      });
    }
  }

  // initial render
  await loadAll();
}
document.addEventListener('DOMContentLoaded', initAdmin);
