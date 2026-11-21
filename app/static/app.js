
const API='/api';

function esc(value=''){
 return String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

let token=localStorage.getItem('ec_token')||'';
let me=null;
let activeView='inicio';

const $=s=>document.querySelector(s);
const $$=s=>document.querySelectorAll(s);

async function api(path,options={}){
 const headers={'Content-Type':'application/json',...(options.headers||{})};
 if(token)headers.Authorization=`Bearer ${token}`;

 const res=await fetch(API+path,{...options,headers});
 let data={};

 try{data=await res.json()}catch{}

 if(!res.ok){
  const detail=data.detail;
  let message='No fue posible completar la operación (HTTP '+res.status+').';

  if(typeof detail==='string'&&detail.trim()){
   message=detail;
  }else if(Array.isArray(detail)){
   const labels={
    full_name:'Nombre completo',
    phone:'Teléfono',
    password:'Contraseña',
    email:'Correo electrónico',
    address:'Dirección',
    generator_type:'Tipo de generador'
   };

   message=detail.map(item=>{
    const location=Array.isArray(item.loc)
     ?item.loc.filter(part=>part!=='body'&&part!=='query'&&part!=='path').slice(-1)[0]
     :'';

    const label=labels[location]||(location?String(location):'Dato');
    const reason=String(item.msg||'Dato no válido').replace(/^Value error,\s*/,'');
    return label+': '+reason;
   }).join(' · ');

  }else if(detail&&typeof detail==='object'&&typeof detail.message==='string'){
   message=detail.message;
  }

  throw new Error(message);
 }

 return data;
}

function toast(msg){
 const el=$('#toast');
 el.textContent=String(msg);
 el.classList.add('show');
 clearTimeout(window.toastTimer);
 window.toastTimer=setTimeout(()=>el.classList.remove('show'),8000);
}

function initials(name='EcoConecta'){
 return name.split(' ').slice(0,2).map(x=>x[0]).join('').toUpperCase();
}

function setUser(user){
 me=user;

 document.querySelectorAll('.community-only').forEach(x=>
  x.classList.toggle('hidden',!!user&&user.role!=='community')
 );

 $('#sideName').textContent=user?.name||'Invitado';
 $('#sideRole').textContent=roleName(user?.role);
 $('#avatar').textContent=initials(user?.name);
 $('#topAvatar').textContent=initials(user?.name);
 $('#logout').classList.toggle('hidden',!user);

 $$('.staff-only').forEach(x=>
  x.classList.toggle('hidden',!['coordinator_garden','coordinator_recycling','admin','collector_garden','collector_recycling'].includes(user?.role))
 );

 $$('.admin-only').forEach(x=>
  x.classList.toggle('hidden',user?.role!=='admin')
 );

 if(user?.role==='community'){
  $('#pointsBalance').innerHTML=`${user.points||0} <small>puntos</small>`;
 }

 const title=$('#view-operacion .page-title h1');
 const desc=$('#view-operacion .page-title p');
 const eyebrow=$('#view-operacion .page-title .eyebrow');

 if(title&&user){
  if(user.role==='admin'){
   title.textContent='Administración general';
   desc.textContent='Vista global de solicitudes, operación y seguimiento de todos los colectivos.';
   eyebrow.textContent='PANEL ADMINISTRATIVO';
  }else if(user.role.startsWith('coordinator_')){
   title.textContent='Panel de coordinación';
   desc.textContent='Gestiona las solicitudes y el equipo de tu colectivo.';
   eyebrow.textContent='GESTIÓN DEL COLECTIVO';
  }else{
   title.textContent='Mi ruta de recolección';
   desc.textContent='Consulta tus asignaciones y registra el avance de tus recolecciones.';
   eyebrow.textContent='PANEL DEL RECOLECTOR';
  }
 }
}

function roleName(role){
 return ({
  community:'Comunidad',
  coordinator_garden:'Coordinación · Huerteros',
  coordinator_recycling:'Coordinación · Recicladores',
  collector_garden:'Huertero',
  collector_recycling:'Reciclador',
  admin:'Administración'
 })[role]||'Comunidad';
}

function go(view){
 activeView=view;

 $$('.view').forEach(x=>x.classList.remove('active'));
 $('#view-'+view)?.classList.add('active');

 $$('.nav-item').forEach(x=>x.classList.toggle('active',x.dataset.view===view));

 $('#pageCrumb').textContent=({
  inicio:'Inicio',
  solicitar:'Solicitar recolección',
  solicitudes:'Mis solicitudes',
  educacion:'Educación ambiental',
  puntos:'Mis puntos',
  operacion:'Panel operativo'
 })[view]||'Inicio';

 $('#sidebar').classList.remove('open');

 if(view==='solicitudes'){
  loadRequests();
  loadNotifications();
 }

 if(view==='puntos')loadMe();

 if(view==='operacion'){
  loadOps();
  loadNotifications();
 }

 window.scrollTo({top:0,behavior:'smooth'});
}

$$('.nav-item').forEach(b=>b.addEventListener('click',()=>go(b.dataset.view)));

$$('[data-go]').forEach(b=>b.addEventListener('click',()=>{
 go(b.dataset.go);

 if(b.dataset.flow){
  const r=document.querySelector(`input[name="waste_type"][value="${b.dataset.flow}"]`);
  if(r)r.checked=true;
 }
}));

$('#mobileMenu').onclick=()=>$('#sidebar').classList.toggle('open');

$('#profileButton').onclick=()=>token
 ?toast(`Sesión: ${me?.name||'activa'}`)
 :openAuth();

$('#logout').onclick=()=>{
 token='';
 localStorage.removeItem('ec_token');
 setUser(null);
 toast('Sesión cerrada');
 go('inicio');
};

function openAuth(){
 if(token){
  toast('Ya tienes una sesión iniciada');
  return;
 }
 $('#authModal').classList.remove('hidden');
}

$('#closeAuth').onclick=()=>$('#authModal').classList.add('hidden');

$('#authModal').addEventListener('click',e=>{
 if(e.target.id==='authModal'){
  $('#authModal').classList.add('hidden');
 }
});

$$('[data-auth-tab]').forEach(b=>b.onclick=()=>{
 const reg=b.dataset.authTab==='register';

 $$('[data-auth-tab]').forEach(x=>
  x.classList.toggle('selected',x===b)
 );

 $('#loginForm').classList.toggle('hidden',reg);
 $('#registerForm').classList.toggle('hidden',!reg);
});

async function authSubmit(form,path){
 const data=Object.fromEntries(new FormData(form));

 if(data.email==='')data.email=null;

 try{
  const result=await api(path,{
   method:'POST',
   body:JSON.stringify(data)
  });

  token=result.access_token;
  localStorage.setItem('ec_token',token);

  setUser(result.user);

  $('#authModal').classList.add('hidden');
  form.reset();

  toast(`Bienvenido, ${result.user.name}`);

  if(['admin','coordinator_garden','coordinator_recycling','collector_garden','collector_recycling'].includes(result.user.role)){
   go('operacion');
   loadOps();
   loadNotifications();
  }else if(activeView==='solicitudes'){
   loadRequests();
   loadNotifications();
  }

  if(activeView==='operacion'){
   loadOps();
   loadNotifications();
  }

 }catch(e){
  toast(e.message);
 }
}

$('#loginForm').onsubmit=e=>{
 e.preventDefault();
 authSubmit(e.target,'/auth/login');
};

$('#registerForm').onsubmit=e=>{
 e.preventDefault();
 authSubmit(e.target,'/auth/register');
};

$('#requestForm').onsubmit=async e=>{
 e.preventDefault();

 if(!token){
  openAuth();
  toast('Inicia sesión o crea una cuenta para enviar tu solicitud');
  return;
 }

 const data=Object.fromEntries(new FormData(e.target));

 try{
  const result=await api('/requests',{
   method:'POST',
   body:JSON.stringify(data)
  });

  toast(`Solicitud ${result.code} enviada al colectivo correspondiente`);
  e.target.reset();
  go('solicitudes');
  loadNotifications();

 }catch(err){
  toast(err.message);
 }
};

function statusLabel(s){
 return ({
  recibida:'Recibida',
  en_revision:'En revisión',
  asignada:'Asignada',
  programada:'Programada',
  en_camino:'Vehículo en camino',
  recolectando:'Recolección en curso',
  recolectada:'Recolección finalizada',
  cancelada:'Cancelada'
 })[s]||s;
}

function requestRow(r,staff=false){
 const date=r.scheduled_date
  ?new Date(r.scheduled_date+'T00:00:00').toLocaleDateString('es-CO')
  :'Por confirmar';

 let actions='';
 const canCancel=!['recolectada','cancelada'].includes(r.status);

 if(staff){
  if(['coordinator_garden','coordinator_recycling','admin'].includes(me?.role)&&(r.status==='recibida'||r.status==='asignada')){
   actions+=`<button data-action="schedule" data-id="${r.id}" data-flow="${r.flow}">Asignar y programar</button>`;
  }

  if(['coordinator_garden','coordinator_recycling','admin'].includes(me?.role)&&canCancel){
   actions+=`<button data-action="cancel" data-id="${r.id}">Cancelar solicitud</button>`;
  }

  if(['collector_garden','collector_recycling','admin'].includes(me?.role)){
   if(r.status==='programada')actions+=`<button data-action="advance" data-status="en_camino" data-id="${r.id}">Iniciar recorrido</button>`;
   if(r.status==='en_camino')actions+=`<button data-action="advance" data-status="recolectando" data-id="${r.id}">Comenzar recolección</button>`;
   if(r.status==='recolectando')actions+=`<button data-action="collect" data-id="${r.id}">Finalizar y registrar evidencia</button>`;
  }

 }else if(me?.role==='community'&&canCancel){
  actions+=`<button data-action="cancel" data-id="${r.id}">Cancelar solicitud</button>`;
 }

 return `<div class="request-row">
  <div class="request-main">
   <b>${esc(r.code)} · ${r.flow==='organico'?'Orgánicos':'Reciclables'}</b>
   <small>${staff?esc((r.user_name||'Usuario')+' · '+(r.address||'')+' · '):''}${new Date(r.created_at).toLocaleDateString('es-CO')} ${r.scheduled_date?'· '+date+' '+(r.scheduled_time||''):''}${r.collector_name?' · Responsable: '+esc(r.collector_name):''}</small>
   <div class="ops-actions">${actions}<button data-action="history" data-id="${r.id}" class="secondary-action">Ver seguimiento</button></div>
   <div class="request-history hidden" id="history-${r.id}"></div>
  </div>
  <span class="status ${r.status}">${statusLabel(r.status)}</span>
 </div>`;
}


async function loadRequests(){
 const box = $('#requestList');
 if (!box) return;

 if (!token) {
  box.innerHTML = '<div class="empty-state">Inicia sesión para consultar tus solicitudes.</div>';
  return;
 }

 box.innerHTML = '<div class="empty-state">Cargando solicitudes...</div>';

 try {
  const rows = await api('/requests');

  if (!Array.isArray(rows)) {
   throw new Error('Respuesta inválida del servidor.');
  }

  box.innerHTML = rows.length
   ? rows.map(r => requestRow(r)).join('')
   : '<div class="empty-state">Todavía no tienes solicitudes registradas.</div>';

 } catch (e) {
  const message = e?.message || 'Error desconocido';

  if (/401|Sesión no válida/i.test(message)) {
   token = '';
   localStorage.removeItem('ec_token');
   setUser(null);
   box.innerHTML = '<div class="empty-state">Tu sesión venció. Inicia sesión nuevamente.</div>';
  } else {
   box.innerHTML = `
    <div class="empty-state">
     <b>No fue posible cargar tus solicitudes.</b>
     <p>${esc(message)}</p>
     <button class="btn btn-light btn-small" id="retryRequestsInline">
      Reintentar
     </button>
    </div>`;

   $('#retryRequestsInline')?.addEventListener('click', loadRequests);
  }

  toast('Error al consultar solicitudes: ' + message);
 }
}

$('#refreshRequests').onclick=loadRequests;

async function loadMe(){
 if(!token){
  openAuth();
  return;
 }

 try{
  me=await api('/me');
  setUser(me);
  $('#pointsBalance').innerHTML=`${me.points||0} <small>puntos</small>`;
 }catch(e){
  toast(e.message);
 }
}

async function loadOps(){
 if(!token){
  openAuth();
  return;
 }

 try{
  const [stats,rows]=await Promise.all([
   api('/dashboard'),
   api('/requests')
  ]);

  $('#statsGrid').innerHTML=[
   ['Solicitudes',stats.total,'En el colectivo'],
   ['Por revisar',stats.recibidas,'Pendientes'],
   ['Programadas',stats.programadas,'Con fecha y responsable'],
   ['En camino',stats.en_camino||0,'Vehículos en ruta'],
   ['En recolección',stats.recolectando||0,'Trabajo en curso'],
   ['Finalizadas',stats.recolectadas,`${stats.kg} kg registrados`]
  ].map(([a,b,c])=>`<div class="stat-card"><small>${a}</small><b>${b}</b><span>${c}</span></div>`).join('');

  $('#opsList').innerHTML=rows.length
   ?rows.map(r=>requestRow(r,true)).join('')
   :'<div class="empty-state">No hay solicitudes en esta bandeja.</div>';

  if(me?.role==='admin')await loadAdminUsers();

 }catch(e){
  toast(e.message);
 }
}

$('#refreshOps').onclick=loadOps;

const adminRoleOptions=[
 ['community','Ciudadano'],
 ['coordinator_garden','Coordinador orgánico'],
 ['coordinator_recycling','Coordinador reciclaje'],
 ['collector_garden','Recolector orgánico'],
 ['collector_recycling','Recolector reciclaje'],
 ['admin','Administrador']
];

async function loadAdminUsers(){
 if(me?.role!=='admin')return;

 try{
  const users=await api('/admin/users');

  $('#adminUsersList').innerHTML=users.map(u=>`
   <div class="admin-user-row">
    <div class="admin-user-info">
     <b>${esc(u.name)}</b>
     <small>${esc(u.phone)} · ${esc(u.email||'Sin correo')} · ${u.active?'Activa':'Desactivada'}</small>
    </div>
    <select aria-label="Rol de ${esc(u.name)}" data-admin-role="${u.id}">
     ${adminRoleOptions.map(([value,label])=>`<option value="${value}" ${u.role===value?'selected':''}>${label}</option>`).join('')}
    </select>
    <label class="admin-active-toggle">
     <input type="checkbox" data-admin-active="${u.id}" ${u.active?'checked':''}> Activa
    </label>
    <button class="btn btn-light btn-small" data-admin-save="${u.id}">Guardar</button>
   </div>
  `).join('')||'<div class="empty-state">No hay usuarios.</div>';

 }catch(e){
  $('#adminUsersList').innerHTML=`<div class="empty-state">${esc(e.message)}</div>`;
 }
}

$('#refreshAdminUsers')?.addEventListener('click',loadAdminUsers);

$('#adminUsersList')?.addEventListener('click',async e=>{
 const button=e.target.closest('[data-admin-save]');
 if(!button)return;

 const id=button.dataset.adminSave;
 const role=$(`[data-admin-role="${id}"]`).value;
 const active=$(`[data-admin-active="${id}"]`).checked;

 try{
  await api(`/admin/users/${id}`,{
   method:'PATCH',
   body:JSON.stringify({role,active})
  });

  toast('Usuario actualizado correctamente');
  await loadAdminUsers();

 }catch(err){
  toast(err.message);
 }
});

async function loadNotifications(){
 if(!token)return;

 try{
  const rows=await api('/notifications');

  const markup=rows.length
   ?rows.map(n=>`
    <article class="notification-item ${n.read?'read':''}">
     <div>
      <b>${esc(n.title)}</b>
      <p>${esc(n.message)}</p>
      <small>${new Date(n.created_at).toLocaleString('es-CO')}</small>
     </div>
     <button data-notification-read="${n.id}" ${n.read?'disabled':''}>${n.read?'Leída':'Marcar leída'}</button>
    </article>
   `).join('')
   :'<div class="empty-state">No hay notificaciones para tu usuario.</div>';

  ['#staffNotifications','#citizenNotifications'].forEach(selector=>{
   const box=$(selector);
   if(box)box.innerHTML=markup;
  });

 }catch(e){
  toast(e.message);
 }
}

async function showHistory(id){
 const target=$(`#history-${id}`);

 if(!target)return;

 if(!target.classList.contains('hidden')){
  target.classList.add('hidden');
  return;
 }

 try{
  const data=await api(`/requests/${id}/history`);
  const events=Array.isArray(data)?data:(data.events||[]);
  const evidence=data.evidence||[];

  target.innerHTML=`
   <div class="timeline">
    ${events.map(ev=>`
     <div class="timeline-item">
      <b>${statusLabel(ev.status)}</b>
      <p>${esc(ev.detail||'')}</p>
      <small>${new Date(ev.created_at).toLocaleString('es-CO')}</small>
     </div>
    `).join('')}
   </div>
   ${evidence.map(ev=>`
    <div class="evidence-card">
     <img data-evidence-url="${esc(ev.photo_url)}" alt="Evidencia de recolección">
     <div>
      <b>${esc(ev.weight_kg)} kg · ${esc(ev.material_type)}</b>
      <small>${new Date(ev.created_at).toLocaleString('es-CO')}</small>
      ${ev.notes?`<p>${esc(ev.notes)}</p>`:''}
     </div>
    </div>
   `).join('')}
  `;

  target.classList.remove('hidden');

  for(const img of target.querySelectorAll('[data-evidence-url]')){
   const res=await fetch(img.dataset.evidenceUrl,{
    headers:{Authorization:`Bearer ${token}`}
   });

   if(res.ok){
    const blob=await res.blob();
    img.src=URL.createObjectURL(blob);
   }
  }

 }catch(e){
  toast(e.message);
 }
}

$('#opsList').addEventListener('click',async e=>{
 const btn=e.target.closest('button[data-action]');
 if(!btn)return;

 const id=btn.dataset.id;

 try{
  if(btn.dataset.action==='history'){
   await showHistory(id);
   return;
  }

  if(btn.dataset.action==='cancel'){
   if(!confirm('¿Confirmas que deseas cancelar esta solicitud?'))return;

   await api(`/requests/${id}/cancel`,{method:'POST'});
   toast('Solicitud cancelada y responsables notificados');
   loadOps();
   loadRequests();
   loadNotifications();
   return;
  }

  if(btn.dataset.action==='schedule'){
   const collectors=await api('/collectors');

   if(!collectors.length){
    toast('No hay recolectores configurados para este colectivo');
    return;
   }

   const options=collectors.map(c=>`${c.id}: ${c.name}`).join('\n');
   const chosen=prompt('Escribe el ID del recolector:\n'+options,String(collectors[0].id));

   if(!chosen)return;

   const collector=collectors.find(c=>c.id===Number(chosen));

   if(!collector){
    toast('ID de recolector no válido');
    return;
   }

   const day=prompt('Fecha de recolección (AAAA-MM-DD):');
   if(!day)return;

   const hour=prompt('Hora (HH:MM):','09:00');
   if(!hour)return;

   await api(`/requests/${id}/schedule`,{
    method:'POST',
    body:JSON.stringify({
     collector_id:collector.id,
     scheduled_date:day,
     scheduled_time:hour
    })
   });

   toast('Programación registrada y recolector notificado');

  }else if(btn.dataset.action==='advance'){
   await api(`/requests/${id}/advance`,{
    method:'POST',
    body:JSON.stringify({status:btn.dataset.status})
   });

   toast(btn.dataset.status==='en_camino'
    ?'Recorrido iniciado'
    :'Recolección iniciada');

  }else if(btn.dataset.action==='collect'){
   const weight=prompt('Peso recolectado en kilogramos:');
   if(!weight)return;

   const material=prompt('Tipo de material: organico, papel_carton, plasticos, vidrio, metales o mixto:','mixto');
   if(!material)return;

   const picker=document.createElement('input');
   picker.type='file';
   picker.accept='image/jpeg,image/png,image/webp';

   picker.onchange=async()=>{
    const photo=picker.files[0];
    if(!photo)return;

    const notes=prompt('Observaciones (opcional):','')||'';
    const body=new FormData();

    body.append('weight_kg',weight);
    body.append('material_type',material);
    body.append('photo',photo);
    body.append('notes',notes);

    const headers={};
    if(token)headers.Authorization=`Bearer ${token}`;

    const res=await fetch(API+`/requests/${id}/collect`,{
     method:'POST',
     headers,
     body
    });

    const result=await res.json();

    if(!res.ok){
     throw new Error(result.detail||'No fue posible guardar la evidencia');
    }

    toast('Recolección finalizada; evidencia registrada y puntos acreditados');
    loadOps();
    loadNotifications();
   };

   picker.click();
   return;
  }

  loadOps();
  loadNotifications();

 }catch(err){
  toast(err.message);
 }
});

document.addEventListener('click',async e=>{
 const b=e.target.closest('[data-notification-read]');
 if(!b)return;

 try{
  await api(`/notifications/${b.dataset.notificationRead}/read`,{
   method:'POST'
  });

  loadNotifications();

 }catch(err){
  toast(err.message);
 }
});

$('#requestList').addEventListener('click',async e=>{
 const b=e.target.closest('button[data-action]');
 if(!b)return;

 try{
  if(b.dataset.action==='history'){
   await showHistory(b.dataset.id);
   return;
  }

  if(b.dataset.action==='cancel'){
   if(!confirm('¿Confirmas que deseas cancelar esta solicitud?'))return;

   await api(`/requests/${b.dataset.id}/cancel`,{method:'POST'});
   toast('Solicitud cancelada correctamente');
   await loadRequests();
   await loadNotifications();
  }

 }catch(err){
  toast(err.message);
 }
});

async function boot(){
 try{
  if(token){
   const user=await api('/me');
   setUser(user);
  }else{
   setUser(null);
  }
 }catch{
  token='';
  localStorage.removeItem('ec_token');
  setUser(null);
 }
}

boot();

// Chatbot libre: conversación breve en memoria de la pestaña, enviada al backend.
const chatHistory=[];
const chatPanel=$('#chatPanel');

$('#chatLauncher')?.addEventListener('click',()=>{
 chatPanel.classList.toggle('hidden');
 $('#chatLauncher').setAttribute('aria-expanded',String(!chatPanel.classList.contains('hidden')));
 if(!chatPanel.classList.contains('hidden'))$('#chatInput').focus();
});

$('#chatClose')?.addEventListener('click',()=>{
 chatPanel.classList.add('hidden');
 $('#chatLauncher').setAttribute('aria-expanded','false');
});

function appendChat(role,text){
 const node=document.createElement('div');
 node.className=`chat-bubble ${role}`;
 node.textContent=text;
 $('#chatMessages').appendChild(node);
 $('#chatMessages').scrollTop=$('#chatMessages').scrollHeight;
}

$('#chatForm')?.addEventListener('submit',async e=>{
 e.preventDefault();

 const input=$('#chatInput');
 const question=input.value.trim();

 if(!question)return;

 appendChat('user',question);
 chatHistory.push({role:'user',content:question});

 input.value='';
 $('#chatSend').disabled=true;
 $('#chatSend').textContent='…';

 try{
  const result=await api('/chat',{
   method:'POST',
   body:JSON.stringify({messages:chatHistory.slice(-10)})
  });

  const answer=result.answer||'No recibí una respuesta.';

  appendChat('bot',answer);
  chatHistory.push({role:'assistant',content:answer});

 }catch(err){
  appendChat(
   'bot',
   err.message==='El asistente inteligente todavía no está configurado. Puedes comunicarte con el equipo de EcoConecta.'
    ?err.message
    :'No pude procesar la pregunta en este momento. Inténtalo nuevamente o contacta al equipo de EcoConecta.'
  );

 }finally{
  $('#chatSend').disabled=false;
  $('#chatSend').textContent='Enviar';
  input.focus();
 }
});
