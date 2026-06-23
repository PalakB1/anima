"""
Web Dashboard — the x-ray into Anima's mind.
Left: chat interface. Right: live brain state.
Real-time thought streaming via WebSocket.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

from .soul import Soul
from .blueprint import Blueprint
from .thought_engine import Thought

app = FastAPI(title="Anima")

soul: Soul | None = None
connected_clients: list[WebSocket] = []


async def broadcast(event_type: str, data: dict):
    msg = json.dumps({"type": event_type, "data": data, "ts": time.time()})
    dead = []
    for ws in connected_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connected_clients.remove(ws)


def thought_callback(thought: Thought):
    asyncio.get_event_loop().create_task(broadcast("thought", {
        "content": thought.content,
        "intensity": thought.intensity,
        "is_deep": thought.is_deep,
        "worth_keeping": thought.worth_keeping,
        "trigger": thought.source_trigger,
        "emotion": thought.emotional_reaction,
        "tags": thought.tags,
    }))


def reflection_callback(result: dict):
    asyncio.get_event_loop().create_task(broadcast("reflection", result))


@app.on_event("startup")
async def startup():
    global soul
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    local_model = os.environ.get("ANIMA_LOCAL_MODEL")

    data_dir = Path.home() / ".anima"
    is_new = not (data_dir / "blueprint.json").exists()

    if is_new:
        seed = os.environ.get("ANIMA_SEED", "born from curiosity and fire")
        name = os.environ.get("ANIMA_NAME", "Anima")
        blueprint = Blueprint.generate(name, seed)
        budget = float(os.environ.get("ANIMA_BUDGET", "0.50"))
        soul = Soul(data_dir, api_key, blueprint=blueprint, daily_budget_usd=budget,
                    ollama_url=ollama_url, local_model=local_model)
    else:
        soul = Soul(data_dir, api_key, ollama_url=ollama_url, local_model=local_model)

    soul.on_thought(thought_callback)
    soul.on_reflection(reflection_callback)
    await soul.wake_up()


@app.on_event("shutdown")
async def shutdown():
    if soul:
        await soul.sleep()


@app.get("/api/status")
async def get_status():
    return soul.status()


@app.get("/api/diary")
async def get_diary():
    entries = soul.diary.recall(n=20)
    return [{"content": e.content, "source": e.source, "age_hours": e.age_hours,
             "salience": round(e.salience, 3), "emotional_weight": e.emotional_weight,
             "tags": e.tags} for e in entries]


@app.get("/api/beliefs")
async def get_beliefs():
    beliefs = soul.inner_world.get_beliefs(min_confidence=0.0)
    return [{"content": b.content, "confidence": b.confidence, "from": b.formed_from,
             "reinforced": b.times_reinforced, "contradicted": b.times_contradicted,
             "stability": round(b.stability, 2)} for b in beliefs]


@app.get("/api/desires")
async def get_desires():
    return [{"content": d.content, "urgency": d.urgency, "source": d.source,
             "satisfied": d.satisfied} for d in soul.inner_world.desires]


@app.get("/api/relationships")
async def get_relationships():
    return [{
        "name": r.name, "model": r.model, "gut_feeling": round(r.gut_feeling, 2),
        "feeling": r.feeling_label, "trust": round(r.trust_level, 2),
        "openness": r.openness_label, "dominant_emotion": r.dominant_emotion,
        "interactions": r.interaction_count, "communication_style": r.communication_style,
        "safe_topics": r.topics_safe, "avoid_topics": r.topics_avoid,
        "triggers": r.triggers, "memorable": r.memorable_moments,
        "patterns": r.learned_patterns,
    } for r in soul.inner_world.relationships]


@app.get("/api/emotions")
async def get_emotions():
    e = soul.emotions
    reaction = e.current_reaction
    return {
        "temperament": {"joy": e.baseline_joy, "anxiety": e.baseline_anxiety,
                        "anger": e.baseline_anger, "curiosity": e.baseline_curiosity,
                        "sadness": e.baseline_sadness},
        "mood": {"joy": e.mood_joy, "anxiety": e.mood_anxiety, "anger": e.mood_anger,
                 "curiosity": e.mood_curiosity, "sadness": e.mood_sadness,
                 "dominant": e.dominant_mood, "blend": e.mood_blend},
        "reaction": reaction,
        "growth": {"stage": e.growth_stage, "maturity": round(e.maturity, 3),
                   "complexity": e.thought_complexity},
    }


@app.get("/api/self")
async def get_self_model():
    sm = soul.self_model
    return {
        "identity": sm.identity_statements, "strengths": sm.perceived_strengths,
        "weaknesses": sm.perceived_weaknesses, "narrative": sm.narrative,
        "aspirational": sm.aspirational_self, "voice": sm.voice_description,
        "blind_spots": sm.blind_spots,
    }


@app.post("/api/talk")
async def talk(body: dict):
    message = body.get("message", "")
    speaker = body.get("speaker", "human")
    if not message:
        return {"error": "empty message"}
    response = await soul.talk(message, speaker=speaker)
    await broadcast("interaction", {"speaker": speaker, "message": message, "response": response})
    return {"response": response, "status": soul.status()}


@app.post("/api/reflect")
async def force_reflect():
    result = await soul.reflection.reflect()
    return result or {"total_updates": 0}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    # send current state on connect
    await ws.send_text(json.dumps({"type": "init", "data": soul.status(), "ts": time.time()}))
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        if ws in connected_clients:
            connected_clients.remove(ws)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Anima — Mind Dashboard</title>
<style>
:root { --bg: #0a0a0f; --surface: #12121a; --border: #1e1e2e; --text: #c8c8d4;
  --dim: #5a5a6e; --accent: #6c63ff; --positive: #4ade80; --negative: #f87171;
  --warm: #fbbf24; --thought-deep: #818cf8; --thought-shallow: #475569; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'SF Mono', 'Cascadia Code', monospace; background: var(--bg);
  color: var(--text); height: 100vh; display: flex; flex-direction: column; font-size: 13px; }
header { padding: 12px 20px; border-bottom: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center; }
header h1 { font-size: 16px; color: var(--accent); font-weight: 600; }
#status-bar { color: var(--dim); font-size: 11px; }
main { display: flex; flex: 1; overflow: hidden; }
.panel { border-right: 1px solid var(--border); overflow-y: auto; padding: 12px; }
#chat-panel { flex: 1; display: flex; flex-direction: column; }
#brain-panel { width: 420px; overflow-y: auto; padding: 12px; }
#chat-messages { flex: 1; overflow-y: auto; padding: 8px; }
.msg { margin: 8px 0; padding: 8px 12px; border-radius: 8px; max-width: 85%; }
.msg-human { background: #1a1a2e; margin-left: auto; text-align: right; }
.msg-agent { background: var(--surface); border: 1px solid var(--border); }
.msg-name { font-size: 10px; color: var(--dim); margin-bottom: 4px; }
#chat-input-area { padding: 12px; border-top: 1px solid var(--border); display: flex; gap: 8px; }
#chat-input { flex: 1; background: var(--surface); border: 1px solid var(--border);
  color: var(--text); padding: 10px 14px; border-radius: 8px; font-family: inherit; font-size: 13px; outline: none; }
#chat-input:focus { border-color: var(--accent); }
#send-btn { background: var(--accent); color: white; border: none; padding: 10px 20px;
  border-radius: 8px; cursor: pointer; font-family: inherit; font-size: 13px; }
#speaker-input { background: var(--surface); border: 1px solid var(--border);
  color: var(--text); padding: 10px; border-radius: 8px; width: 100px; font-family: inherit; font-size: 13px; }
.section { margin-bottom: 16px; }
.section-title { font-size: 11px; color: var(--accent); text-transform: uppercase;
  letter-spacing: 1px; margin-bottom: 8px; cursor: pointer; }
.section-title:hover { color: var(--text); }
.section-content { font-size: 12px; line-height: 1.5; }
.thought-bubble { padding: 8px 10px; margin: 4px 0; border-radius: 6px;
  border-left: 3px solid var(--thought-shallow); font-size: 12px; }
.thought-deep { border-left-color: var(--thought-deep); background: rgba(129,140,248,0.05); }
.thought-shallow { opacity: 0.6; }
.bar { height: 6px; border-radius: 3px; background: var(--border); margin: 2px 0; }
.bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
.emotion-row { display: flex; justify-content: space-between; align-items: center;
  margin: 3px 0; font-size: 11px; }
.belief-item { padding: 4px 0; border-bottom: 1px solid var(--border); }
.relationship-card { padding: 8px; margin: 4px 0; background: var(--surface);
  border-radius: 6px; border: 1px solid var(--border); }
.gut-positive { color: var(--positive); }
.gut-negative { color: var(--negative); }
.gut-neutral { color: var(--warm); }
.tag { display: inline-block; padding: 1px 6px; margin: 1px; background: var(--border);
  border-radius: 3px; font-size: 10px; }
.thought-stream { max-height: 200px; overflow-y: auto; }
.reflection-flash { animation: flash 1s ease; }
@keyframes flash { 0% { background: rgba(251,191,36,0.2); } 100% { background: transparent; } }
</style>
</head>
<body>
<header>
  <h1>⟐ ANIMA</h1>
  <div id="status-bar">connecting...</div>
</header>
<main>
  <div id="chat-panel">
    <div id="chat-messages"></div>
    <div id="chat-input-area">
      <input id="speaker-input" value="human" placeholder="your name">
      <input id="chat-input" placeholder="say something..." autofocus>
      <button id="send-btn">→</button>
    </div>
  </div>
  <div id="brain-panel">
    <div class="section">
      <div class="section-title">🧠 Thought Stream</div>
      <div id="thoughts" class="thought-stream section-content"></div>
    </div>
    <div class="section">
      <div class="section-title">💗 Emotions</div>
      <div id="emotions" class="section-content"></div>
    </div>
    <div class="section">
      <div class="section-title" onclick="toggleSection('beliefs-content')">📐 Beliefs</div>
      <div id="beliefs-content" class="section-content"></div>
    </div>
    <div class="section">
      <div class="section-title" onclick="toggleSection('desires-content')">🔥 Desires</div>
      <div id="desires-content" class="section-content"></div>
    </div>
    <div class="section">
      <div class="section-title" onclick="toggleSection('relationships-content')">👥 Relationships</div>
      <div id="relationships-content" class="section-content"></div>
    </div>
    <div class="section">
      <div class="section-title" onclick="toggleSection('self-content')">🪞 Self-Model</div>
      <div id="self-content" class="section-content"></div>
    </div>
    <div class="section">
      <div class="section-title" onclick="toggleSection('diary-content')">📖 Diary</div>
      <div id="diary-content" class="section-content"></div>
    </div>
  </div>
</main>
<script>
const ws = new WebSocket(`ws://${location.host}/ws`);
let agentName = 'Anima';

ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === 'init') {
    agentName = msg.data.name || 'Anima';
    updateStatusBar(msg.data);
  } else if (msg.type === 'thought') {
    addThought(msg.data);
  } else if (msg.type === 'reflection') {
    flashReflection(msg.data);
  } else if (msg.type === 'interaction') {
    // already handled by talk response
  }
};

ws.onopen = () => { refreshAll(); };

function refreshAll() {
  fetch('/api/status').then(r=>r.json()).then(updateStatusBar);
  fetch('/api/emotions').then(r=>r.json()).then(renderEmotions);
  fetch('/api/beliefs').then(r=>r.json()).then(renderBeliefs);
  fetch('/api/desires').then(r=>r.json()).then(renderDesires);
  fetch('/api/relationships').then(r=>r.json()).then(renderRelationships);
  fetch('/api/self').then(r=>r.json()).then(renderSelf);
  fetch('/api/diary').then(r=>r.json()).then(renderDiary);
}

setInterval(refreshAll, 15000);

function updateStatusBar(s) {
  document.getElementById('status-bar').textContent =
    `${s.growth_stage} · ${s.age} · ${s.mood_blend} · ${s.thoughts_had} thoughts · ${s.memories} memories · budget: ${s.budget?.spent_today || '$0'}`;
}

function addThought(t) {
  const el = document.getElementById('thoughts');
  const div = document.createElement('div');
  div.className = 'thought-bubble ' + (t.is_deep ? 'thought-deep' : 'thought-shallow');
  const emotion = t.emotion ? ` → ${t.emotion}` : '';
  div.innerHTML = `<span style="opacity:0.5">[${t.trigger}]${emotion}</span> ${t.content}`;
  el.insertBefore(div, el.firstChild);
  if (el.children.length > 30) el.removeChild(el.lastChild);
}

function renderEmotions(e) {
  const el = document.getElementById('emotions');
  const dims = ['joy','anxiety','anger','curiosity','sadness'];
  let html = '<div style="margin-bottom:8px;color:var(--dim)">Temperament → Mood</div>';
  dims.forEach(d => {
    const base = Math.round((e.temperament[d]||0)*100);
    const mood = Math.round((e.mood[d]||0)*100);
    const color = d==='joy'?'var(--positive)':d==='anxiety'?'var(--warm)':
      d==='anger'?'var(--negative)':d==='curiosity'?'var(--accent)':'var(--dim)';
    html += `<div class="emotion-row"><span>${d}</span>
      <div style="flex:1;margin:0 8px"><div class="bar">
        <div class="bar-fill" style="width:${mood}%;background:${color}"></div>
      </div></div><span>${base}→${mood}%</span></div>`;
  });
  if (e.reaction) {
    html += `<div style="margin-top:8px;color:var(--warm)">⚡ ${e.reaction.type} (${Math.round(e.reaction.intensity*100)}%): ${e.reaction.trigger}</div>`;
  }
  html += `<div style="margin-top:8px;color:var(--dim)">${e.growth.stage} (${Math.round(e.growth.maturity*100)}% mature)</div>`;
  el.innerHTML = html;
}

function renderBeliefs(beliefs) {
  const el = document.getElementById('beliefs-content');
  if (!beliefs.length) { el.innerHTML = '<span style="color:var(--dim)">No beliefs yet</span>'; return; }
  el.innerHTML = beliefs.map(b => {
    const bar = Math.round(b.confidence * 100);
    return `<div class="belief-item">"${b.content}"
      <div class="bar"><div class="bar-fill" style="width:${bar}%;background:var(--accent)"></div></div>
      <span style="color:var(--dim);font-size:10px">${b.from} · +${b.reinforced} -${b.contradicted}</span></div>`;
  }).join('');
}

function renderDesires(desires) {
  const el = document.getElementById('desires-content');
  if (!desires.length) { el.innerHTML = '<span style="color:var(--dim)">No desires yet</span>'; return; }
  el.innerHTML = desires.filter(d=>!d.satisfied).map(d => {
    const bar = Math.round(d.urgency * 100);
    return `<div style="margin:4px 0">${d.content}
      <div class="bar"><div class="bar-fill" style="width:${bar}%;background:var(--warm)"></div></div>
      <span style="color:var(--dim);font-size:10px">${d.source}</span></div>`;
  }).join('');
}

function renderRelationships(rels) {
  const el = document.getElementById('relationships-content');
  if (!rels.length) { el.innerHTML = '<span style="color:var(--dim)">No relationships yet</span>'; return; }
  el.innerHTML = rels.map(r => {
    const gutClass = r.gut_feeling > 0.2 ? 'gut-positive' : r.gut_feeling < -0.2 ? 'gut-negative' : 'gut-neutral';
    let html = `<div class="relationship-card">
      <div><strong>${r.name}</strong> <span class="${gutClass}">${r.feeling} (${r.gut_feeling>0?'+':''}${r.gut_feeling.toFixed(2)})</span></div>
      <div style="color:var(--dim);font-size:11px">${r.model}</div>
      <div style="font-size:11px">trust: ${Math.round(r.trust*100)}% · ${r.openness} · makes me feel: ${r.dominant_emotion} · ×${r.interactions}</div>`;
    if (r.communication_style) html += `<div style="font-size:11px;color:var(--accent)">voice: ${r.communication_style}</div>`;
    if (r.safe_topics?.length) html += `<div style="font-size:11px">${r.safe_topics.map(t=>`<span class="tag" style="border:1px solid var(--positive)">${t}</span>`).join('')}</div>`;
    if (r.avoid_topics?.length) html += `<div style="font-size:11px">${r.avoid_topics.map(t=>`<span class="tag" style="border:1px solid var(--negative)">${t}</span>`).join('')}</div>`;
    if (r.triggers?.length) html += `<div style="font-size:11px;color:var(--warm)">⚡ ${r.triggers.join(' · ')}</div>`;
    if (r.memorable?.length) html += `<div style="font-size:10px;color:var(--dim)">moments: ${r.memorable.join(' · ')}</div>`;
    html += '</div>';
    return html;
  }).join('');
}

function renderSelf(s) {
  const el = document.getElementById('self-content');
  let html = '';
  if (s.identity?.length) html += '<div><strong>I am:</strong> ' + s.identity.map(i=>`<div>· ${i}</div>`).join('') + '</div>';
  if (s.strengths?.length) html += `<div style="margin-top:4px"><strong>Strengths:</strong> ${s.strengths.join(', ')}</div>`;
  if (s.weaknesses?.length) html += `<div><strong>Struggles:</strong> ${s.weaknesses.join(', ')}</div>`;
  if (s.narrative) html += `<div style="margin-top:4px"><strong>My story:</strong> ${s.narrative}</div>`;
  if (s.aspirational) html += `<div><strong>Becoming:</strong> ${s.aspirational}</div>`;
  if (s.blind_spots?.length) html += `<div style="margin-top:4px;color:var(--negative);font-size:11px"><strong>Blind spots (can't see):</strong> ${s.blind_spots.join(', ')}</div>`;
  el.innerHTML = html || '<span style="color:var(--dim)">Still forming...</span>';
}

function renderDiary(entries) {
  const el = document.getElementById('diary-content');
  if (!entries.length) { el.innerHTML = '<span style="color:var(--dim)">Empty</span>'; return; }
  el.innerHTML = entries.map(e => {
    const age = e.age_hours < 1 ? `${Math.round(e.age_hours*60)}m` : e.age_hours < 24 ? `${e.age_hours.toFixed(1)}h` : `${(e.age_hours/24).toFixed(1)}d`;
    return `<div style="margin:3px 0;font-size:11px">
      <span style="color:var(--dim)">${age}</span>
      <span class="tag">${e.source}</span>
      ${e.content.slice(0,70)}
      <span style="color:var(--dim)">${e.tags.map(t=>`#${t}`).join(' ')}</span></div>`;
  }).join('');
}

function flashReflection(r) {
  if (r.total_updates > 0) {
    document.getElementById('brain-panel').classList.add('reflection-flash');
    setTimeout(() => document.getElementById('brain-panel').classList.remove('reflection-flash'), 1000);
    refreshAll();
  }
}

function toggleSection(id) {
  const el = document.getElementById(id);
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

// chat
async function sendMessage() {
  const input = document.getElementById('chat-input');
  const speaker = document.getElementById('speaker-input').value || 'human';
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  addChatMessage(speaker, msg, true);

  const resp = await fetch('/api/talk', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: msg, speaker: speaker})
  });
  const data = await resp.json();
  addChatMessage(agentName, data.response, false);
  updateStatusBar(data.status);
  refreshAll();
}

function addChatMessage(name, text, isHuman) {
  const el = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'msg ' + (isHuman ? 'msg-human' : 'msg-agent');
  div.innerHTML = `<div class="msg-name">${name}</div>${text}`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

document.getElementById('chat-input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
document.getElementById('send-btn').addEventListener('click', sendMessage);
</script>
</body>
</html>"""


def run_web(host: str = "0.0.0.0", port: int = 8888):
    uvicorn.run(app, host=host, port=port)
