var SB_URL='https://pgnmpxqljxrpnvexcygh.supabase.co';
var SB_KEY='sb_publishable_HmiBL9VpEhaYyPqjA1v67w_F38x48El';
var ANG={prob:'Problema',prod:'Producto',sol:'Solucion',con:'Otro',aut:'Autoridad',pred:'Prediccion',comp:'Comparacion',hist:'Historia'};
var ANG_C={prob:['#FDE8E8','#C8453A'],prod:['#E8F5EE','#2D8C5A'],sol:['#E8F0FD','#4A90D9'],con:['#FDF3E8','#D48A2C'],aut:['#F5E8FD','#7B4A9E'],pred:['#E8FDF8','#1F8F7A'],comp:['#FDF8E8','#A8862C'],hist:['#FDE8F0','#B4455F']};
var TEMAS={'Inversion':'Inversión / Números','Credito':'Crédito / Financiamiento','Costos':'Costos / Construcción','Fideicomiso':'Fideicomiso / Pozo','Tandil':'Tandil como Negocio','Alquileres':'Alquileres / Acceso','Mercado':'Mercado Argentina','PrimerDepto':'Primer Departamento','Mudarse':'Mudarse al Interior','Infra':'Infraestructura','Escena':'Detrás de Escena','Polemicos':'Polémicos / Opinión','Meta':'Meta Ads','Captacion':'Captación','marca_personal':'Marca Personal','Historia Personal':'Historia Personal','Finanzas':'Finanzas Personales','Comparacion':'Comparaciones'};
// Normaliza variantes de tema a la clave canónica
var TEMA_NORM={'Inversión':'Inversion','inversión':'Inversion','inversion':'Inversion','Crédito':'Credito','crédito':'Credito','credito hipotecario':'Credito','Crédito hipotecario':'Credito','Crédito hipotecario':'Credito','costo de construccion':'Costos','Costos':'Costos','Inflación y Alquileres':'Alquileres','Inflación y economía':'Mercado','Comparación':'Comparacion','Comparación':'Comparacion'};
function normTema(t){return TEMA_NORM[t]||t;}

var sb=window.supabase.createClient(SB_URL,SB_KEY);
var allG=[],curId=null,curRat=0,allVotos=[],curUserEmail='';
var guionesOffset=0,guionesHasMore=false;
var BADGE_MAP={'santiagomfunes@gmail.com':'S','celina.colombo15@gmail.com':'C','huergomarcos@gmail.com':'M'};
var BADGE_COLOR={'S':'#8B6F3A','C':'#2D6A9F','M':'#2D8C5A'};

// Build selects
var k;
var fAngSel=document.getElementById('f-ang');
var fCatSel=document.getElementById('f-cat');
var mAngSel=document.getElementById('m-ang');
var iAngSel=document.getElementById('i-ang');
iAngSel.innerHTML='<option value="">--</option>';
for(k in ANG){
    fAngSel.innerHTML+='<option value="'+k+'">'+ANG[k]+'</option>';
    mAngSel.innerHTML+='<option value="'+k+'">'+ANG[k]+'</option>';
    iAngSel.innerHTML+='<option value="'+k+'">'+ANG[k]+'</option>';
}
for(k in TEMAS) fCatSel.innerHTML+='<option value="'+k+'">'+TEMAS[k]+'</option>';

// Search
var sTO;
document.getElementById('q').addEventListener('input',function(e){
    clearTimeout(sTO);sTO=setTimeout(function(){doFilter();},200);
});

function clearFilters(){
    document.getElementById('f-tipo').value='organico';
    document.getElementById('f-ang').value='todos';
    document.getElementById('f-cat').value='todos';
    document.getElementById('f-status').value='todos';
    document.getElementById('q').value='';
    doFilter();
}

// Login
document.getElementById('login-form').addEventListener('submit',function(e){
    e.preventDefault();
    var email=document.getElementById('in-email').value.trim();
    var pass=document.getElementById('in-pass').value;
    var btn=document.getElementById('login-btn');
    var err=document.getElementById('login-err');
    btn.disabled=true;btn.textContent='Ingresando...';err.textContent='';
    sb.auth.signInWithPassword({email:email,password:pass}).then(function(res){
        if(res.error)throw res.error;
        enterApp();
    }).catch(function(ex){
        err.textContent=ex.message==='Invalid login credentials'?'Email o contrasena incorrectos.':(ex.message||'Error');
    }).finally(function(){btn.disabled=false;btn.textContent='Ingresar';});
});

function doSignOut(){
    sb.auth.signOut().then(function(){
        document.getElementById('app').style.display='none';
        document.getElementById('login').style.display='flex';
        allG=[];
    });
}

function enterApp(){
    document.getElementById('login').style.display='none';
    document.getElementById('app').style.display='block';
    sb.auth.getUser().then(function(res){curUserEmail=(res.data&&res.data.user)?res.data.user.email:'';});
    loadAll();
    if(window.PZ)PZ.load('guiones');
    try{sb.channel('g').on('postgres_changes',{event:'*',schema:'public',table:'guiones'},function(){loadAll();}).subscribe();}catch(e){}
    try{sb.channel('v').on('postgres_changes',{event:'*',schema:'public',table:'votos_filmar'},function(){loadVotos(function(){doFilter();if(document.getElementById('v-parafilmar').classList.contains('on'))loadParaFilmar();});}).subscribe();}catch(e){}
}

function loadAll(){
    guionesOffset=0;
    sb.from('guiones').select('*').order('id',{ascending:false}).range(0,49).then(function(res){
        if(res.error){toast('Error: '+res.error.message,true);return;}
        allG=res.data||[];
        guionesHasMore=(allG.length===50);
        var lmw=document.getElementById('load-more-wrap');
        if(lmw)lmw.style.display=guionesHasMore?'block':'none';
        loadVotos(function(){doFilter();});
    });
}
function loadMore(){
    var btn=document.getElementById('load-more-btn');
    if(btn){btn.textContent='Cargando...';btn.disabled=true;}
    guionesOffset+=50;
    sb.from('guiones').select('*').order('id',{ascending:false}).range(guionesOffset,guionesOffset+49).then(function(res){
        if(btn){btn.textContent='Cargar mas guiones';btn.disabled=false;}
        var more=res.data||[];
        allG=allG.concat(more);
        guionesHasMore=(more.length===50);
        var lmw=document.getElementById('load-more-wrap');
        if(lmw)lmw.style.display=guionesHasMore?'block':'none';
        loadVotos(function(){doFilter();});
    });
}
function loadVotos(cb){
    sb.from('votos_filmar').select('*').then(function(res){
        allVotos=res.data||[];
        if(cb)cb();
    });
}
function getVotosPorGuion(guionId){
    return allVotos.filter(function(v){return v.guion_id===guionId;});
}
function yoVote(guionId){
    return allVotos.some(function(v){return v.guion_id===guionId&&v.user_email===curUserEmail;});
}

function isFilmado(g){var st=g.status||'listo';return st==='filmado'||st==='publicado';}
function tieneVotos(g){return allVotos.some(function(v){return v.guion_id===g.id;});}

function renderVista(vista){
    var qEl=document.getElementById(vista==='filmados'?'q-fil':'q-ree');
    var fQ=qEl?(qEl.value||'').trim().toLowerCase():'';
    var cntEl=document.getElementById(vista==='filmados'?'cnt-fil':'cnt-ree');
    var contentEl=document.getElementById('content-'+vista);
    var r=allG.filter(function(g){
        if(vista==='filmados'&&!isFilmado(g))return false;
        if(vista==='reestructurar'&&(isFilmado(g)||tieneVotos(g)))return false;
        if(fQ){var h=[g.id,g.titulo,g.hook,g.texto,g.tema].filter(Boolean).join(' ').toLowerCase();if(h.indexOf(fQ)<0)return false;}
        return true;
    });
    if(cntEl)cntEl.textContent=r.length+' guiones';
    if(contentEl)renderGroupedInto(r,contentEl);
}

function doFilter(){
    var fTipo=document.getElementById('f-tipo').value;
    var fAng=document.getElementById('f-ang').value;
    var fCat=document.getElementById('f-cat').value;
    var fQ=(document.getElementById('q').value||'').trim().toLowerCase();
    var fStatus=(document.getElementById('f-status')||{}).value||'todos';

    var r=allG.filter(function(g){
        if(isFilmado(g))return false;
        if(!tieneVotos(g))return false;
        var st=g.status||'listo';
        var tp=(g.tipo||'organico').toLowerCase();
        if(fTipo!=='todos'&&((fTipo==='organico'&&tp!=='organico')||(fTipo==='ads'&&tp!=='ads')))return false;
        if(fAng!=='todos'&&(g.angulo||'')!==fAng)return false;
        if(fCat!=='todos'&&(g.tema||'')!==fCat)return false;
        if(fStatus!=='todos'&&st!==fStatus)return false;
        if(fQ){var h=[g.id,g.titulo,g.hook,g.texto,g.tema,g.semana].filter(Boolean).join(' ').toLowerCase();if(h.indexOf(fQ)<0)return false;}
        return true;
    });

    // Stats from filtered
    var tot=allG.filter(function(g){var tp=(g.tipo||'organico').toLowerCase();if(fTipo!=='todos'&&((fTipo==='organico'&&tp!=='organico')||(fTipo==='ads'&&tp!=='ads')))return false;return true;}).length;
    var fil=0,pub=0;
    allG.forEach(function(g){if(g.status==='filmado')fil++;if(g.status==='publicado')pub++;});
    document.getElementById('s-tot').textContent=tot;
    document.getElementById('s-fil').textContent=fil;
    document.getElementById('s-pub').textContent=pub;
    document.getElementById('cnt').textContent=r.length+' de '+tot;

    renderGrouped(r);
}

function esc(s){var d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}

function renderGroupedInto(gs,el){
    if(!gs.length){el.innerHTML='<div style="text-align:center;padding:60px;color:#ccc;font-size:14px">No se encontraron guiones.</div>';return;}
    var groups={};
    gs.forEach(function(g){var t=normTema(g.tema||'Sin categoria');if(!groups[t])groups[t]=[];groups[t].push(g);});
    var html='';
    for(var tema in groups){
        var items=groups[tema];
        html+='<div class="section"><div class="section-head"><span>'+(TEMAS[tema]||tema)+'</span><span class="section-count">'+items.length+' guiones</span></div><div class="grid">';
        items.forEach(function(g){
            var a=(g.angulo||'').toLowerCase();var c=ANG_C[a]||['#F0EFED','#999'];var st=g.status||'listo';var hk=g.hook||'';
            html+='<div class="card" onclick="openModal(\''+esc(g.id)+'\')">';
            html+='<div class="card-head"><span class="card-id">'+esc(g.id)+'</span><span class="badge" style="background:'+c[0]+';color:'+c[1]+'">'+esc(ANG[a]||a)+'</span></div>';
            html+='<div class="card-title">'+esc(g.titulo)+'</div><div class="card-hook">'+esc(hk)+'</div>';
            var gVotos=getVotosPorGuion(g.id);
            html+='<div class="card-foot"><span class="st st-'+st+'">'+(st.charAt(0).toUpperCase()+st.slice(1))+'</span>';
            if(g.semana)html+='<span class="card-sem">'+esc(g.semana)+'</span>';
            if(gVotos.length){html+='<span style="margin-left:auto;display:flex;gap:3px">'+gVotos.map(function(v){var b=BADGE_MAP[v.user_email]||'?';var col=BADGE_COLOR[b]||'#999';return '<span style="background:'+col+';color:#fff;border-radius:50%;width:16px;height:16px;font-size:9px;font-weight:700;display:flex;align-items:center;justify-content:center">'+b+'</span>';}).join('')+'</span>';}
            html+='</div></div>';
        });
        html+='</div></div>';
    }
    el.innerHTML=html;
}

