/* ============================================================
   PIEZAS — motor del espacio de contenido (multi-vista)
   Una sola máquina (window.PZ) sobre la tabla `guiones`.
   Reusa el `sb`, `esc` y `toast` globales del dashboard (app.js).

   Vistas (cada una es su contenedor <div class="view">):
     guiones    -> v-piezas      piezas (flujo='pieza') + importador + filtros + ficha
     parafilmar -> v-parafilmar  piezas en estado 'para_grabar'
     filmados   -> v-filmados    piezas 'grabado' o 'publicado'
     selector   -> v-selector    piezas 'idea'/'guionado' -> marcar 'para_grabar'
     archivo    -> v-archivo      guiones viejos (flujo=null) — leer / recuperar
   ============================================================ */
(function(){
'use strict';

var STATUS=['idea','guionado','para_grabar','grabado','editando','publicado'];
var STATUS_LBL={idea:'Idea',guionado:'Guionado',para_grabar:'Para grabar',grabado:'Grabado',editando:'Editando',publicado:'Publicado'};
var CLIENT=['inversor','vivienda','ambos'];
var CLIENT_LBL={inversor:'Inversor',vivienda:'Vivienda',ambos:'Ambos'};
var FORMAT=['pizarra','camara','numeros','explicativo','caso_real'];
var FORMAT_LBL={pizarra:'Pizarra',camara:'Cámara',numeros:'Números',explicativo:'Explicativo',caso_real:'Caso real'};
var PERF=['sin_datos','funciono','normal','no_funciono'];
var PERF_LBL={sin_datos:'Sin datos',funciono:'Funcionó',normal:'Normal',no_funciono:'No funcionó'};

var VIEWS={
    guiones:   {cont:'v-piezas',     grid:'pz-grid-guiones',    full:true},
    parafilmar:{cont:'v-parafilmar', grid:'pz-grid-parafilmar', title:'Para filmar',        sub:'Piezas listas para grabar.', empty:'Nada marcado para grabar todavía. Marcá "Para grabar" en la ficha o desde el Selector.', base:function(g){return (g.status||'')==='para_grabar';}},
    filmados:  {cont:'v-filmados',   grid:'pz-grid-filmados',   title:'Filmados',            sub:'Grabados y publicados.',     empty:'Todavía no marcaste ninguna pieza como grabada.', base:function(g){var s=g.status||'';return s==='grabado'||s==='publicado';}},
    selector:  {cont:'v-selector',   grid:'pz-grid-selector',   title:'Elegí qué filmar primero', sub:'Ideas y guiones nuevos. Tocá "Para grabar →" en las que quieras priorizar.', empty:'No hay piezas nuevas para elegir.', pick:true, base:function(g){var s=g.status||'';return s==='idea'||s==='guionado';}},
    archivo:   {cont:'v-archivo',    grid:'pz-grid-archivo',    archivo:true}
};

var all=[], allArch=[], archSel={}, curId=null, curView='guiones', overlaysBuilt=false, builtViews={};

function esc(s){ if(typeof window.esc==='function')return window.esc(s); var d=document.createElement('div');d.textContent=(s==null?'':s);return d.innerHTML; }
function toast(m,e){ if(typeof window.toast==='function')return window.toast(m,e); }
function el(id){return document.getElementById(id);}
function opt(v,l){return '<option value="'+v+'">'+l+'</option>';}
function findPiece(id){return all.find(function(x){return x.id===id;})||allArch.find(function(x){return x.id===id;});}

/* ---------- overlays (ficha + importar) — una sola vez en body ---------- */
function ensureOverlays(){
    if(overlaysBuilt)return;
    var d=document.createElement('div');
    d.innerHTML=[
'<div id="pz-ficha" class="pz-ficha-bg"><div class="pz-ficha">',
'  <div class="pz-ficha-head">',
'    <span class="fid" id="pz-fid"></span>',
'    <select id="pz-fstatus" onchange="PZ.quickStatus()" title="Estado"></select>',
'    <select id="pz-fperf" onchange="PZ.quickPerf()" title="Performance"></select>',
'    <span class="grow"></span>',
'    <button class="pz-btn" onclick="PZ.marcarPublicado()">Marcar publicado</button>',
'    <button class="pz-ficha-x" onclick="PZ.closeFicha()">&times;</button>',
'  </div>',
'  <div class="pz-ficha-body">',
'    <textarea id="pz-title" class="pz-in pz-title-in" rows="1" placeholder="Título de la pieza" oninput="PZ.grow(this)"></textarea>',
'    <div class="pz-hook-box"><div class="pz-lbl">Hook</div>',
'      <textarea id="pz-hook" class="pz-hook-in" rows="1" placeholder="Lo primero que digo frente a cámara..." oninput="PZ.grow(this)"></textarea></div>',
'    <div class="pz-meta-row">',
'      <div class="cell"><label>Cliente</label><select id="pz-fclient"></select></div>',
'      <div class="cell"><label>Formato</label><select id="pz-format"></select></div>',
'      <div class="cell"><label>Duración</label><input type="text" id="pz-dur" placeholder="60-75 seg"></div>',
'      <div class="cell"><label>Categoría</label><input type="text" id="pz-fcat" placeholder="pozo_vs_terminado"></div>',
'    </div>',
'    <div class="pz-lbl">Idea / dolor del cliente</div>',
'    <textarea id="pz-pain" class="pz-in pz-small-in" rows="1" placeholder="Qué problema o duda le resuelve este reel..." oninput="PZ.grow(this)"></textarea>',
'    <div class="pz-lbl">Guion</div>',
'    <textarea id="pz-script" class="pz-in pz-script-in" rows="4" placeholder="Cuerpo del guion..." oninput="PZ.grow(this)"></textarea>',
'    <div class="pz-board-box"><div class="pz-lbl">Pizarra / apoyo visual</div>',
'      <textarea id="pz-board" class="pz-board-in" rows="1" placeholder="Números, palabras o esquemas a escribir en cámara..." oninput="PZ.grow(this)"></textarea></div>',
'    <div class="pz-lbl">Conclusión</div>',
'    <textarea id="pz-concl" class="pz-in pz-small-in" rows="1" placeholder="El cierre / la postura..." oninput="PZ.grow(this)"></textarea>',
'    <div class="pz-lbl">CTA</div>',
'    <textarea id="pz-cta" class="pz-in pz-small-in" rows="1" placeholder="Llamado a la acción (opcional)..." oninput="PZ.grow(this)"></textarea>',
'    <div class="pz-lbl">Notas personales</div>',
'    <textarea id="pz-notes" class="pz-in pz-small-in" rows="1" placeholder="Recordatorios para grabar / editar..." oninput="PZ.grow(this)"></textarea>',
'    <div style="margin-top:22px;color:#B8A87F;font-size:11px" id="pz-pubinfo"></div>',
'  </div>',
'  <div class="pz-ficha-bar"><div class="inner">',
'    <button class="pz-btn pz-btn-primary" id="pz-save-btn" onclick="PZ.saveFicha()">Guardar</button>',
'    <span class="pz-save-msg" id="pz-save-msg"></span><span style="flex:1"></span>',
'    <button class="pz-btn pz-btn-danger" onclick="PZ.archivar()">Archivar</button>',
'  </div></div>',
'</div></div>',
'<div id="pz-import" class="modal-bg"><div class="modal" style="max-width:560px">',
'  <button class="modal-x" onclick="PZ.closeImport()">&times;</button>',
'  <div class="modal-h">Importar guion</div>',
'  <div class="modal-sub">Pegá el JSON que te dio ChatGPT (uno solo o una lista).</div>',
'  <textarea id="pz-imp-ta" class="pz-import-ta" placeholder=\'{ "title": "...", "hook": "...", "clientType": "inversor", "script": "...", "status": "guionado" }\'></textarea>',
'  <div class="pz-import-hint">Se acepta un objeto <code>{ }</code> o una lista <code>[ ]</code>. Podés dejar el bloque <code>```json</code> incluido. Solo hace falta <strong>título</strong> o <strong>guion</strong>; el resto se completa solo.</div>',
'  <div id="pz-imp-msg" class="pz-import-err"></div>',
'  <div class="modal-btns"><button class="pz-btn pz-btn-primary" id="pz-imp-btn" onclick="PZ.doImport()">Importar</button>',
'  <button class="pz-btn" onclick="PZ.closeImport()">Cancelar</button></div>',
'</div></div>'
    ].join('\n');
    while(d.firstChild)document.body.appendChild(d.firstChild);
    overlaysBuilt=true;
}

/* ---------- markup por vista ---------- */
function ensureViewMarkup(view){
    if(builtViews[view])return;
    var v=VIEWS[view], cont=el(v.cont);
    if(v.full){
        cont.innerHTML=[
'<div class="filterbar">',
'  <select id="pz-f-status"></select>',
'  <select id="pz-f-client"></select>',
'  <select id="pz-f-cat"></select>',
'  <select id="pz-f-perf"></select>',
'  <select id="pz-f-sort"></select>',
'  <input type="text" id="pz-q" placeholder="Buscar por título, hook, guion, dolor...">',
'  <button class="pz-btn pz-btn-primary" onclick="PZ.openImport()">+ Importar guion</button>',
'  <span class="pz-count" id="pz-count-guiones">0</span>',
'</div>',
'<div class="pz-wrap"><div id="'+v.grid+'" class="pz-grid"></div></div>'
        ].join('\n');
        buildFilters();
    }else if(v.archivo){
        cont.innerHTML=[
'<div class="pz-wrap">',
'  <div class="pz-section-head"><div><h2>Banco de guiones</h2><p>Tus 393 guiones ya escritos. Tocá el ✓ para elegir varios y pasalos a Guiones para filmar. Abrí cualquiera para leerlo.</p></div><span class="pz-count" id="pz-count-archivo">0</span></div>',
'  <div class="pz-archbar">',
'    <input type="text" id="pz-q-arch" placeholder="Buscar en el banco (título, hook, texto)...">',
'    <select id="pz-cat-arch"></select>',
'    <select id="pz-st-arch"></select>',
'  </div>',
'  <div id="'+v.grid+'" class="pz-grid" style="padding-bottom:70px"></div>',
'  <div id="pz-selbar" class="pz-selbar" style="display:none"><div class="inner"><span id="pz-selcount">0 seleccionados</span><span style="flex:1"></span><button class="pz-btn" onclick="PZ.limpiarSel()">Limpiar</button><button class="pz-btn pz-btn-primary" onclick="PZ.pasarSel()">Pasar a Guiones →</button></div></div>',
'</div>'
        ].join('\n');
    }else{
        cont.innerHTML=[
'<div class="pz-wrap">',
'  <div class="pz-section-head"><div><h2>'+v.title+'</h2><p>'+v.sub+'</p></div><span class="pz-count" id="pz-count-'+view+'">0</span></div>',
'  <div id="'+v.grid+'" class="pz-grid"></div>',
'</div>'
        ].join('\n');
    }
    builtViews[view]=true;
}

function buildFilters(){
    el('pz-f-status').innerHTML=opt('todos','Estado: todos')+STATUS.map(function(x){return opt(x,STATUS_LBL[x]);}).join('');
    el('pz-f-client').innerHTML=opt('todos','Cliente: todos')+CLIENT.map(function(x){return opt(x,CLIENT_LBL[x]);}).join('');
    el('pz-f-perf').innerHTML=opt('todos','Performance: todas')+PERF.map(function(x){return opt(x,PERF_LBL[x]);}).join('');
    el('pz-f-sort').innerHTML=opt('recientes','Orden: recientes')+opt('pipeline','Orden: producción')+opt('perf','Orden: performance')+opt('cat','Orden: categoría');
    ['pz-f-status','pz-f-client','pz-f-cat','pz-f-perf','pz-f-sort'].forEach(function(id){el(id).addEventListener('change',render);});
    el('pz-q').addEventListener('input',render);
}
function refreshCategoryFilter(){
    var sel=el('pz-f-cat');if(!sel)return;var prev=sel.value;
    var cats={};all.forEach(function(g){if(g.tema)cats[g.tema]=1;});
    sel.innerHTML=opt('todos','Categoría: todas')+Object.keys(cats).sort().map(function(c){return opt(c,c);}).join('');
    if(prev&&sel.querySelector('option[value="'+(window.CSS&&CSS.escape?CSS.escape(prev):prev)+'"]'))sel.value=prev;
}
function buildArchFilters(){
    var cats={},sts={};
    allArch.forEach(function(g){if(g.tema)cats[g.tema]=1;if(g.status)sts[g.status]=1;});
    var c=el('pz-cat-arch'),s=el('pz-st-arch'),q=el('pz-q-arch');
    var pc=c.value,ps=s.value;
    c.innerHTML=opt('todos','Categoría: todas')+Object.keys(cats).sort().map(function(x){return opt(x,x);}).join('');
    s.innerHTML=opt('todos','Estado: todos')+Object.keys(sts).sort().map(function(x){return opt(x,x.charAt(0).toUpperCase()+x.slice(1));}).join('');
    if(pc)c.value=pc; if(ps)s.value=ps;
    if(!c._b){c.addEventListener('change',render);s.addEventListener('change',render);q.addEventListener('input',render);c._b=true;}
}

/* ---------- carga ---------- */
function load(view){
    curView=(view&&VIEWS[view])?view:'guiones';
    ensureOverlays();
    ensureViewMarkup(curView);
    if(curView==='archivo'){
        archSel={};
        sb.from('guiones').select('*').is('flujo',null).order('id',{ascending:false}).range(0,4999).then(function(res){
            if(res.error){toast('Error al cargar banco: '+res.error.message,true);return;}
            allArch=res.data||[];
            buildArchFilters();
            render();
        });
        return;
    }
    sb.from('guiones').select('*').eq('flujo','pieza').order('created_at',{ascending:false}).range(0,999).then(function(res){
        if(res.error){toast('Error al cargar: '+res.error.message,true);return;}
        all=res.data||[];
        if(curView==='guiones')refreshCategoryFilter();
        render();
    });
}

/* ---------- render ---------- */
function render(){
    if(curView==='archivo'){renderArch();return;}
    var v=VIEWS[curView], g=el(v.grid);if(!g)return;
    var list=all.slice();
    if(v.base)list=list.filter(v.base);
    var count=el('pz-count-'+curView);

    if(v.full){
        var fst=el('pz-f-status').value, fcl=el('pz-f-client').value, fca=el('pz-f-cat').value, fpe=el('pz-f-perf').value, srt=el('pz-f-sort').value;
        var q=(el('pz-q').value||'').trim().toLowerCase();
        list=list.filter(function(x){
            var st=x.status||'idea', pf=x.performance||'sin_datos';
            if(fst!=='todos'&&st!==fst)return false;
            if(fcl!=='todos'&&(x.client_type||'')!==fcl)return false;
            if(fca!=='todos'&&(x.tema||'')!==fca)return false;
            if(fpe!=='todos'&&pf!==fpe)return false;
            if(q){var h=[x.titulo,x.hook,x.texto,x.pain_point,x.tema].filter(Boolean).join(' ').toLowerCase();if(h.indexOf(q)<0)return false;}
            return true;
        });
        if(srt==='pipeline')list.sort(function(a,b){return STATUS.indexOf(a.status||'idea')-STATUS.indexOf(b.status||'idea');});
        else if(srt==='perf')list.sort(function(a,b){return PERF.indexOf(b.performance||'sin_datos')-PERF.indexOf(a.performance||'sin_datos');});
        else if(srt==='cat')list.sort(function(a,b){return (a.tema||'').localeCompare(b.tema||'');});
    }
    if(count)count.textContent=list.length+(list.length===1?' pieza':' piezas');

    if(v.full&&!all.length){g.className='pz-empty';g.innerHTML='<h3>Todavía no cargaste ninguna pieza</h3><p>Desarrollá el guion en ChatGPT, copiá el JSON y traelo acá con <strong>Importar guion</strong>.</p><button class="pz-btn pz-btn-primary" onclick="PZ.openImport()">Importar guion</button>';return;}
    if(!list.length){g.className='pz-empty';g.innerHTML='<h3>Sin piezas acá</h3><p>'+(v.empty||'Ninguna pieza coincide con los filtros.')+'</p>';return;}
    g.className='pz-grid';
    g.innerHTML=list.map(function(x){return cardHtml(x,v.pick?'pick':null);}).join('');
}
function renderArch(){
    var g=el('pz-grid-archivo');if(!g)return;
    var q=(el('pz-q-arch').value||'').trim().toLowerCase();
    var fc=el('pz-cat-arch').value, fs=el('pz-st-arch').value;
    var list=allArch.filter(function(x){
        if(fc!=='todos'&&(x.tema||'')!==fc)return false;
        if(fs!=='todos'&&(x.status||'')!==fs)return false;
        if(q){var h=[x.id,x.titulo,x.hook,x.texto,x.tema].filter(Boolean).join(' ').toLowerCase();if(h.indexOf(q)<0)return false;}
        return true;
    });
    el('pz-count-archivo').textContent=list.length+(list.length===1?' guion':' guiones');
    if(!allArch.length){g.className='pz-empty';g.innerHTML='<h3>El banco está vacío</h3><p>No hay guiones viejos.</p>';updateSelBar();return;}
    if(!list.length){g.className='pz-empty';g.innerHTML='<h3>Sin resultados</h3><p>Ningún guion coincide con la búsqueda.</p>';updateSelBar();return;}
    g.className='pz-grid';g.style.paddingBottom='70px';
    g.innerHTML=list.map(function(x){return cardHtml(x,'recuperar');}).join('');
    updateSelBar();
}
/* selección múltiple del Banco */
function toggleSel(id,elem){
    if(archSel[id]){delete archSel[id];if(elem){elem.classList.remove('on');var c=elem.closest('.pz-card');if(c)c.classList.remove('pz-card-sel');}}
    else{archSel[id]=1;if(elem){elem.classList.add('on');var c2=elem.closest('.pz-card');if(c2)c2.classList.add('pz-card-sel');}}
    updateSelBar();
}
function updateSelBar(){
    var bar=el('pz-selbar');if(!bar)return;
    var n=Object.keys(archSel).length;
    bar.style.display=n?'flex':'none';
    var c=el('pz-selcount');if(c)c.textContent=n+(n===1?' guion elegido':' guiones elegidos');
}
function limpiarSel(){archSel={};if(curView==='archivo')render();updateSelBar();}
function pasarSel(){
    var ids=Object.keys(archSel);
    if(!ids.length)return;
    if(!confirm('Pasar '+ids.length+' guion'+(ids.length>1?'es':'')+' a Guiones para filmar?'))return;
    sb.from('guiones').update({flujo:'pieza',status:'guionado',updated_at:new Date().toISOString()}).in('id',ids).then(function(res){
        if(res.error){toast('Error: '+res.error.message,true);return;}
        allArch=allArch.filter(function(x){return !archSel[x.id];});
        var n=ids.length;archSel={};
        render();
        toast(n+' pasado'+(n>1?'s':'')+' a Guiones');
    });
}
function cardHtml(g,action){
    var st=g.status||'idea', pf=g.performance||'sin_datos';
    var stLbl=STATUS_LBL[st]||(st.charAt(0).toUpperCase()+st.slice(1));
    var arch=(action==='recuperar'), seled=arch&&!!archSel[g.id];
    var h='<div class="pz-card'+(seled?' pz-card-sel':'')+'" onclick="PZ.openFicha(\''+esc(g.id)+'\')">';
    h+='<div class="pz-card-top">';
    if(arch)h+='<span class="pz-check'+(seled?' on':'')+'" title="Elegir" onclick="event.stopPropagation();PZ.toggleSel(\''+esc(g.id)+'\',this)"></span>';
    h+='<span class="pz-card-id">'+esc(g.id)+'</span><span class="pzst pzst-'+st+'">'+esc(stLbl)+'</span></div>';
    h+='<div class="pz-card-title">'+esc(g.titulo||'(sin título)')+'</div>';
    if(g.hook)h+='<div class="pz-card-hook">'+esc(g.hook)+'</div>';
    var meta='';
    if(g.client_type&&CLIENT_LBL[g.client_type])meta+='<span class="pill ct-'+g.client_type+'">'+CLIENT_LBL[g.client_type]+'</span>';
    if(g.format&&FORMAT_LBL[g.format])meta+='<span class="chip fmt">'+FORMAT_LBL[g.format]+'</span>';
    if(g.target_duration)meta+='<span class="chip chip-dur">'+esc(g.target_duration)+'</span>';
    if(meta)h+='<div class="pz-card-meta">'+meta+'</div>';
    h+='<div class="pz-card-foot">'+(g.tema?'<span class="chip">'+esc(g.tema)+'</span>':'<span></span>');
    if(action==='pick')h+='<button class="pz-pick" onclick="event.stopPropagation();PZ.pick(\''+esc(g.id)+'\')">Para grabar →</button>';
    else if(arch)h+='<span class="pz-hint">✓ elegir · clic para leer</span>';
    else h+='<span class="pzperf pzperf-'+pf+'"><span class="dot"></span>'+PERF_LBL[pf]+'</span>';
    h+='</div></div>';
    return h;
}

/* ---------- ficha ---------- */
function selOpts(list,lbl,cur,allowEmpty,emptyLbl){
    var h=allowEmpty?'<option value="">'+(emptyLbl||'—')+'</option>':'';
    var found=list.indexOf(cur)>=0;
    if(cur&&!found&&!allowEmpty)h+='<option value="'+esc(cur)+'" selected>'+esc(cur)+'</option>';
    return h+list.map(function(x){return '<option value="'+x+'"'+((cur||'')===x?' selected':'')+'>'+lbl[x]+'</option>';}).join('');
}
function setV(id,v){el(id).value=(v==null?'':v);}
function openFicha(id){
    var g=findPiece(id);if(!g)return;
    curId=id;
    el('pz-fid').textContent=g.id;
    el('pz-fstatus').innerHTML=selOpts(STATUS,STATUS_LBL,g.status||'idea',false);
    el('pz-fperf').innerHTML=selOpts(PERF,PERF_LBL,g.performance||'sin_datos',false);
    setV('pz-title',g.titulo); setV('pz-hook',g.hook);
    el('pz-fclient').innerHTML=selOpts(CLIENT,CLIENT_LBL,g.client_type,true,'Cliente —');
    el('pz-format').innerHTML=selOpts(FORMAT,FORMAT_LBL,g.format,true,'Formato —');
    setV('pz-dur',g.target_duration); setV('pz-fcat',g.tema); setV('pz-pain',g.pain_point);
    setV('pz-script',g.texto); setV('pz-board',g.screen); setV('pz-concl',g.conclusion);
    setV('pz-cta',g.cta); setV('pz-notes',g.notas);
    el('pz-pubinfo').textContent=g.published_at?('Publicado el '+new Date(g.published_at).toLocaleDateString('es-AR')):'';
    el('pz-ficha').classList.add('open'); document.body.style.overflow='hidden';
    setTimeout(growAll,20);
    el('pz-save-msg').textContent='';
}
function closeFicha(){el('pz-ficha').classList.remove('open');document.body.style.overflow='';curId=null;}
function grow(t){t.style.height='auto';t.style.height=(t.scrollHeight+2)+'px';}
function growAll(){['pz-title','pz-hook','pz-pain','pz-script','pz-board','pz-concl','pz-cta','pz-notes'].forEach(function(id){grow(el(id));});}
function collect(){
    return {
        titulo:el('pz-title').value.trim(), hook:el('pz-hook').value.trim(),
        client_type:el('pz-fclient').value||null, format:el('pz-format').value||null,
        target_duration:el('pz-dur').value.trim(), tema:el('pz-fcat').value.trim(),
        pain_point:el('pz-pain').value.trim(), texto:el('pz-script').value,
        screen:el('pz-board').value, conclusion:el('pz-concl').value.trim(),
        cta:el('pz-cta').value.trim(), notas:el('pz-notes').value,
        status:el('pz-fstatus').value, performance:el('pz-fperf').value,
        updated_at:new Date().toISOString()
    };
}
function patch(id,u,okMsg){
    return sb.from('guiones').update(u).eq('id',id).then(function(res){
        if(res.error){toast('Error: '+res.error.message,true);return false;}
        var g=findPiece(id);if(g)for(var k in u)g[k]=u[k];
        render();
        if(okMsg)toast(okMsg);
        return true;
    });
}
function saveFicha(){
    if(!curId)return;
    var id=curId,m=el('pz-save-msg'),btn=el('pz-save-btn');
    btn.disabled=true;btn.textContent='Guardando...';m.className='pz-save-msg';m.textContent='';
    patch(id,collect()).then(function(ok){
        btn.disabled=false;btn.textContent='Guardar';
        m.className='pz-save-msg'+(ok?'':' err');m.textContent=ok?'Guardado ✓':'Error';
        setTimeout(function(){m.textContent='';},2500);
    });
}
function quickStatus(){if(curId)patch(curId,{status:el('pz-fstatus').value,updated_at:new Date().toISOString()},'Estado actualizado');}
function quickPerf(){if(curId)patch(curId,{performance:el('pz-fperf').value,updated_at:new Date().toISOString()},'Performance actualizada');}
function marcarPublicado(){
    if(!curId)return;
    var g=findPiece(curId);
    var u={status:'publicado',updated_at:new Date().toISOString()};
    if(g&&!g.published_at)u.published_at=new Date().toISOString();
    el('pz-fstatus').value='publicado';
    patch(curId,u,'Marcada como publicada').then(function(){
        if(g&&g.published_at)el('pz-pubinfo').textContent='Publicado el '+new Date(g.published_at).toLocaleDateString('es-AR');
    });
}
function archivar(){
    if(!curId||!confirm('Archivar esta pieza? Sale de la lista (no se borra).'))return;
    var id=curId;
    patch(id,{flujo:'archivada'},'Archivada').then(function(){
        all=all.filter(function(x){return x.id!==id;});closeFicha();render();
    });
}
/* Selector: marcar una pieza para grabar */
function pick(id){patch(id,{status:'para_grabar',updated_at:new Date().toISOString()},'Marcada para grabar');}
/* Archivo: recuperar un guion viejo al flujo nuevo */
function recuperar(id){
    if(!confirm('Recuperar este guion al flujo nuevo? Va a aparecer en Guiones como "guionado".'))return;
    sb.from('guiones').update({flujo:'pieza',status:'guionado',updated_at:new Date().toISOString()}).eq('id',id).then(function(res){
        if(res.error){toast('Error: '+res.error.message,true);return;}
        allArch=allArch.filter(function(x){return x.id!==id;});
        render();
        toast('Recuperado a Guiones');
    });
}

/* ---------- importar JSON ---------- */
function openImport(){el('pz-imp-ta').value='';el('pz-imp-msg').textContent='';el('pz-import').classList.add('open');document.body.style.overflow='hidden';setTimeout(function(){el('pz-imp-ta').focus();},50);}
function closeImport(){el('pz-import').classList.remove('open');document.body.style.overflow='';}
function cleanEnum(v,list){v=(v||'').toString().trim().toLowerCase();return list.indexOf(v)>=0?v:null;}
function mapPiece(o){
    return {
        titulo:(o.title||o.titulo||'').toString().trim(),
        hook:(o.hook||'').toString().trim(),
        client_type:cleanEnum(o.clientType||o.client_type,CLIENT),
        pain_point:(o.painPoint||o.pain_point||'').toString().trim(),
        tema:(o.category||o.tema||'').toString().trim(),
        format:cleanEnum(o.format,FORMAT),
        target_duration:(o.targetDuration||o.target_duration||'').toString().trim(),
        texto:(o.script||o.texto||'').toString(),
        screen:(o.boardNotes||o.board_notes||o.screen||'').toString(),
        conclusion:(o.conclusion||'').toString().trim(),
        cta:(o.cta||'').toString().trim(),
        notas:(o.notes||o.notas||'').toString(),
        status:cleanEnum(o.status,STATUS)||'guionado',
        performance:cleanEnum(o.performance,PERF)||'sin_datos',
        tipo:'organico', angulo:'con', flujo:'pieza'
    };
}
function doImport(){
    var raw=el('pz-imp-ta').value.trim(), msg=el('pz-imp-msg');
    msg.className='pz-import-err';
    if(!raw){msg.textContent='Pegá el JSON del guion.';return;}
    raw=raw.replace(/^```(json)?/i,'').replace(/```$/,'').trim();
    var data;try{data=JSON.parse(raw);}catch(e){msg.textContent='JSON inválido: '+e.message;return;}
    var items=Array.isArray(data)?data:[data];
    if(!items.length){msg.textContent='No hay piezas para importar.';return;}
    var mapped=[],skipped=0,stamp=Date.now();
    items.forEach(function(o,i){
        if(typeof o!=='object'||o===null){skipped++;return;}
        var rec=mapPiece(o);
        if(!rec.titulo&&!rec.texto){skipped++;return;}
        if(!rec.titulo)rec.titulo='(sin título)';
        rec.id='PZ-'+(stamp+i).toString(36).toUpperCase();
        mapped.push(rec);
    });
    if(!mapped.length){msg.textContent='Ninguna pieza válida (falta título y guion).';return;}
    var btn=el('pz-imp-btn');btn.disabled=true;btn.textContent='Importando...';
    sb.from('guiones').insert(mapped).then(function(res){
        btn.disabled=false;btn.textContent='Importar';
        if(res.error){msg.className='pz-import-err';msg.textContent='Error al guardar: '+res.error.message;return;}
        var extra=skipped?(' · '+skipped+' omitida'+(skipped>1?'s':'')):'';
        closeImport();
        toast(mapped.length+' pieza'+(mapped.length>1?'s':'')+' importada'+(mapped.length>1?'s':'')+extra);
        load('guiones');
    }).catch(function(e){btn.disabled=false;btn.textContent='Importar';msg.textContent='Error: '+(e.message||e);});
}

document.addEventListener('keydown',function(e){
    if(e.key!=='Escape'||!overlaysBuilt)return;
    if(el('pz-import').classList.contains('open'))closeImport();
    else if(el('pz-ficha').classList.contains('open'))closeFicha();
});

window.PZ={load:load,render:render,openFicha:openFicha,closeFicha:closeFicha,saveFicha:saveFicha,
    quickStatus:quickStatus,quickPerf:quickPerf,marcarPublicado:marcarPublicado,archivar:archivar,pick:pick,recuperar:recuperar,
    toggleSel:toggleSel,pasarSel:pasarSel,limpiarSel:limpiarSel,
    openImport:openImport,closeImport:closeImport,doImport:doImport,grow:grow};
})();
