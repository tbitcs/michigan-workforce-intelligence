'use strict';
let token = '', actor = '', role = '', ownSignals = [];
const byId = id => document.getElementById(id);
const node = (tag, text) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; return n; };
function message(text) { byId('message').textContent = text; }
async function api(path, method = 'GET', body) {
  const response = await fetch('/api/' + path, {method, headers: {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}, body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store', credentials: 'omit'});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error + (data.fields ? ': ' + data.fields.map(f => f.field).join(', ') : ''));
  return data;
}
function action(label, fn) { const b = node('button', label); b.type = 'button'; b.addEventListener('click', async () => { b.disabled = true; try { await fn(); message('Saved.'); await refresh(); } catch (e) { message(e.message); } finally { b.disabled = false; } }); return b; }
function input(form, label, name, type = 'text', value = '') { const l = node('label', label), i = node('input'); i.name = name; i.type = type; i.value = value; i.required = true; l.append(i); form.append(l); return i; }
function card(parent, title, lines) { const c = node('article'); c.className = 'card'; c.append(node('h3', title)); for (const line of lines) c.append(node('p', line)); parent.append(c); return c; }
async function refresh() {
  const [s,t] = await Promise.all([api('signals'), api('transitions')]); ownSignals = s.signals;
  byId('signals').replaceChildren(); byId('transitions').replaceChildren(); byId('matches').replaceChildren();
  for (const signal of s.signals) {
    const c = card(byId('signals'), `${signal.kind} · ${signal.occupation} · ${signal.headcount} roles`, [`County ${signal.county} · $${signal.minimum_hourly_wage}/hour · ${signal.hours_per_week} hours/week`, `${signal.earliest} to ${signal.latest} · expires ${signal.expires}`, `Sharing: ${signal.share_with_network && !signal.closed ? 'network opted in' : 'private / closed'} · ${signal.confidence}`, `Skills: ${signal.skills.join(', ')}`, `Reference: ${signal.id}`]);
    if (!signal.closed) c.append(action('Close / withdraw sharing', () => api('signals/' + signal.id, 'DELETE')));
  }
  if (!s.signals.length) byId('signals').append(node('p', 'No signals yet.'));
  if (role === 'employer') {
    const data = await api('matches');
    for (const match of data.matches) {
      const job = match.hiring;
      const c = card(byId('matches'), `${match.employer} · ${job.occupation}`, [`${job.headcount} roles · $${job.minimum_hourly_wage}/hour · ${job.hours_per_week} hours/week`, `${job.earliest} to ${job.latest}`, `Shared skills: ${match.shared_skills.join(', ') || 'none recorded'}`, `Requirements to review: ${match.remaining_requirements.join(', ') || 'verify with employer'}`, match.reason]);
      const f = node('form'); input(f, 'People proposed', 'headcount', 'number', '1').min = '1';
      const consent = input(f, 'I attest that each proposed worker voluntarily consented; consent evidence is held outside this pilot.', 'consent', 'checkbox');
      f.append(node('button', 'Propose voluntary transition')); f.addEventListener('submit', async e => { e.preventDefault(); try { await api('transitions', 'POST', {surplus_id:match.surplus_id,hiring_id:job.id,headcount:Number(f.elements.headcount.value),worker_consent_attested:consent.checked}); message('Proposal recorded. No outreach or placement was performed.'); await refresh(); } catch (err) {message(err.message);} }); c.append(f);
    }
    if (!data.matches.length) byId('matches').append(node('p', 'No currently compatible shared signals. This does not mean no jobs exist.'));
  }
  for (const transition of t.transitions) renderTransition(transition);
  if (role === 'operator') {
    const data = await api('employers'); byId('employers').replaceChildren();
    for (const employer of data.employers) { const c = card(byId('employers'), employer.name, [`${employer.active ? 'Active' : 'Revoked'} · expires ${employer.expires}`, employer.id]); if (employer.active) c.append(action('Revoke access', () => api('employers/' + employer.id, 'DELETE'))); }
  }
}
function renderTransition(t) {
  const c = card(byId('transitions'), `${t.status} · ${t.headcount} people`, [`Reference: ${t.id}`, `Surplus ${t.surplus_id} → hiring ${t.hiring_id}`, 'Worker consent: employer-attested; not independently verified.']);
  if (t.offer) c.append(node('p', `Confirmed offer: ${t.offer.start_date}, $${t.offer.hourly_wage}/hour, ${t.offer.hours_per_week} hours/week; benefits confirmed by employer.`));
  if (t.actual_start_date) c.append(node('p', `Employer-reported start: ${t.actual_start_date}`));
  if (actor === t.receiving_tenant && t.status === 'proposed') {
    const f = node('form'), job = ownSignals.find(s => s.id === t.hiring_id);
    input(f, 'Confirmed start date', 'start_date', 'date'); input(f, 'Confirmed hourly wage', 'hourly_wage', 'number', job ? String(job.minimum_hourly_wage) : '').step = '0.01'; input(f, 'Confirmed weekly hours', 'hours_per_week', 'number', job ? String(job.hours_per_week) : ''); const benefits = input(f, 'I confirmed benefits and the offer with the participants.', 'benefits', 'checkbox');
    f.append(node('button', 'Confirm receiving offer')); f.addEventListener('submit', async e => { e.preventDefault(); try { await api('transitions/' + t.id, 'POST', {action:'accept',start_date:f.elements.start_date.value,hourly_wage:Number(f.elements.hourly_wage.value),hours_per_week:Number(f.elements.hours_per_week.value),benefits_confirmed:benefits.checked}); await refresh(); message('Receiving offer recorded.'); } catch (err) {message(err.message);} }); c.append(f, action('Decline', () => api('transitions/' + t.id, 'POST', {action:'decline'})));
  }
  if ([t.tenant,t.receiving_tenant].includes(actor) && ['proposed','accepted'].includes(t.status)) c.append(action('Withdraw transition / consent', () => api('transitions/' + t.id, 'POST', {action:'withdraw'})));
  if (actor === t.receiving_tenant && t.status === 'accepted') { const f = node('form'); input(f,'Actual start date confirmed by employer','actual_start_date','date'); f.append(node('button','Record reported start')); f.addEventListener('submit',async e=>{e.preventDefault();try{await api('transitions/'+t.id,'POST',{action:'started',actual_start_date:f.elements.actual_start_date.value});await refresh();message('Employer-reported start recorded.');}catch(err){message(err.message);}});c.append(f); }
}
byId('login-form').addEventListener('submit', async e => { e.preventDefault(); token = byId('token').value; byId('token').value = ''; try { const me = await api('me'); actor = me.actor; role = me.role; byId('identity').textContent = role === 'operator' ? 'Operator workspace' : 'Employer workspace'; byId('login').hidden = true; byId('workspace').hidden = false; byId('operator').hidden = role !== 'operator'; byId('employer').hidden = role !== 'employer'; byId('match-section').hidden = role !== 'employer'; await refresh(); message(''); } catch (err) { token = ''; message(err.message); } });
byId('logout').addEventListener('click', () => location.reload());
byId('refresh').addEventListener('click', () => refresh().catch(err => message(err.message)));
byId('audit').addEventListener('click', async () => { try { const d = await api('audit'); message(`Audit valid: ${d.valid}; ${d.events} events.`); } catch (err) {message(err.message);} });
byId('employer-form').addEventListener('submit', async e => {e.preventDefault();const f=e.target;try{const d=await api('employers','POST',{name:f.elements.name.value,credential_days:Number(f.elements.credential_days.value),identity_verified:f.elements.identity_verified.checked});byId('new-credential').textContent=`${d.name}\nEmployer ID: ${d.id}\nOne-time access key: ${d.credential}\n${d.notice}`;f.reset();await refresh();message('Credential created; distribute through your agreed secure channel.');}catch(err){message(err.message);}});
byId('signal-form').addEventListener('submit',async e=>{e.preventDefault();const f=e.target;const d=Object.fromEntries(new FormData(f));for(const key of ['headcount','minimum_hourly_wage','hours_per_week'])d[key]=Number(d[key]);d.skills=d.skills.split(',').map(s=>s.trim()).filter(Boolean);d.share_with_network=f.elements.share_with_network.checked;try{await api('signals','POST',d);f.reset();await refresh();message('Signal saved.');}catch(err){message(err.message);}});