function renderGrouped(gs){
    var el=document.getElementById('content');
    if(!gs.length){el.innerHTML='<div style="text-align:center;padding:60px;color:#ccc;font-size:14px">No se encontraron guiones.</div>';return;}

    // Group by tema (normalizado)
    var groups={};
    gs.forEach(function(g){
        var t=normTema(g.tema||'Sin categoria');
        if(!groups[t])groups[t]=[];
        groups[t].push(g);
    });

    var html='';
    for(var tema in groups){
        var items=groups[tema];
        html+='<div class="section">';
        html+='<div class="section-head"><span>'+(TEMAS[tema]||tema)+'</span><span class="section-count">'+items.length+' guiones</span></div>';
        html+='<div class="grid">';
        items.forEach(function(g){
            var a=(g.angulo||'').toLowerCase();
            var c=ANG_C[a]||['#F0EFED','#999'];
            var st=g.status||'listo';
            var hk=g.hook||'';
            html+='<div class="card" onclick="openModal(\''+esc(g.id)+'\')">';
            html+='<div class="card-head"><span class="card-id">'+esc(g.id)+'</span>';
            html+='<span class="badge" style="background:'+c[0]+';color:'+c[1]+'">'+esc(ANG[a]||a)+'</span></div>';
            html+='<div class="card-title">'+esc(g.titulo)+'</div>';
            html+='<div class="card-hook">'+esc(hk)+'</div>';
            var gVotos=getVotosPorGuion(g.id);
            html+='<div class="card-foot">';
            html+='<span class="st st-'+st+'">'+(st.charAt(0).toUpperCase()+st.slice(1))+'</span>';
            if(g.semana)html+='<span class="card-sem">'+esc(g.semana)+'</span>';
            if(gVotos.length){html+='<span style="margin-left:auto;display:flex;gap:3px">'+gVotos.map(function(v){var b=BADGE_MAP[v.user_email]||'?';var col=BADGE_COLOR[b]||'#999';return '<span style="background:'+col+';color:#fff;border-radius:50%;width:16px;height:16px;font-size:9px;font-weight:700;display:flex;align-items:center;justify-content:center">'+b+'</span>';}).join('')+'</span>';}
            html+='</div></div>';
        });
        html+='</div></div>';
    }
    el.innerHTML=html;
}

// Spaces
var currentSpace='contenido';
var lastTabPerSpace={contenido:'guiones',inmobiliario:'fichas'};

function switchSpace(space,btn){
    currentSpace=space;
    document.querySelectorAll('.space-btn').forEach(function(b){b.classList.remove('on');});
    if(btn)btn.classList.add('on');
    document.querySelectorAll('[data-space]').forEach(function(el){
        el.style.display=el.dataset.space===space?'':'none';
    });
    var last=lastTabPerSpace[space]||(space==='contenido'?'guiones':'fichas');
    var tabBtn=document.querySelector('.tab[data-space="'+space+'"][onclick*="\''+last+'\'"]');
    switchTab(last,tabBtn);
}

// Tabs
function switchTab(name,btn){
    document.querySelectorAll('.view').forEach(function(v){v.classList.remove('on');});
    document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('on');});
    document.getElementById('v-'+name).classList.add('on');
    if(btn)btn.classList.add('on');
    if(currentSpace&&lastTabPerSpace)lastTabPerSpace[currentSpace]=name;
    if(name==='piezas'&&window.PZ)PZ.load('guiones');
    if(name==='archivo'&&window.PZ)PZ.load('archivo');
    if(name==='selector'&&window.PZ)PZ.load('selector');
    if(name==='parafilmar'&&window.PZ)PZ.load('parafilmar');
    if(name==='briefing')loadBriefing();
    if(name==='reportes')loadReportes();
    if(name==='calendario')loadCalendario();
    if(name==='fichas')fichasUpdatePreview();
    if(name==='ideas'){loadIdeas2();buildIdeasSelects();}
    if(name==='filmados'&&window.PZ)PZ.load('filmados');
    if(name==='reestructurar')renderVista('reestructurar');
    closeMore();
}

function switchTabMenu(name){
    switchTab(name,null);
    document.querySelector('.tab-more').classList.add('on');
}

function toggleMore(btn){
    var menu=document.getElementById('tab-more-menu');
    menu.classList.toggle('open');
}

function closeMore(){
    var menu=document.getElementById('tab-more-menu');
    if(menu)menu.classList.remove('open');
}

document.addEventListener('click',function(e){
    if(!e.target.closest('.tab-more-wrap'))closeMore();
});

// Ideas v2 (tab view)
var ideasSelBuilt=false;
function buildIdeasSelects(){
    if(ideasSelBuilt)return;ideasSelBuilt=true;
    var iA=document.getElementById('i-ang2');
    iA.innerHTML='<option value="">--</option>';
    for(var k in ANG)iA.innerHTML+='<option value="'+k+'">'+ANG[k]+'</option>';
    // Build guion reference select
    var gSel=document.getElementById('i-guion-ref');
    gSel.innerHTML='<option value="">-- Elegir guion --</option>';
    allG.forEach(function(g){
        gSel.innerHTML+='<option value="'+esc(g.id)+'">'+esc(g.id)+' — '+esc((g.titulo||'').substring(0,50))+'</option>';
    });
}

function toggleIdeaTipo(){
    var tipo=document.getElementById('i-tipo2').value;
    document.getElementById('i-guion-ref-wrap').style.display=tipo==='mejora'?'block':'none';
}

function checkIdeaDuplicado(){
    var tema=document.getElementById('i-tema2').value.trim().toLowerCase();
    var warn=document.getElementById('i-dup-warn');
    if(tema.length<5){warn.style.display='none';return;}
    var words=tema.split(/\s+/).filter(function(w){return w.length>3;});
    var matches=allG.filter(function(g){
        var t=(g.titulo||'').toLowerCase();
        var matchCount=0;
        words.forEach(function(w){if(t.indexOf(w)>=0)matchCount++;});
        return matchCount>=2||(tema.length>10&&t.indexOf(tema.substring(0,10))>=0);
    });
    if(matches.length>0){
        warn.style.display='block';
        warn.innerHTML='<strong>Ojo:</strong> ya existen guiones parecidos: '+matches.map(function(g){
            return '<strong>'+esc(g.id)+'</strong> "'+esc(g.titulo)+'"';
        }).join(', ')+'. Si queres mejorar uno existente, cambia el tipo a "Mejora de guion existente".';
    } else {
        warn.style.display='none';
    }
}

function loadIdeas2(){
    sb.from('ideas').select('*').order('created_at',{ascending:false}).then(function(res){
        var el=document.getElementById('ideas-list2'),ideas=res.data||[];
        if(!ideas.length){el.innerHTML='<p style="color:#ccc;font-size:12px;text-align:center;padding:20px">No hay propuestas todavia.</p>';return;}
        el.innerHTML=ideas.map(function(i){
            var a=ANG[(i.angulo||'').toLowerCase()]||'';
            var tipo=i.tipo||'idea';
            var tipoLabel=tipo==='mejora'?'MEJORA':'IDEA NUEVA';
            var tipoColor=tipo==='mejora'?'#D48A2C':'#4A90D9';
            var estadoLabel=(i.estado||'propuesta').toUpperCase();
            var estadoColor=i.estado==='aprobada'?'#2D8C5A':i.estado==='rechazada'?'#C8453A':'#999';
            var fecha=i.created_at?new Date(i.created_at).toLocaleDateString('es-AR',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}):'';

            // If it's a mejora, show the original guion for comparison
            var diffHtml='';
            if(tipo==='mejora'&&i.guion_ref){
                var orig=allG.find(function(g){return g.id===i.guion_ref;});
                if(orig){
                    diffHtml='<div style="background:#F5F5F3;border:1px solid #E8E4DD;border-radius:6px;padding:10px;margin:8px 0;font-size:10px">'+
                        '<div style="font-weight:700;color:#8B6F3A;margin-bottom:4px">GUION ORIGINAL: '+esc(orig.id)+' — '+esc(orig.titulo)+'</div>'+
                        '<div style="color:#888;font-style:italic;margin-bottom:6px">Hook: "'+esc((orig.hook||'').substring(0,120))+'..."</div>'+
                        '<div style="border-top:1px dashed #E8E4DD;padding-top:6px;margin-top:6px;font-weight:700;color:#D48A2C">CAMBIOS PROPUESTOS POR '+esc(i.autor||'').toUpperCase()+':</div>'+
                    '</div>';
                }
            }

            // Auto-detect if detalle matches an existing guion (for old ideas without tipo)
            var autoMatchHtml='';
            if(tipo==='idea'&&!i.guion_ref){
                var temaLow=(i.tema||'').toLowerCase();
                var words=temaLow.split(/\s+/).filter(function(w){return w.length>3;});
                var autoMatch=allG.filter(function(g){
                    var t=(g.titulo||'').toLowerCase();
                    var mc=0;words.forEach(function(w){if(t.indexOf(w)>=0)mc++;});
                    return mc>=2;
                });
                if(autoMatch.length>0){
                    autoMatchHtml='<div style="background:#FDE8E8;border:1px solid #C8453A44;border-radius:6px;padding:8px 10px;margin:6px 0;font-size:10px;color:#C8453A">'+
                        '<strong>POSIBLE DUPLICADO</strong> — Ya existe: '+autoMatch.map(function(g){
                            return '<strong>'+esc(g.id)+'</strong> "'+esc(g.titulo)+'"';
                        }).join(', ')+
                    '</div>';
                }
            }

            // Approval buttons (only for propuesta status)
            var btnHtml='';
            if(i.estado==='propuesta'){
                btnHtml='<div style="display:flex;gap:6px;margin-top:8px">'+
                    '<button onclick="approveIdea(\''+i.id+'\',\'aprobada\')" style="padding:5px 12px;border-radius:6px;font-size:9px;font-weight:700;background:#E8F5EE;color:#2D8C5A;border:1px solid #2D8C5A44;cursor:pointer">Aprobar</button>'+
                    '<button onclick="approveIdea(\''+i.id+'\',\'rechazada\')" style="padding:5px 12px;border-radius:6px;font-size:9px;font-weight:700;background:#FDE8E8;color:#C8453A;border:1px solid #C8453A44;cursor:pointer">Rechazar</button>'+
                    (tipo!=='mejora'&&!i.guion_ref?'<button onclick="convertIdeaToGuion(\''+i.id+'\')" style="padding:5px 12px;border-radius:6px;font-size:9px;font-weight:700;background:#E8F0FD;color:#4A90D9;border:1px solid #4A90D944;cursor:pointer">Convertir en Guion</button>':'')+
                '</div>';
            }

            return '<div class="idea-card" style="border-left:3px solid '+tipoColor+'">'+
                '<div class="idea-card-head">'+
                    '<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">'+
                        '<span style="font-size:8px;font-weight:700;letter-spacing:1px;padding:2px 6px;border-radius:4px;background:'+tipoColor+'22;color:'+tipoColor+'">'+tipoLabel+'</span>'+
                        '<span class="idea-card-tema">'+esc(i.tema)+'</span>'+
                        (i.guion_ref?'<span style="font-size:9px;color:#8B6F3A;font-weight:600">ref: '+esc(i.guion_ref)+'</span>':'')+
                    '</div>'+
                    '<div style="display:flex;align-items:center;gap:8px">'+
                        '<span style="font-size:8px;font-weight:700;letter-spacing:1px;padding:2px 6px;border-radius:4px;color:'+estadoColor+';border:1px solid '+estadoColor+'44">'+estadoLabel+'</span>'+
                        '<span style="font-size:10px;color:#999">'+esc(i.autor||'')+' · '+fecha+(a?' · '+a:'')+'</span>'+
                    '</div>'+
                '</div>'+
                autoMatchHtml+
                diffHtml+
                (i.detalle?'<div class="idea-card-det" style="white-space:pre-wrap;max-height:200px;overflow-y:auto">'+esc(i.detalle)+'</div>':'')+
                btnHtml+
            '</div>';
        }).join('');
    });
}

function approveIdea(ideaId,estado){
    sb.from('ideas').update({estado:estado}).eq('id',ideaId).then(function(res){
        if(res.error){toast('Error',true);return;}
        toast('Propuesta '+estado);
        loadIdeas2();
    });
}

function convertIdeaToGuion(ideaId){
    sb.from('ideas').select('*').eq('id',ideaId).single().then(function(res){
        if(res.error||!res.data){toast('Error',true);return;}
        var idea=res.data;
        var newId='IDEA-'+Date.now().toString(36).toUpperCase().substring(0,4);
        sb.from('guiones').insert({
            id:newId,
            titulo:idea.tema||'Sin titulo',
            angulo:idea.angulo||'prob',
            tema:'Ideas',
            hook:idea.detalle?(idea.detalle.split('\n')[0]||''):'',
            texto:idea.detalle||'',
            tipo:'organico',
            status:'listo',
            screen:'',caption_ig:'',caption_tk:'',fuentes:'',notas:'Convertido desde idea de '+idea.autor
        }).then(function(r){
            if(r.error){toast('Error: '+r.error.message,true);return;}
            sb.from('ideas').update({estado:'aprobada'}).eq('id',ideaId);
            toast('Guion '+newId+' creado desde idea');
            loadGuiones();loadIdeas2();
        });
    });
}

function doSaveIdea2(){
    var tema=document.getElementById('i-tema2').value.trim(),msg=document.getElementById('i-msg2');
    if(!tema){msg.style.color='#C8453A';msg.textContent='Completa el tema.';return;}
    var tipo=document.getElementById('i-tipo2').value;
    var guionRef=tipo==='mejora'?document.getElementById('i-guion-ref').value:'';
    if(tipo==='mejora'&&!guionRef){msg.style.color='#C8453A';msg.textContent='Selecciona el guion que queres mejorar.';return;}
    var detalle=document.getElementById('i-det2').value.trim();
    if(!detalle){msg.style.color='#C8453A';msg.textContent='Explica tu propuesta en el detalle.';return;}
    msg.textContent='';
    sb.from('ideas').insert({
        autor:document.getElementById('i-aut2').value.trim()||'Anonimo',
        angulo:document.getElementById('i-ang2').value,
        tema:tema,
        detalle:detalle,
        estado:'propuesta',
        tipo:tipo,
        guion_ref:guionRef
    }).then(function(res){
        if(res.error){msg.style.color='#C8453A';msg.textContent='Error: '+res.error.message;return;}
        document.getElementById('i-tema2').value='';document.getElementById('i-det2').value='';
        document.getElementById('i-tipo2').value='idea';toggleIdeaTipo();
        msg.style.color='#2D8C5A';msg.textContent='Propuesta enviada! Santiago la va a revisar.';toast('Propuesta enviada');
        setTimeout(function(){msg.textContent='';},3000);loadIdeas2();
    });
}

// Modal — read/edit toggle
var editMode=false;
function toggleEdit(){
    editMode=!editMode;
    document.getElementById('read-view').style.display=editMode?'none':'block';
    document.getElementById('edit-fields').style.display=editMode?'block':'none';
    document.getElementById('m-edit-btn').textContent=editMode?'Leer':'Editar';
    document.getElementById('m-edit-btn').className=editMode?'read-toggle':'edit-toggle';
}

function openModal(id){
    var g=allG.find(function(x){return x.id===id;});if(!g)return;
    curId=id;
    // Reset to read mode
    editMode=false;
    document.getElementById('read-view').style.display='block';
    document.getElementById('edit-fields').style.display='none';
    document.getElementById('m-edit-btn').textContent='Editar';
    document.getElementById('m-edit-btn').className='edit-toggle';

    document.getElementById('m-id').textContent=g.id;
    var a=(g.angulo||'').toLowerCase(),c=ANG_C[a]||['#F0EFED','#999'];
    var badge=document.getElementById('m-badge');badge.textContent=ANG[a]||a;badge.style.background=c[0];badge.style.color=c[1];

    // Read view
    document.getElementById('r-tit').textContent=g.titulo||'';
    document.getElementById('r-hook').textContent=g.hook||'';
    document.getElementById('r-txt').textContent=g.texto||'';
    document.getElementById('r-scr').textContent=g.screen||'';
    document.getElementById('r-cap').textContent='IG: '+(g.caption_ig||'—')+'\n\nTK: '+(g.caption_tk||'—');
    document.getElementById('r-fue').textContent=g.fuentes||'';
    document.getElementById('r-ang').textContent=ANG[a]||a;
    document.getElementById('r-st').textContent=(g.status||'listo').charAt(0).toUpperCase()+(g.status||'listo').slice(1);
    document.getElementById('r-sem').textContent=g.semana||'—';
    document.getElementById('r-rat').textContent=g.rating?'★'.repeat(g.rating)+'☆'.repeat(5-g.rating):'—';

    // Edit fields
    document.getElementById('m-tit').value=g.titulo||'';
    document.getElementById('m-hook').value=g.hook||'';
    document.getElementById('m-txt').value=g.texto||'';
    document.getElementById('m-scr').value=g.screen||'';
    document.getElementById('m-ig').value=g.caption_ig||'';
    document.getElementById('m-tk').value=g.caption_tk||'';
    document.getElementById('m-fue').value=g.fuentes||'';
    document.getElementById('m-ang').value=a;
    document.getElementById('m-st').value=g.status||'listo';
    document.getElementById('m-sem').value=g.semana||'';
    document.getElementById('m-not').value=g.notas||'';
    document.getElementById('m-msg').textContent='';
    curRat=g.rating||0;renderStars();

    // Aprobar button label
    var apBtn=document.getElementById('m-aprobar-btn');
    if(apBtn){
        var ap=g.status==='aprobado';
        apBtn.textContent=ap?'Quitar aprobacion':'Aprobar para filmar';
        apBtn.style.background=ap?'#8B6F3A':'#FDF8E8';
        apBtn.style.color=ap?'#fff':'#8B6F3A';
    }

    document.getElementById('modal').classList.add('open');
    document.body.style.overflow='hidden';

    // Render votos
    renderVotosModal(id);

    // Load variantes
    loadVariantes(id);
}
function closeModal(){document.getElementById('modal').classList.remove('open');document.body.style.overflow='';curId=null;}

function renderStars(){
    var el=document.getElementById('m-stars');el.innerHTML='';
    for(var i=1;i<=5;i++){(function(n){var s=document.createElement('span');s.innerHTML='&#9733;';s.className=n<=curRat?'on':'';s.onclick=function(){curRat=n;renderStars();};el.appendChild(s);})(i);}
}

function doSave(){
    if(!curId)return;
    var savedId=curId;
    var btn=document.getElementById('m-save'),msg=document.getElementById('m-msg');
    btn.disabled=true;btn.textContent='Guardando...';msg.textContent='';
    var reset=function(){var b=document.getElementById('m-save');if(b){b.disabled=false;b.textContent='Guardar';}};
    var timeout=setTimeout(reset,10000);
    var u={titulo:document.getElementById('m-tit').value,hook:document.getElementById('m-hook').value,texto:document.getElementById('m-txt').value,screen:document.getElementById('m-scr').value,caption_ig:document.getElementById('m-ig').value,caption_tk:document.getElementById('m-tk').value,fuentes:document.getElementById('m-fue').value,angulo:document.getElementById('m-ang').value,status:document.getElementById('m-st').value,semana:document.getElementById('m-sem').value,rating:curRat,notas:document.getElementById('m-not').value,updated_at:new Date().toISOString()};
    sb.from('guiones').update(u).eq('id',savedId).then(function(res){
        clearTimeout(timeout);
        if(res.error){var m=document.getElementById('m-msg');if(m){m.style.color='#C8453A';m.textContent='Error: '+res.error.message;}toast('Error al guardar',true);reset();return;}
        var idx=allG.findIndex(function(x){return x.id===savedId;});
        if(idx>=0)for(var k in u)allG[idx][k]=u[k];
        doFilter();
        var m=document.getElementById('m-msg');if(m){m.style.color='#2D8C5A';m.textContent='Guardado';}
        toast('Guardado');
        reset();
        setTimeout(function(){var m=document.getElementById('m-msg');if(m)m.textContent='';},3000);
    }).catch(function(err){
        clearTimeout(timeout);
        var m=document.getElementById('m-msg');if(m){m.style.color='#C8453A';m.textContent='Error: '+(err&&err.message?err.message:'desconocido');}
        toast('Error al guardar',true);
        reset();
    });
}

function doDiscard(){
    if(!curId||!confirm('Marcar como descartado?'))return;
    sb.from('guiones').update({status:'descartado',updated_at:new Date().toISOString()}).eq('id',curId).then(function(res){
        if(res.error){toast('Error',true);return;}
        var idx=allG.findIndex(function(x){return x.id===curId;});
        if(idx>=0)allG[idx].status='descartado';
        document.getElementById('m-st').value='descartado';
        doFilter();toast('Descartado');
    });
}

// Ideas
function openIdeas(){document.getElementById('ideas-modal').classList.add('open');document.body.style.overflow='hidden';loadIdeas();}
function closeIdeas(){document.getElementById('ideas-modal').classList.remove('open');document.body.style.overflow='';}
function loadIdeas(){
    sb.from('ideas').select('*').order('created_at',{ascending:false}).then(function(res){
        var el=document.getElementById('ideas-list'),ideas=res.data||[];
        if(!ideas.length){el.innerHTML='<p style="color:#ccc;font-size:11px;text-align:center;padding:10px">No hay ideas.</p>';return;}
        el.innerHTML='<div style="font-weight:600;font-size:11px;color:#8B6F3A;margin-bottom:6px">Ideas ('+ideas.length+')</div>'+
            ideas.map(function(i){return '<div style="background:#F5F5F3;border-radius:8px;padding:8px 10px;margin-bottom:5px;font-size:11px"><strong>'+esc(i.tema)+'</strong> <span style="color:#999">'+esc(i.autor||'')+'</span>'+(i.detalle?'<div style="color:#777;margin-top:2px;font-size:10px">'+esc(i.detalle)+'</div>':'')+'</div>';}).join('');
    });
}
function doSaveIdea(){
    var tema=document.getElementById('i-tema').value.trim(),msg=document.getElementById('i-msg');
    if(!tema){msg.style.color='#C8453A';msg.textContent='Completa el tema.';return;}
    msg.textContent='';
    sb.from('ideas').insert({autor:document.getElementById('i-aut').value.trim()||'Anonimo',angulo:document.getElementById('i-ang').value,tema:tema,detalle:document.getElementById('i-det').value.trim(),estado:'propuesta'}).then(function(res){
        if(res.error){msg.style.color='#C8453A';msg.textContent='Error: '+res.error.message;return;}
        document.getElementById('i-tema').value='';document.getElementById('i-det').value='';
        msg.style.color='#2D8C5A';msg.textContent='Enviada!';toast('Idea enviada');
        setTimeout(function(){msg.textContent='';},3000);loadIdeas();
    });
}

// Variantes
function loadVariantes(guionId){
    var el=document.getElementById('var-list');
    el.innerHTML='<div style="color:#ccc;font-size:11px;text-align:center;padding:8px">Cargando variantes...</div>';
    sb.from('variantes').select('*').eq('guion_id',guionId).order('created_at').then(function(res){
        var vars=res.data||[];
        if(!vars.length){el.innerHTML='<div style="color:#ccc;font-size:11px;text-align:center;padding:12px">Sin variantes. Genera 5 hooks de prueba para testear.</div>';return;}
        el.innerHTML=vars.map(function(v){
            var isGanador=v.tipo==='ganador';
            return '<div class="var-card'+(isGanador?' ganador':'')+'">'+
                '<div class="var-hook">'+esc(v.hook_variante)+'</div>'+
                '<div class="var-meta">'+
                '<span class="var-badge '+(isGanador?'var-badge-ganador':'var-badge-prueba')+'">'+(isGanador?'GANADOR':'PRUEBA')+'</span>'+
                '<span>Finalizacion: <input type="number" value="'+(v.tasa_finalizacion||0)+'" min="0" max="100" onchange="updateVar(\''+v.id+'\',\'tasa_finalizacion\',this.value)">%</span>'+
                '<span>Views: <input type="number" value="'+(v.views||0)+'" min="0" onchange="updateVar(\''+v.id+'\',\'views\',this.value)"></span>'+
                '<span class="var-actions">'+
                (isGanador?'':'<button class="var-winner-btn" onclick="markGanador(\''+v.id+'\',\''+guionId+'\')">Ganador</button>')+
                '<button onclick="deleteVar(\''+v.id+'\',\''+guionId+'\')">Borrar</button>'+
                '</span>'+
                '</div></div>';
        }).join('');
    });
}

function updateVar(varId,field,val){
    var u={};u[field]=Number(val);
    sb.from('variantes').update(u).eq('id',varId).then(function(res){
        if(!res.error)toast('Actualizado');
    });
}

function markGanador(varId,guionId){
    // Reset all to prueba first, then mark winner
    sb.from('variantes').update({tipo:'prueba'}).eq('guion_id',guionId).then(function(){
        return sb.from('variantes').update({tipo:'ganador'}).eq('id',varId);
    }).then(function(){
        toast('Ganador marcado');
        loadVariantes(guionId);
    });
}

function deleteVar(varId,guionId){
    if(!confirm('Borrar esta variante?'))return;
    sb.from('variantes').delete().eq('id',varId).then(function(){
        toast('Variante borrada');
        loadVariantes(guionId);
    });
}

function genVariantes(){
    if(!curId)return;
    var g=allG.find(function(x){return x.id===curId;});
    if(!g)return;
    var btn=document.getElementById('var-gen-btn');
    btn.disabled=true;btn.textContent='Generando...';

    // Generate 5 hook variations based on the original
    var hookBase=g.hook||g.titulo||'';
    var variations=[
        {hook:'Dato directo: '+rewriteHook(hookBase,'dato'),titulo:'V1 - Dato'},
        {hook:'Provocacion: '+rewriteHook(hookBase,'provocacion'),titulo:'V2 - Provocacion'},
        {hook:'Pregunta fuerte: '+rewriteHook(hookBase,'pregunta'),titulo:'V3 - Pregunta'},
        {hook:'Historia: '+rewriteHook(hookBase,'historia'),titulo:'V4 - Historia'},
        {hook:'Contrario: '+rewriteHook(hookBase,'contrario'),titulo:'V5 - Contrario'}
    ];

    var inserts=variations.map(function(v){
        return {guion_id:curId,hook_variante:v.hook,titulo_variante:v.titulo,tipo:'prueba'};
    });

    sb.from('variantes').insert(inserts).then(function(res){
        if(res.error){toast('Error: '+res.error.message,true);return;}
        toast('5 variantes generadas');
        loadVariantes(curId);
    }).finally(function(){btn.disabled=false;btn.textContent='Generar 5 hooks';});
}

function rewriteHook(base,style){
    // Simple client-side variation — for real AI variations, use Paperclip Escritor agent
    var clean=base.replace(/^["']/,'').replace(/["']$/,'').substring(0,120);
    switch(style){
        case 'dato': return clean;
        case 'provocacion': return 'Nadie te va a decir esto: '+clean.toLowerCase();
        case 'pregunta': return 'Pensa en esto: '+clean.toLowerCase();
        case 'historia': return 'Te cuento lo que paso: '+clean.toLowerCase();
        case 'contrario': return 'Todo el mundo piensa lo contrario, pero '+clean.toLowerCase();
        default: return clean;
    }
}

// Briefing
var allBriefing=[];
function loadBriefing(){
    var el=document.getElementById('briefing-list');
    el.innerHTML='<div style="color:#ccc;text-align:center;padding:20px">Cargando...</div>';
    sb.from('newsletter').select('*').order('id',{ascending:false}).limit(20).then(function(res){
        allBriefing=res.data||[];
        renderBriefing();
    });
}
function filterBriefing(){renderBriefing();}
function renderBriefing(){
    var el=document.getElementById('briefing-list');
    var filtro=document.getElementById('bf-filtro').value;
    var items=allBriefing.filter(function(n){
        if(filtro==='true')return n.convertido===true||n.convertido==='true';
        if(filtro==='false')return !n.convertido;
        return true;
    });
    document.getElementById('bf-count').textContent=items.length+' entradas';
    if(!items.length){el.innerHTML='<div style="color:#ccc;text-align:center;padding:40px;font-size:13px">No hay entradas todavia. El Investigador genera el primer briefing los lunes y jueves.</div>';return;}
    el.innerHTML=items.map(function(n){
        var ang=ANG[n.angulo]||n.angulo||'';
        var angC=ANG_C[n.angulo]||['#F0EFED','#999'];
        var conv=n.convertido===true||n.convertido==='true';
        return '<div style="background:#fff;border:1px solid #E8E4DD;border-radius:12px;padding:16px 18px;margin-bottom:12px">'+
            '<div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:10px">'+
            '<div style="flex:1">'+
            '<div style="font-size:13px;font-weight:700;color:#1a1a2e;line-height:1.4;margin-bottom:4px">'+esc(n.titulo)+'</div>'+
            (ang?'<span style="display:inline-block;background:'+angC[0]+';color:'+angC[1]+';font-size:10px;font-weight:600;padding:2px 8px;border-radius:20px;letter-spacing:0.5px">'+esc(ang)+'</span>':'')+'</div>'+
            (conv?'<span style="font-size:10px;font-weight:600;color:#2D8C5A;background:#E8F5EE;padding:3px 10px;border-radius:20px;white-space:nowrap;flex-shrink:0">Convertido</span>':
                  '<span style="font-size:10px;font-weight:600;color:#8B6F3A;background:#FDF8E8;padding:3px 10px;border-radius:20px;white-space:nowrap;flex-shrink:0">Sin convertir</span>')+
            '</div>'+
            (n.hook_propuesto?'<div style="background:#FDF8E8;border-left:3px solid #8B6F3A;padding:10px 14px;border-radius:0 8px 8px 0;margin-bottom:10px;font-size:12px;color:#5C4A28;font-style:italic;line-height:1.5">'+esc(n.hook_propuesto)+'</div>':'')+
            (n.dato_duro?'<div style="display:flex;gap:8px;align-items:flex-start;margin-bottom:8px"><span style="font-size:10px;letter-spacing:1px;font-weight:700;color:#8B6F3A;white-space:nowrap;padding-top:1px">DATO</span><span style="font-size:12px;color:#1a1a2e;line-height:1.5">'+esc(n.dato_duro)+'</span></div>':'')+
            (n.por_que_pega?'<div style="display:flex;gap:8px;align-items:flex-start;margin-bottom:8px"><span style="font-size:10px;letter-spacing:1px;font-weight:700;color:#999;white-space:nowrap;padding-top:1px">POR QUE</span><span style="font-size:12px;color:#555;line-height:1.5">'+esc(n.por_que_pega)+'</span></div>':'')+
            (n.fuente_url?'<div style="font-size:11px;margin-top:4px"><a href="'+esc(n.fuente_url)+'" target="_blank" rel="noopener" style="color:#8B6F3A;text-decoration:none;word-break:break-all">'+esc(n.fuente_url)+'</a></div>':'')+
            '</div>';
    }).join('');
}

// Reportes
function loadReportes(){
    var el=document.getElementById('reportes-list');
    el.innerHTML='<div style="color:#ccc;text-align:center;padding:20px">Cargando...</div>';
    sb.from('reportes').select('*').order('created_at',{ascending:false}).then(function(res){
        var items=res.data||[];
        if(!items.length){el.innerHTML='<div style="color:#ccc;text-align:center;padding:40px;font-size:13px">No hay reportes todavia. El Auditor genera el primero los viernes.</div>';return;}
        el.innerHTML=items.map(function(r){
            var fecha=new Date(r.created_at);
            var fechaStr=fecha.getDate()+'/'+(fecha.getMonth()+1)+'/'+fecha.getFullYear();
            return '<div style="background:#fff;border:1px solid #E8E4DD;border-radius:10px;padding:16px;margin-bottom:12px">'+
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'+
                '<div><strong style="font-size:13px">'+esc(r.titulo)+'</strong></div>'+
                '<div style="font-size:10px;color:#999">'+esc(r.agente)+' · '+fechaStr+'</div>'+
                '</div>'+
                '<div style="font-size:12px;color:#444;line-height:1.8;white-space:pre-wrap">'+esc(r.contenido)+'</div>'+
                '</div>';
        }).join('');
    });
}

// Tinder selector
var tinderQueue=[], tinderIdx=0, tinderSelected=[];

function initTinder(){
    // Curated 50 for session 20/4 — 92% marca personal, 8% producto
    var curated50=["LIFE1","LIFE2","LIFE3","LIFE4","LIFE5","LIFE6","PO1","PO2","PO3","PO4","PO5","PO6","PO7","PO9","PO12","DE1","DE3","DE4","DE5","DE9","HIST1","CO1","CO2","DE2","DE6","PD7","TN2","TN9","PD8","CR14","CR9","PD4","PD6","AL3","MU1","CR11","MK2","TN3","MU6","MK1","MK3","TN8","PD1","CR8","INV2","INV10","TN5","TN6","INV3","NL3","VIR1","VIR2","VIR3","VIR4","VIR5","VIR6","VIR7","VIR8","VIR9","VIR10","VIR11","VIR12","VIR13","VIR14","VIR15","VIR16","VIR17","VIR18"];
    var curated50Set={};curated50.forEach(function(id){curated50Set[id]=true;});
    tinderQueue=allG.filter(function(g){return curated50Set[g.id];});
    // Shuffle
    for(var i=tinderQueue.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=tinderQueue[i];tinderQueue[i]=tinderQueue[j];tinderQueue[j]=t;}
    tinderIdx=0;
    tinderSelected=[];
    renderTinderCard();
    renderTinderSelected();
}

function renderTinderCard(){
    var card=document.getElementById('t-card');
    var btns=document.getElementById('t-btns');
    var prog=document.getElementById('t-progress');

    if(tinderIdx>=tinderQueue.length){
        card.innerHTML='<div style="padding:40px;color:#999;font-size:14px">No quedan mas guiones. Tenes '+tinderSelected.length+' seleccionados.</div>';
        btns.style.display='none';
        prog.textContent='Listo — '+tinderSelected.length+' seleccionados';
        return;
    }

    var g=tinderQueue[tinderIdx];
    var a=(g.angulo||'').toLowerCase();
    var c=ANG_C[a]||['#F0EFED','#999'];

    prog.textContent=(tinderIdx+1)+' de '+tinderQueue.length+' · '+tinderSelected.length+' seleccionados';

    card.innerHTML='<div class="tinder-card" id="t-active">'+
        '<div class="tinder-badge"><span class="badge" style="background:'+c[0]+';color:'+c[1]+';font-size:10px;padding:4px 10px">'+esc(ANG[a]||a)+'</span></div>'+
        '<div class="tinder-id">'+esc(g.id)+' · '+esc(TEMAS[g.tema]||g.tema||'')+'</div>'+
        '<div class="tinder-title">'+esc(g.titulo)+'</div>'+
        '<div class="tinder-hook">'+esc(g.hook)+'</div>'+
        '</div>';
    btns.style.display='flex';
}

function tinderSwipe(dir){
    var cardEl=document.getElementById('t-active');
    if(!cardEl)return;

    if(dir==='si'){
        tinderSelected.push(tinderQueue[tinderIdx]);
        cardEl.classList.add('swipe-right');
    } else if(dir==='no'){
        cardEl.classList.add('swipe-left');
    }
    // skip = just move to next

    setTimeout(function(){
        tinderIdx++;
        renderTinderCard();
        renderTinderSelected();
    }, dir==='skip'?0:250);
}

function renderTinderSelected(){
    var el=document.getElementById('t-selected');
    if(!tinderSelected.length){el.innerHTML='';return;}

    el.innerHTML='<div class="tinder-selected-title">Seleccionados ('+tinderSelected.length+')</div>'+
        tinderSelected.map(function(g,i){
            var a=(g.angulo||'').toLowerCase();
            return '<div class="tinder-sel-item">'+
                '<span><strong>'+esc(g.id)+'</strong> '+esc(g.titulo.substring(0,45))+(g.titulo.length>45?'...':'')+'</span>'+
                '<button class="tinder-sel-remove" onclick="tinderRemove('+i+')">x</button>'+
                '</div>';
        }).join('')+
        (tinderSelected.length>=5?'<button class="tinder-done-btn" onclick="tinderCreateSession()">Continuar con '+tinderSelected.length+' guiones seleccionados →</button>':'');
}

function tinderRemove(idx){
    tinderSelected.splice(idx,1);
    renderTinderSelected();
}

function tinderCreateSession(){
    if(!tinderSelected.length)return;
    // Go to Phase 2 — editing proposals
    document.getElementById('t-phase1').style.display='none';
    renderTinderPhase2();
    document.getElementById('t-phase2').style.display='block';
    window.scrollTo(0,0);
}

function renderTinderPhase2(){
    var el=document.getElementById('t-phase2');
    var n=tinderSelected.length;
    var html='<div class="p2-header">Propuestas de Celina</div>'+
        '<div class="p2-sub">'+n+' guiones seleccionados — Edita el hook o el texto de cada uno (o dejalo igual si esta bien)</div>';

    tinderSelected.forEach(function(g,i){
        html+='<div class="p2-card" id="p2c-'+i+'">'+
            '<div class="p2-card-top">'+
                '<div class="p2-card-num">'+(i+1)+'</div>'+
                '<div class="p2-card-meta">'+
                    '<div class="p2-card-id">'+esc(g.id)+'</div>'+
                    '<div class="p2-card-title">'+esc(g.titulo)+'<span class="p2-changed-badge" id="p2badge-'+i+'" style="display:none">MODIFICADO</span></div>'+
                '</div>'+
            '</div>'+
            '<div class="p2-label">Hook (primera frase)</div>'+
            '<textarea class="p2-textarea" id="p2hook-'+i+'" rows="2" oninput="p2markChanged('+i+')">'+esc(g.hook||'')+'</textarea>'+
            '<div class="p2-label" style="margin-top:10px">Guion completo</div>'+
            '<textarea class="p2-textarea" id="p2texto-'+i+'" rows="6" oninput="p2markChanged('+i+')">'+esc(g.texto||'')+'</textarea>'+
            '<textarea class="p2-nota" id="p2nota-'+i+'" rows="2" placeholder="Nota para Santiago (opcional): \'quiero que el hook sea mas directo\', \'cambia el final\', etc."></textarea>'+
        '</div>';
    });

    html+='<button class="p2-confirm-btn" id="p2-submit-btn" onclick="tinderConfirmSession()">Guardar cambios y crear sesion</button>'+
          '<button class="p2-back-btn" onclick="tinderBackToPhase1()">Volver a la seleccion</button>';

    el.innerHTML=html;

    // Store originals for diff detection
    window._p2originals=tinderSelected.map(function(g){return {hook:g.hook||'',texto:g.texto||''};});
}

function p2markChanged(i){
    var origHook=window._p2originals[i].hook;
    var origTexto=window._p2originals[i].texto;
    var newHook=document.getElementById('p2hook-'+i).value;
    var newTexto=document.getElementById('p2texto-'+i).value;
    var changed=(newHook.trim()!==origHook.trim())||(newTexto.trim()!==origTexto.trim());
    var badge=document.getElementById('p2badge-'+i);
    if(badge)badge.style.display=changed?'inline':'none';
}

function tinderBackToPhase1(){
    document.getElementById('t-phase2').style.display='none';
    document.getElementById('t-phase1').style.display='block';
}

function tinderConfirmSession(){
    var btn=document.getElementById('p2-submit-btn');
    btn.disabled=true;
    btn.textContent='Guardando...';

    var updates=[];
    tinderSelected.forEach(function(g,i){
        var newHook=document.getElementById('p2hook-'+i).value.trim();
        var newTexto=document.getElementById('p2texto-'+i).value.trim();
        var nota=document.getElementById('p2nota-'+i).value.trim();
        var origHook=window._p2originals[i].hook;
        var origTexto=window._p2originals[i].texto;
        var changed=(newHook!==origHook.trim())||(newTexto!==origTexto.trim());
        if(changed){
            updates.push({id:g.id,hook:newHook,texto:newTexto,nota:nota});
        } else if(nota){
            updates.push({id:g.id,nota:nota}); // note only
        }
    });

    // Apply all updates to guiones in Supabase, then create session
    var promises=updates.map(function(u){
        var patch={};
        if(u.hook!==undefined)patch.hook=u.hook;
        if(u.texto!==undefined)patch.texto=u.texto;
        return sb.from('guiones').update(patch).eq('id',u.id).then(function(res){
            // Save nota as idea if present
            if(u.nota){
                sb.from('ideas').insert({
                    autor:'Celina',angulo:'sol',tema:'',
                    detalle:u.nota,
                    tipo:'mejora',guion_ref:u.id,
                    estado:'aplicada'
                });
            }
            return res;
        });
    });

    Promise.all(promises).then(function(){
        var ids=tinderSelected.map(function(g){return g.id;});
        var hoy=new Date();
        var lunes=new Date(hoy);
        lunes.setDate(lunes.getDate()+((8-lunes.getDay())%7||7));
        var fecha=lunes.toISOString().split('T')[0];
        var sem='Lun '+lunes.getDate()+'/'+(lunes.getMonth()+1);

        sb.from('sesiones').insert({
            fecha:fecha,
            guiones_ids:ids,
            estado:'planificada',
            notas:ids.length+' guiones seleccionados via Selector'+(updates.length?' — '+updates.length+' editados por Celina':'')
        }).then(function(res){
            if(res.error){toast('Error: '+res.error.message,true);btn.disabled=false;btn.textContent='Guardar cambios y crear sesion';return;}
            sb.from('guiones').update({semana:sem}).in('id',ids).then(function(){
                var msg='Sesion creada con '+ids.length+' guiones';
                if(updates.length)msg+=' — '+updates.length+' editados por Celina';
                toast(msg);
                // Reset
                tinderSelected=[];
                window._p2originals=[];
                document.getElementById('t-phase2').style.display='none';
                document.getElementById('t-phase1').style.display='block';
                // Reload allG so changes reflect
                loadAll();
                renderTinderSelected();
            });
        });
    });
}

// Keyboard shortcuts for tinder
document.addEventListener('keydown',function(e){
    if(!document.getElementById('v-selector').classList.contains('on'))return;
    if(document.getElementById('modal').classList.contains('open'))return;
    if(e.key==='ArrowLeft')tinderSwipe('no');
    if(e.key==='ArrowRight')tinderSwipe('si');
    if(e.key==='ArrowDown'||e.key==='ArrowUp')tinderSwipe('skip');
});

// Calendario
function loadCalendario(){
    var grid=document.getElementById('cal-grid');
    grid.innerHTML='<div style="color:#ccc;text-align:center;padding:20px">Cargando...</div>';

    sb.from('publicaciones').select('*').order('fecha_programada').then(function(res){
        var pubs=res.data||[];

        // Get next 2 weeks of weekdays
        var days=[];
        var d=new Date();
        while(days.length<10){
            if(d.getDay()!==0&&d.getDay()!==6) days.push(new Date(d));
            d.setDate(d.getDate()+1);
        }

        // Split into 2 weeks
        var html='';
        for(var w=0;w<2;w++){
            html+='<div style="font-size:10px;font-weight:600;color:#999;letter-spacing:1px;margin:12px 0 6px">SEMANA '+(w+1)+'</div>';
            html+='<div class="cal-week">';
            for(var i=w*5;i<(w+1)*5&&i<days.length;i++){
                var day=days[i];
                var dateStr=day.toISOString().split('T')[0];
                var dayName=['Dom','Lun','Mar','Mie','Jue','Vie','Sab'][day.getDay()];
                var dayNum=day.getDate()+'/'+(day.getMonth()+1);

                var dayPubs=pubs.filter(function(p){return p.fecha_programada===dateStr;});

                html+='<div class="cal-day">';
                html+='<div class="cal-day-head"><span>'+dayName+'</span><span class="cal-day-date">'+dayNum+'</span></div>';

                if(dayPubs.length){
                    dayPubs.forEach(function(p){
                        var tipo=p.plataforma==='tiktok_prueba'?'prueba':'oficial';
                        html+='<div class="cal-item '+tipo+'">';
                        html+='<div class="cal-item-title">'+esc(p.caption.substring(0,40))+'</div>';
                        html+='<div class="cal-item-meta">'+esc(p.plataforma)+' · '+esc(p.estado)+'</div>';
                        html+='</div>';
                    });
                } else {
                    html+='<div class="cal-empty">Sin contenido</div>';
                }
                html+='</div>';
            }
            html+='</div>';
        }

        grid.innerHTML=html||'<div class="cal-empty">No hay publicaciones programadas. Crea una sesion para empezar.</div>';
    });

    loadSesiones();
}

function loadSesiones(){
    sb.from('sesiones').select('*').order('fecha',{ascending:false}).then(function(res){
        var el=document.getElementById('sesiones-list');
        var sesiones=res.data||[];
        if(!sesiones.length){
            el.innerHTML='<div style="color:#ccc;font-size:12px;text-align:center;padding:16px">No hay sesiones creadas. Cuando te juntes con Celina a filmar, crea una sesion aca.</div>';
            return;
        }
        el.innerHTML=sesiones.map(function(s){
            var gIds=s.guiones_ids||[];
            var numGuiones=gIds.length;
            var guionesHtml='';
            var showCelinaPanel=(s.estado==='filmada'||s.estado==='editada'||s.estado==='publicando');

            if(showCelinaPanel&&gIds.length&&allG.length){
                // Celina editing panel
                var guionesData=gIds.map(function(gid){return allG.find(function(x){return x.id===gid;});}).filter(Boolean);
                var listos=guionesData.filter(function(g){return g.drive_link&&g.drive_link.length>5;}).length;
                var pct=numGuiones>0?Math.round(listos/numGuiones*100):0;

                guionesHtml='<div class="celina-panel">'+
                    '<div class="celina-panel-title">Panel de Edicion — Celina</div>'+
                    '<div class="celina-panel-sub">Subi el link de Google Drive de cada video editado. Cuando esten todos, Santiago programa la publicacion.</div>'+
                    '<div class="celina-progress-bar"><div class="celina-progress-fill" style="width:'+pct+'%"></div></div>'+
                    '<div style="font-size:10px;color:#8B6F3A;margin-bottom:10px;font-weight:600">'+listos+' de '+numGuiones+' listos ('+pct+'%)</div>'+
                    guionesData.map(function(g){
                        var a=(g.angulo||'').toLowerCase();
                        var c=ANG_C[a]||['#F0EFED','#999'];
                        var hasDrive=g.drive_link&&g.drive_link.length>5;
                        var edStatus=hasDrive?'listo':(g.edicion_notas?'editando':'pendiente');
                        return '<div class="celina-row">'+
                            '<div class="celina-row-top">'+
                                '<div class="celina-row-info" onclick="openModal(\''+esc(g.id)+'\')" style="cursor:pointer">'+
                                    '<span class="celina-row-id">'+esc(g.id)+'</span>'+
                                    '<span class="badge" style="background:'+c[0]+';color:'+c[1]+';font-size:7px">'+esc(ANG[a]||a)+'</span>'+
                                    '<span class="celina-row-title">'+esc(g.titulo)+'</span>'+
                                '</div>'+
                                '<div class="celina-status">'+
                                    '<span class="celina-st-btn active-'+edStatus+'">'+edStatus+'</span>'+
                                '</div>'+
                            '</div>'+
                            '<div class="celina-row-bottom">'+
                                (hasDrive?
                                    '<a href="'+esc(g.drive_link)+'" target="_blank" class="celina-drive-link">Abrir en Drive</a>'+
                                    '<input class="celina-drive-input" style="flex:0.5" value="'+esc(g.drive_link)+'" id="drive-'+esc(g.id)+'" placeholder="Link de Drive">'
                                :
                                    '<input class="celina-drive-input" id="drive-'+esc(g.id)+'" placeholder="Pega aca el link de Google Drive del video editado" value="'+esc(g.drive_link||'')+'">'
                                )+
                                '<input class="celina-notes-input" style="max-width:180px" id="notas-'+esc(g.id)+'" placeholder="Notas de edicion" value="'+esc(g.edicion_notas||'')+'">'+
                                '<button class="celina-save-btn" onclick="saveCelinaEdit(\''+esc(g.id)+'\')">Guardar</button>'+
                            '</div>'+
                        '</div>';
                    }).join('')+
                '</div>';
            } else if(gIds.length&&allG.length){
                // Normal guiones grid for planificada
                guionesHtml='<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:6px;margin-top:10px">'+
                gIds.map(function(gid){
                    var g=allG.find(function(x){return x.id===gid;});
                    if(!g) return '';
                    var a=(g.angulo||'').toLowerCase();
                    var c=ANG_C[a]||['#F0EFED','#999'];
                    return '<div style="background:#F5F5F3;border:1px solid #E8E4DD;border-radius:6px;padding:10px;cursor:pointer" onclick="openModal(\''+esc(g.id)+'\')">'+
                        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">'+
                        '<span style="font-family:Cinzel,serif;font-size:12px;color:#8B6F3A">'+esc(g.id)+'</span>'+
                        '<span class="badge" style="background:'+c[0]+';color:'+c[1]+'">'+esc(ANG[a]||a)+'</span></div>'+
                        '<div style="font-weight:600;font-size:11px;margin-bottom:3px">'+esc(g.titulo)+'</div>'+
                        '<div style="font-size:10px;color:#888;font-style:italic;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc((g.hook||'').substring(0,80))+'</div>'+
                        '</div>';
                }).join('')+'</div>';
            }

            // Session status color
            var stColor=s.estado==='planificada'?'#D48A2C':s.estado==='filmada'?'#C8453A':s.estado==='editada'?'#4A90D9':'#2D8C5A';

            var sesNombre=s.notas||('Sesion '+s.fecha);
            return '<div style="background:#fff;border:1px solid #E8E4DD;border-radius:10px;padding:14px;margin-bottom:10px">'+
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">'+
                '<div><strong style="font-size:13px">'+esc(sesNombre)+'</strong> <span style="font-size:11px;color:'+stColor+';font-weight:600"> · '+esc(s.estado.toUpperCase())+'</span> <span style="font-size:11px;color:#999">· '+numGuiones+' guiones · '+esc(s.fecha)+'</span></div>'+
                '<div style="display:flex;gap:6px;align-items:center">'+
                '<button style="background:none;border:1px solid #E8E4DD;border-radius:6px;padding:4px 10px;font-size:10px;color:#8B6F3A;font-weight:600;cursor:pointer" onclick="openSesEdit(\''+s.id+'\')">Editar</button>'+
                (s.estado==='planificada'?'<button class="sesion-btn" style="font-size:9px;padding:5px 10px" onclick="updateSesion(\''+s.id+'\',\'filmada\')">Filmada</button>':'')+
                (s.estado==='filmada'?'<button class="sesion-btn" style="font-size:9px;padding:5px 10px" onclick="updateSesion(\''+s.id+'\',\'editada\')">Editada</button>':'')+
                (s.estado==='editada'?'<button class="sesion-btn" style="font-size:9px;padding:5px 10px;background:#2D8C5A" onclick="programarSesion(\''+s.id+'\')">Programar</button>':'')+
                '</div></div>'+
                guionesHtml+
                '</div>';
        }).join('');
    });
}

function saveCelinaEdit(guionId){
    var driveEl=document.getElementById('drive-'+guionId);
    var notasEl=document.getElementById('notas-'+guionId);
    if(!driveEl)return;
    var updates={drive_link:driveEl.value.trim(),edicion_notas:notasEl?notasEl.value.trim():''};
    sb.from('guiones').update(updates).eq('id',guionId).then(function(res){
        if(res.error){toast('Error al guardar',true);return;}
        // Update local data
        var g=allG.find(function(x){return x.id===guionId;});
        if(g){g.drive_link=updates.drive_link;g.edicion_notas=updates.edicion_notas;}
        toast('Guardado: '+guionId);
        loadSesiones();
    });
}

function crearSesion(){
    var guionesListos=allG.filter(function(g){return g.status==='listo'&&(g.tipo||'organico')==='organico';});
    if(guionesListos.length<5){toast('Necesitas al menos 5 guiones en "Listo" para crear una sesion',true);return;}

    // Take first 10 (or fewer) guiones listos
    var seleccion=guionesListos.slice(0,10);
    var ids=seleccion.map(function(g){return g.id;});
    var hoy=new Date().toISOString().split('T')[0];

    sb.from('sesiones').insert({
        fecha:hoy,
        guiones_ids:ids,
        estado:'planificada',
        notas:ids.length+' guiones: '+ids.join(', ')
    }).then(function(res){
        if(res.error){toast('Error: '+res.error.message,true);return;}
        toast('Sesion creada con '+ids.length+' guiones');
        loadSesiones();
    });
}

function updateSesion(id,estado){
    sb.from('sesiones').update({estado:estado}).eq('id',id).then(function(res){
        if(res.error){toast('Error',true);return;}
        toast('Sesion marcada como '+estado);
        loadSesiones();
    });
}

function programarSesion(sesionId){
    // Get sesion, then create publicaciones for 2 weeks
    sb.from('sesiones').select('*').eq('id',sesionId).single().then(function(res){
        if(res.error||!res.data){toast('Error al leer sesion',true);return;}
        var sesion=res.data;
        var guionIds=sesion.guiones_ids||[];

        // Get next weekdays
        var days=[];
        var d=new Date();
        d.setDate(d.getDate()+1); // start tomorrow
        while(days.length<guionIds.length){
            if(d.getDay()!==0&&d.getDay()!==6) days.push(new Date(d));
            d.setDate(d.getDate()+1);
        }

        // Create publications
        var inserts=[];
        guionIds.forEach(function(gid,idx){
            if(idx>=days.length)return;
            var fecha=days[idx].toISOString().split('T')[0];
            var g=allG.find(function(x){return x.id===gid;});
            var caption=g?g.hook||g.titulo:'Guion '+gid;

            // 5 test reels on TikTok
            for(var v=1;v<=5;v++){
                inserts.push({
                    guion_id:gid,
                    plataforma:'tiktok_prueba',
                    estado:'programado',
                    fecha_programada:fecha,
                    hora_programada:'12:00',
                    caption:'V'+v+': '+caption.substring(0,120),
                    hashtags:'#Tandil #RealEstate #Inversiones'
                });
            }

            // Official winner next day (if not last)
            if(idx>0){
                var prevGid=guionIds[idx-1];
                var prevG=allG.find(function(x){return x.id===prevGid;});
                var prevCap=prevG?prevG.hook||prevG.titulo:'';
                ['instagram','tiktok','youtube','facebook'].forEach(function(plat){
                    inserts.push({
                        guion_id:prevGid,
                        plataforma:plat,
                        estado:'programado',
                        fecha_programada:fecha,
                        hora_programada:plat==='youtube'?'15:00':plat==='facebook'?'20:00':'11:00',
                        caption:prevCap.substring(0,200),
                        hashtags:'#Tandil #RealEstate #SantiagoFunes'
                    });
                });
            }
        });

        sb.from('publicaciones').insert(inserts).then(function(r){
            if(r.error){toast('Error: '+r.error.message,true);return;}
            sb.from('sesiones').update({estado:'publicando'}).eq('id',sesionId);
            toast(inserts.length+' publicaciones programadas para '+guionIds.length+' dias');
            loadCalendario();
        });
    });
}

// ── PARA FILMAR ─────────────────────────────────────────────────────
function loadParaFilmar(){
    loadVotos(function(){_renderParaFilmar();});
}
function _renderParaFilmar(){
    var el=document.getElementById('pf-content');
    var cnt=document.getElementById('pf-count');
    // Build list: guiones with at least 1 voto
    var conVotos=allG.filter(function(g){return getVotosPorGuion(g.id).length>0;}).map(function(g){
        return {g:g,votos:getVotosPorGuion(g.id)};
    }).sort(function(a,b){return b.votos.length-a.votos.length;});
    cnt.textContent=conVotos.length+' guion'+(conVotos.length!==1?'es':'')+' seleccionado'+(conVotos.length!==1?'s':'');
    if(!conVotos.length){
        el.innerHTML='<div style="text-align:center;padding:48px;color:#ccc;font-size:13px">Nadie seleccionó guiones todavía.<br><span style="font-size:11px">Abrí un guion y tocá "Seleccionar para filmar".</span></div>';
        return;
    }
    // Group by vote count
    var groups={3:[],2:[],1:[]};
    conVotos.forEach(function(item){
        var n=Math.min(item.votos.length,3);
        groups[n].push(item);
    });
    var html='';
    [[3,'Los 3 coinciden','#2D8C5A'],[2,'2 de 3 coinciden','#8B6F3A'],[1,'Solo 1 lo seleccionó','#999']].forEach(function(grp){
        var n=grp[0],label=grp[1],color=grp[2];
        if(!groups[n].length)return;
        html+='<div style="padding:16px 20px 4px"><div style="font-size:11px;font-weight:700;color:'+color+';letter-spacing:0.5px;text-transform:uppercase;margin-bottom:10px">'+label+' ('+groups[n].length+')</div>';
        html+='<div class="grid">';
        groups[n].forEach(function(item){
            var g=item.g,votos=item.votos;
            var a=(g.angulo||'').toLowerCase(),c=ANG_C[a]||['#F0EFED','#999'];
            html+='<div class="pf-card" style="border-left:3px solid '+color+'">'+
                '<div class="card-head"><span class="card-id">'+esc(g.id)+'</span>'+
                '<span class="badge" style="background:'+c[0]+';color:'+c[1]+'">'+esc(ANG[a]||a)+'</span>'+
                '<span style="margin-left:auto;display:flex;gap:3px">'+votos.map(function(v){var b=BADGE_MAP[v.user_email]||'?';var col2=BADGE_COLOR[b]||'#999';return '<span style="background:'+col2+';color:#fff;border-radius:50%;width:18px;height:18px;font-size:9px;font-weight:700;display:inline-flex;align-items:center;justify-content:center">'+b+'</span>';}).join('')+'</span>'+
                '</div>'+
                '<div class="card-title" onclick="openModal(\''+esc(g.id)+'\')" style="cursor:pointer;margin-bottom:6px">'+esc(g.titulo)+'</div>'+
                '<div class="card-hook" style="margin-bottom:10px">'+esc(g.hook||'')+'</div>'+
                (g.status==='filmado'
                    ? '<div style="display:flex;align-items:center;gap:6px"><span style="font-size:10px;font-weight:700;color:#2D8C5A;background:#E8F7F0;padding:4px 10px;border-radius:6px">✓ Filmado</span><button onclick="pfDesmarcarFilmado(\''+esc(g.id)+'\')" style="font-size:9px;color:#999;background:none;border:none;cursor:pointer;padding:2px 4px">Desmarcar</button></div>'
                    : '<button onclick="pfMarcarFilmado(\''+esc(g.id)+'\')" style="background:#E8F7F0;color:#2D8C5A;border:1px solid #2D8C5A44;padding:7px 14px;border-radius:6px;font-size:10px;font-weight:700;cursor:pointer">Marcar como filmado</button>'
                )+
            '</div>';
        });
        html+='</div></div>';
    });
    el.innerHTML=html;
}

function pfMarcarFilmado(id){
    sb.from('guiones').update({status:'filmado',updated_at:new Date().toISOString()}).eq('id',id).then(function(res){
        if(res.error){toast('Error',true);return;}
        var g=allG.find(function(x){return x.id===id;});
        if(g)g.status='filmado';
        _renderParaFilmar();
        toast('Marcado como filmado');
    });
}
function pfDesmarcarFilmado(id){
    sb.from('guiones').update({status:'listo',updated_at:new Date().toISOString()}).eq('id',id).then(function(res){
        if(res.error){toast('Error',true);return;}
        var g=allG.find(function(x){return x.id===id;});
        if(g)g.status='listo';
        _renderParaFilmar();
        toast('Desmarcado');
    });
}

function renderVotosModal(guionId){
    var btn=document.getElementById('btn-votar');
    var disp=document.getElementById('votos-display');
    if(!btn||!disp)return;
    var votos=getVotosPorGuion(guionId);
    var yoVote_=yoVote(guionId);
    btn.textContent=yoVote_?'Quitar mi seleccion':'Seleccionar para filmar';
    btn.style.background=yoVote_?'#8B6F3A':'#FDF8E8';
    btn.style.color=yoVote_?'#fff':'#8B6F3A';
    btn.style.border=yoVote_?'none':'1px solid #D4A83A55';
    disp.innerHTML=votos.length?
        '<span style="font-size:10px;color:#999;margin-right:4px">'+votos.length+' voto'+(votos.length>1?'s':'')+':</span>'+
        votos.map(function(v){var b=BADGE_MAP[v.user_email]||'?';var col=BADGE_COLOR[b]||'#999';return '<span style="background:'+col+';color:#fff;border-radius:50%;width:20px;height:20px;font-size:10px;font-weight:700;display:inline-flex;align-items:center;justify-content:center">'+b+'</span>';}).join('')
        :'<span style="font-size:10px;color:#bbb">Nadie lo seleccionó todavía</span>';
}

function doVotar(){
    if(!curId||!curUserEmail)return;
    var btn=document.getElementById('btn-votar');
    btn.disabled=true;
    if(yoVote(curId)){
        sb.from('votos_filmar').delete().eq('guion_id',curId).eq('user_email',curUserEmail).then(function(res){
            if(res.error){toast('Error',true);btn.disabled=false;return;}
            allVotos=allVotos.filter(function(v){return !(v.guion_id===curId&&v.user_email===curUserEmail);});
            renderVotosModal(curId);doFilter();btn.disabled=false;toast('Quitado de tu seleccion');
        });
    } else {
        sb.from('votos_filmar').insert({guion_id:curId,user_email:curUserEmail}).then(function(res){
            if(res.error){toast('Error',true);btn.disabled=false;return;}
            loadVotos(function(){renderVotosModal(curId);doFilter();btn.disabled=false;toast('Agregado a tu seleccion');});
        });
    }
}

function doAprobarGuion(){
    if(!curId)return;
    var btn=document.getElementById('m-aprobar-btn');
    var g=allG.find(function(x){return x.id===curId;});
    if(!g)return;
    var isAprobado=g.status==='aprobado';
    var newStatus=isAprobado?'listo':'aprobado';
    btn.disabled=true;
    sb.from('guiones').update({status:newStatus,updated_at:new Date().toISOString()}).eq('id',curId).then(function(res){
        if(res.error){toast('Error',true);btn.disabled=false;return;}
        g.status=newStatus;
        document.getElementById('m-st').value=newStatus;
        document.getElementById('r-st').textContent=newStatus.charAt(0).toUpperCase()+newStatus.slice(1);
        btn.textContent=newStatus==='aprobado'?'Quitar aprobacion':'Aprobar para filmar';
        btn.style.background=newStatus==='aprobado'?'#8B6F3A':'#FDF8E8';
        btn.style.color=newStatus==='aprobado'?'#fff':'#8B6F3A';
        doFilter();
        toast(newStatus==='aprobado'?'Aprobado para filmar':'Quitado de Para Filmar');
        btn.disabled=false;
    });
}

function openModal_orig_hook(id){
    // Update aprobar button label after modal opens
    setTimeout(function(){
        var g=allG.find(function(x){return x.id===id;});
        var btn=document.getElementById('m-aprobar-btn');
        if(btn&&g){
            var ap=g.status==='aprobado';
            btn.textContent=ap?'Quitar aprobacion':'Aprobar para filmar';
            btn.style.background=ap?'#8B6F3A':'#FDF8E8';
            btn.style.color=ap?'#fff':'#8B6F3A';
        }
    },50);
}

function pfUnapprove(id){
    sb.from('guiones').update({status:'listo',updated_at:new Date().toISOString()}).eq('id',id).then(function(res){
        if(res.error){toast('Error',true);return;}
        var g=allG.find(function(x){return x.id===id;});
        if(g)g.status='listo';
        loadParaFilmar();
        toast('Quitado de Para Filmar');
    });
}

function pfCreateSession(){
    var aprobados=allG.filter(function(g){return g.status==='aprobado';});
    if(!aprobados.length){toast('No hay guiones aprobados',true);return;}
    var ids=aprobados.map(function(g){return g.id;});
    var hoy=new Date().toISOString().split('T')[0];
    sb.from('sesiones').insert({
        fecha:hoy,guiones_ids:ids,estado:'planificada',
        notas:ids.length+' guiones aprobados para filmar'
    }).then(function(res){
        if(res.error){toast('Error: '+res.error.message,true);return;}
        toast('Sesion creada con '+ids.length+' guiones');
        loadSesiones();
    });
}

// ── SESSION EDIT ─────────────────────────────────────────────────────
var curSes=null; // current session being edited

function openSesEdit(sesId){
    sb.from('sesiones').select('*').eq('id',sesId).single().then(function(res){
        if(res.error||!res.data){toast('Error al cargar sesion',true);return;}
        curSes=res.data;
        var el=document.getElementById('ses-nombre');
        el.value=curSes.notas||('Sesion '+curSes.fecha);
        renderSesGlist();
        // Populate merge dropdown
        sb.from('sesiones').select('id,fecha,notas,estado').order('fecha',{ascending:false}).then(function(r){
            var sel=document.getElementById('ses-merge-sel');
            sel.innerHTML='<option value="">— No unir —</option>';
            (r.data||[]).forEach(function(s){
                if(s.id===sesId)return;
                var opt=document.createElement('option');
                opt.value=s.id;
                opt.textContent=(s.notas||('Sesion '+s.fecha))+' ('+s.estado+')';
                sel.appendChild(opt);
            });
        });
        document.getElementById('ses-search-results').innerHTML='';
        document.getElementById('ses-add-q').value='';
        document.getElementById('ses-msg').textContent='';
        document.getElementById('ses-edit-modal').classList.add('open');
        document.body.style.overflow='hidden';
    });
}

function closeSesEdit(){
    document.getElementById('ses-edit-modal').classList.remove('open');
    document.body.style.overflow='';
    curSes=null;
}

function renderSesGlist(){
    var el=document.getElementById('ses-glist');
    var ids=curSes.guiones_ids||[];
    if(!ids.length){el.innerHTML='<div style="color:#ccc;font-size:11px;text-align:center;padding:12px">Sin guiones</div>';return;}
    el.innerHTML=ids.map(function(gid){
        var g=allG.find(function(x){return x.id===gid;});
        return '<div class="ses-gitem">'+
            '<span class="ses-gitem-info"><span class="ses-gitem-id">'+esc(gid)+'</span>'+(g?esc(g.titulo.substring(0,45)):'(no encontrado)')+'</span>'+
            '<button class="ses-rm-btn" onclick="sesRemoveGuion(\''+esc(gid)+'\')">×</button>'+
        '</div>';
    }).join('');
}

function sesRemoveGuion(gid){
    if(!curSes)return;
    curSes.guiones_ids=(curSes.guiones_ids||[]).filter(function(x){return x!==gid;});
    renderSesGlist();
}

function sesSearchGuion(){
    var q=document.getElementById('ses-add-q').value.toLowerCase().trim();
    var res=document.getElementById('ses-search-results');
    if(q.length<2){res.innerHTML='';return;}
    var matches=allG.filter(function(g){
        return g.id.toLowerCase().includes(q)||g.titulo.toLowerCase().includes(q);
    }).slice(0,5);
    if(!matches.length){res.innerHTML='<div style="font-size:10px;color:#bbb;padding:4px 8px">Sin resultados</div>';return;}
    res.innerHTML='<div style="border:1px solid #E8E4DD;border-radius:8px;overflow:hidden;margin-bottom:4px">'+
        matches.map(function(g){
            return '<div style="padding:7px 10px;font-size:11px;cursor:pointer;border-bottom:1px solid #F5F5F3" onclick="sesPickGuion(\''+esc(g.id)+'\')">'+
                '<strong style="color:#8B6F3A">'+esc(g.id)+'</strong> — '+esc(g.titulo.substring(0,50))+'</div>';
        }).join('')+'</div>';
}

function sesPickGuion(gid){
    if(!curSes)return;
    if((curSes.guiones_ids||[]).includes(gid)){toast(gid+' ya esta en la sesion');return;}
    curSes.guiones_ids=(curSes.guiones_ids||[]).concat([gid]);
    renderSesGlist();
    document.getElementById('ses-add-q').value='';
    document.getElementById('ses-search-results').innerHTML='';
}

function sesAddGuion(){
    var q=document.getElementById('ses-add-q').value.trim().toUpperCase();
    if(!q)return;
    var g=allG.find(function(x){return x.id===q;});
    if(!g){toast('ID no encontrado: '+q,true);return;}
    sesPickGuion(q);
}

function saveSesEdit(){
    if(!curSes)return;
    var nombre=document.getElementById('ses-nombre').value.trim();
    var msg=document.getElementById('ses-msg');
    msg.textContent='Guardando...';
    sb.from('sesiones').update({
        guiones_ids:curSes.guiones_ids||[],
        notas:nombre||curSes.notas
    }).eq('id',curSes.id).then(function(res){
        if(res.error){msg.style.color='#C8453A';msg.textContent='Error: '+res.error.message;return;}
        msg.style.color='#2D8C5A';msg.textContent='Guardado';
        setTimeout(function(){closeSesEdit();loadSesiones();},600);
    });
}

function doMergeSesion(){
    if(!curSes)return;
    var targetId=document.getElementById('ses-merge-sel').value;
    if(!targetId){toast('Selecciona una sesion para unir',true);return;}
    if(!confirm('Esto va a unir los guiones de las dos sesiones y eliminar la otra. Confirmar?'))return;
    sb.from('sesiones').select('guiones_ids').eq('id',targetId).single().then(function(res){
        if(res.error||!res.data){toast('Error',true);return;}
        var combined=(curSes.guiones_ids||[]).concat(res.data.guiones_ids||[]);
        // deduplicate
        combined=combined.filter(function(v,i,a){return a.indexOf(v)===i;});
        sb.from('sesiones').update({guiones_ids:combined}).eq('id',curSes.id).then(function(){
            sb.from('sesiones').delete().eq('id',targetId).then(function(){
                toast('Sesiones unidas — '+combined.length+' guiones');
                closeSesEdit();
                loadSesiones();
            });
        });
    });
}

function deleteSesion(){
    if(!curSes)return;
    if(!confirm('Eliminar esta sesion? Los guiones no se borran, solo la sesion.'))return;
    sb.from('sesiones').delete().eq('id',curSes.id).then(function(res){
        if(res.error){toast('Error',true);return;}
        toast('Sesion eliminada');
        closeSesEdit();
        loadSesiones();
    });
}

// ---- FICHAS ----
var RAILWAY_SCRAPER_URL='https://scraper-fichas.up.railway.app'; // actualizar con URL real del deploy
var fichasImages=[];

function fichasHandleFiles(input){
    var files=Array.from(input.files);
    files.forEach(function(file){
        if(fichasImages.length>=10){toast('Máximo 10 imágenes',true);return;}
        var reader=new FileReader();
        reader.onload=function(e){
            var img=new Image();
            img.onload=function(){
                var canvas=document.createElement('canvas');
                var maxDim=1400;
                var w=img.naturalWidth,h=img.naturalHeight;
                if(w>maxDim||h>maxDim){
                    if(w>h){h=Math.round(h*maxDim/w);w=maxDim;}
                    else{w=Math.round(w*maxDim/h);h=maxDim;}
                }
                canvas.width=w;canvas.height=h;
                var ctx=canvas.getContext('2d');
                ctx.fillStyle='#fff';ctx.fillRect(0,0,w,h);
                ctx.drawImage(img,0,0,w,h);
                fichasImages.push({dataUrl:canvas.toDataURL('image/jpeg',0.88)});
                fichasRenderImagePreviews();
                fichasUpdatePreview();
            };
            img.src=e.target.result;
        };
        reader.readAsDataURL(file);
    });
    input.value='';
}

function fichasRenderImagePreviews(){
    var container=document.getElementById('fichas-img-previews');
    if(!fichasImages.length){
        container.innerHTML='<div class="fichas-img-empty">Sin imágenes. Subí al menos una foto.</div>';
        return;
    }
    container.innerHTML=fichasImages.map(function(img,idx){
        return '<div class="fichas-img-item">'+
            '<img src="'+img.dataUrl+'" style="width:100%;height:70px;object-fit:cover;border-radius:4px 4px 0 0;display:block">'+
            '<div style="display:flex;gap:2px;padding:3px;background:#F5F5F3;border-top:1px solid #E8E4DD">'+
                (idx>0?'<button onclick="fichasMoveImage('+idx+',-1)" class="fichas-img-btn" title="Subir">&#8593;</button>':'<span class="fichas-img-btn" style="background:none;color:#8B6F3A;font-size:7px;font-weight:700;letter-spacing:0.5px">PPAL</span>')+
                (idx<fichasImages.length-1?'<button onclick="fichasMoveImage('+idx+',1)" class="fichas-img-btn" title="Bajar">&#8595;</button>':'<span style="flex:1"></span>')+
                '<button onclick="fichasRemoveImage('+idx+')" class="fichas-img-btn" style="margin-left:auto;color:#C8453A" title="Eliminar">&#x2715;</button>'+
            '</div>'+
        '</div>';
    }).join('');
}

function fichasMoveImage(idx,dir){
    var newIdx=idx+dir;
    if(newIdx<0||newIdx>=fichasImages.length)return;
    var tmp=fichasImages[idx];fichasImages[idx]=fichasImages[newIdx];fichasImages[newIdx]=tmp;
    fichasRenderImagePreviews();fichasUpdatePreview();
}

function fichasRemoveImage(idx){
    fichasImages.splice(idx,1);
    fichasRenderImagePreviews();fichasUpdatePreview();
}

function fichasGetData(){
    return{
        tipo:document.getElementById('fi-tipo').value,
        ambientes:document.getElementById('fi-amb').value,
        dormitorios:document.getElementById('fi-dorm').value,
        banos:document.getElementById('fi-ban').value,
        supCubierta:document.getElementById('fi-sup-c').value,
        supTotal:document.getElementById('fi-sup-t').value,
        barrio:document.getElementById('fi-barrio').value,
        precio:document.getElementById('fi-precio').value,
        moneda:document.getElementById('fi-moneda').value,
        descripcion:document.getElementById('fi-desc').value
    };
}

async function fichasImportURL(){
    var url=document.getElementById('fi-url').value.trim();
    if(!url){toast('Pegá una URL primero',true);return;}
    var btn=document.getElementById('fi-url-btn');
    var status=document.getElementById('fi-url-status');
    btn.disabled=true;btn.textContent='Buscando...';
    status.textContent='Consultando datos de la propiedad...';status.style.color='#8B6F3A';
    try{
        var resp=await fetch(RAILWAY_SCRAPER_URL+'/property?url='+encodeURIComponent(url));
        if(!resp.ok){throw new Error('HTTP '+resp.status);}
        var data=await resp.json();
        if(data.error){throw new Error(data.error);}
        var filled=0;
        if(data.tipo){
            var tipoSel=document.getElementById('fi-tipo');
            var tipoVal=data.tipo.toLowerCase();
            for(var o of tipoSel.options){if(o.value.toLowerCase()===tipoVal){tipoSel.value=o.value;filled++;break;}}
        }
        if(data.barrio){document.getElementById('fi-barrio').value=data.barrio;filled++;}
        if(data.ambientes){
            var ambSel=document.getElementById('fi-amb');
            for(var o of ambSel.options){if(o.value===String(data.ambientes)){ambSel.value=o.value;filled++;break;}}
        }
        if(data.dormitorios){document.getElementById('fi-dorm').value=data.dormitorios;filled++;}
        if(data.banos){document.getElementById('fi-ban').value=data.banos;filled++;}
        if(data.sup_cubierta){document.getElementById('fi-sup-c').value=data.sup_cubierta;filled++;}
        if(data.sup_total){document.getElementById('fi-sup-t').value=data.sup_total;filled++;}
        if(data.precio){document.getElementById('fi-precio').value=data.precio;filled++;}
        if(data.moneda){document.getElementById('fi-moneda').value=data.moneda==='ARS'?'ARS':'USD';}
        if(data.descripcion){document.getElementById('fi-desc').value=data.descripcion;filled++;}
        fichasUpdatePreview();
        status.textContent=filled+' campos importados. Revisalos antes de generar el PDF.';status.style.color='#5a9a5a';
        toast('Datos importados correctamente');
    }catch(err){
        console.error(err);
        status.textContent='No se pudieron obtener los datos. Completá el formulario manualmente.';status.style.color='#C8453A';
        toast('No se pudo importar la propiedad',true);
    }finally{btn.disabled=false;btn.textContent='Importar';}
}

function fichasUpdatePreview(){
    var d=fichasGetData();
    var el=document.getElementById('fichas-preview-card');
    if(!el)return;
    var mainImg=fichasImages.length>0?fichasImages[0].dataUrl:null;
    var extraImgs=fichasImages.slice(1,5);
    var precioStr=d.precio?((d.moneda||'USD')+' '+Number(d.precio).toLocaleString('es-AR')):'—';
    var tipoCap=d.tipo?(d.tipo.charAt(0).toUpperCase()+d.tipo.slice(1)):'';
    var dataItems=[];
    if(d.ambientes)dataItems.push({l:'Amb.',v:d.ambientes});
    if(d.dormitorios)dataItems.push({l:'Dorm.',v:d.dormitorios});
    if(d.banos)dataItems.push({l:'Baños',v:d.banos});
    if(d.supCubierta)dataItems.push({l:'Cubierta',v:d.supCubierta+' m²'});
    if(d.supTotal)dataItems.push({l:'Total',v:d.supTotal+' m²'});
    var html='<div class="fp-header">'+
        '<div class="fp-brand">SANTIAGO FUNES</div>'+
        '<div class="fp-sub2">Real Estate</div>'+
        (d.barrio?'<div class="fp-barrio">'+esc(d.barrio.toUpperCase())+(tipoCap?' &nbsp;·&nbsp; '+esc(tipoCap):'')+'</div>':'')+
    '</div>';
    html+=mainImg?'<img src="'+mainImg+'" class="fp-main-img" alt="">':'<div class="fp-img-placeholder">Sin imagen principal</div>';
    if(dataItems.length){
        html+='<div class="fp-data-row">';
        dataItems.forEach(function(item){html+='<div class="fp-data-item"><div class="fp-data-val">'+esc(String(item.v))+'</div><div class="fp-data-label">'+esc(item.l)+'</div></div>';});
        html+='</div>';
    }
    html+='<div class="fp-price">'+esc(precioStr)+'</div>';
    if(d.descripcion)html+='<div class="fp-desc">'+esc(d.descripcion.substring(0,220))+(d.descripcion.length>220?'...':'')+'</div>';
    if(extraImgs.length){
        html+='<div class="fp-gallery">';
        extraImgs.forEach(function(img){html+='<img src="'+img.dataUrl+'" class="fp-gallery-img" alt="">';});
        html+='</div>';
    }
    html+='<div class="fp-footer">Martillero responsable: Juan Otero &nbsp;|&nbsp; Mat. N° 1966 &nbsp;|&nbsp; C.M.C.P. Azul</div>';
    el.innerHTML=html;
}

function fichasGeneratePDF(){
    if(!fichasImages.length){toast('Necesitás al menos una imagen',true);return;}
    var d=fichasGetData();
    var missingFields=[];
    if(!d.barrio)missingFields.push('barrio');
    if(!d.precio)missingFields.push('precio');
    if(missingFields.length){toast('Completá: '+missingFields.join(' y '),true);return;}
    if(!window.jspdf){toast('Cargando generador de PDF, esperá un momento...',true);return;}
    var btn=document.getElementById('fichas-pdf-btn');
    btn.disabled=true;btn.textContent='Generando...';
    try{
        var doc=new window.jspdf.jsPDF('p','mm','a4');
        var W=210,H=297,mg=12,y=0;
        // Header
        doc.setFillColor(26,26,46);doc.rect(0,0,W,36,'F');
        doc.setDrawColor(139,111,58);doc.setLineWidth(0.4);doc.line(mg,31,W-mg,31);
        doc.setTextColor(139,111,58);doc.setFont('helvetica','bold');doc.setFontSize(20);
        doc.text('SANTIAGO FUNES',mg,14);
        doc.setTextColor(180,160,120);doc.setFont('helvetica','normal');doc.setFontSize(9);
        doc.text('Real Estate',mg,21);
        if(d.barrio){
            var barrioTxt=d.barrio.toUpperCase()+(d.tipo?' — '+(d.tipo.charAt(0).toUpperCase()+d.tipo.slice(1)):'');
            doc.setFont('helvetica','bold');doc.setFontSize(8);doc.setTextColor(200,200,220);
            doc.text(barrioTxt,mg,28);
        }
        y=40;
        // Imagen principal
        var imgW=W-mg*2,mainImgH=85;
        if(fichasImages.length>0){
            try{doc.addImage(fichasImages[0].dataUrl,'JPEG',mg,y,imgW,mainImgH,'','FAST');}catch(e){}
        }
        y+=mainImgH+5;
        // Datos clave
        var dataItems=[];
        if(d.ambientes)dataItems.push({l:'Ambientes',v:d.ambientes});
        if(d.dormitorios)dataItems.push({l:'Dormitorios',v:d.dormitorios});
        if(d.banos)dataItems.push({l:'Baños',v:d.banos});
        if(d.supCubierta)dataItems.push({l:'Sup. Cubierta',v:d.supCubierta+' m²'});
        if(d.supTotal)dataItems.push({l:'Sup. Total',v:d.supTotal+' m²'});
        if(dataItems.length){
            doc.setFillColor(253,248,232);doc.setDrawColor(212,168,58);doc.setLineWidth(0.3);
            doc.roundedRect(mg,y,imgW,26,2,2,'FD');
            var cw=imgW/dataItems.length;
            dataItems.forEach(function(item,i){
                var cx=mg+cw*i+cw/2;
                doc.setFont('helvetica','bold');doc.setFontSize(13);doc.setTextColor(26,26,46);
                doc.text(String(item.v),cx,y+12,{align:'center'});
                doc.setFont('helvetica','normal');doc.setFontSize(6.5);doc.setTextColor(139,111,58);
                doc.text(item.l.toUpperCase(),cx,y+20,{align:'center'});
            });
            y+=30;
        }
        // Precio
        var precioStr=(d.moneda==='USD'?'USD ':'ARS ')+Number(d.precio).toLocaleString('es-AR');
        doc.setFillColor(26,26,46);doc.roundedRect(mg,y,imgW,15,2,2,'F');
        doc.setTextColor(139,111,58);doc.setFont('helvetica','bold');doc.setFontSize(16);
        doc.text(precioStr,W/2,y+10.5,{align:'center'});
        y+=20;
        // Descripcion
        if(d.descripcion){
            doc.setFont('helvetica','normal');doc.setFontSize(8.5);doc.setTextColor(60,60,80);
            var lines=doc.splitTextToSize(d.descripcion,imgW);
            var maxL=Math.floor((H-20-y)/4.2);
            if(lines.length>maxL)lines=lines.slice(0,maxL);
            doc.text(lines,mg,y+6);
            y+=lines.length*4.2+12;
        }
        // Galeria de fotos adicionales
        var extras=fichasImages.slice(1);
        if(extras.length&&y<H-40){
            doc.setFont('helvetica','bold');doc.setFontSize(7.5);doc.setTextColor(139,111,58);
            doc.text('GALERÍA DE FOTOS',mg,y);y+=5;
            var photoW=(imgW-4)/2,photoH=44;
            for(var i=0;i<extras.length;i++){
                if(y+photoH>H-18)break;
                var col=i%2;
                var px=mg+col*(photoW+4);
                try{doc.addImage(extras[i].dataUrl,'JPEG',px,y,photoW,photoH,'','FAST');}catch(e){}
                if(col===1||i===extras.length-1)y+=photoH+4;
            }
        }
        // Footer
        doc.setFillColor(26,26,46);doc.rect(0,H-15,W,15,'F');
        doc.setTextColor(180,160,120);doc.setFont('helvetica','normal');doc.setFontSize(7.5);
        doc.text('Martillero responsable: Juan Otero  |  Mat. N° 1966  |  C.M.C.P. Azul',W/2,H-8,{align:'center'});
        // Guardar
        var tipo=d.tipo||'propiedad';
        var barrio=(d.barrio||'tandil').toLowerCase().replace(/\s+/g,'-').replace(/[^a-z0-9-]/g,'');
        var fecha=new Date().toISOString().slice(0,10);
        doc.save('ficha-'+tipo+'-'+barrio+'-'+fecha+'.pdf');
        toast('PDF generado correctamente');
    }catch(err){
        console.error(err);toast('Error al generar PDF: '+err.message,true);
    }finally{btn.disabled=false;btn.textContent='Descargar PDF';}
}

var toastTO;
function toast(msg,err){var el=document.getElementById('toast');el.textContent=msg;el.className='toast show'+(err?' err':'');clearTimeout(toastTO);toastTO=setTimeout(function(){el.className='toast';},2500);}

document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeModal();closeIdeas();closeSesEdit();}});

// Auto-login
sb.auth.getSession().then(function(res){if(res.data&&res.data.session)enterApp();}).catch(function(){});
