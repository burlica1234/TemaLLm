

document.addEventListener("DOMContentLoaded", () => {
  console.log("[SmartLibrarian] script.js loaded & DOM ready");


  const API_BASE = "http://localhost:8000";


  const qEl         = document.getElementById("q");
  const askBtn      = document.getElementById("askBtn");
  const withAudioEl = document.getElementById("withAudio");
  const msgsEl      = document.getElementById("msgs");
  const errEl       = document.getElementById("error");

  const voiceBtn    = document.getElementById("voiceBtn");
  const voiceStatus = document.getElementById("voiceStatus");
  const interimEl   = document.getElementById("interim");


  if (!qEl || !askBtn || !withAudioEl || !msgsEl || !errEl || !voiceBtn || !voiceStatus || !interimEl) {
    console.error("[SmartLibrarian] Missing DOM IDs. Check index.html matches script.js IDs.");
    return;
  }


  function setLoading(isLoading) {
    askBtn.disabled = isLoading || !qEl.value.trim();
    askBtn.textContent = isLoading ? "Thinking..." : "Ask";
  }
  function showError(msg) {
    errEl.textContent = msg || "";
    errEl.classList.toggle("hidden", !msg);
  }
  function addBubble(role, text, audioUrl = null) {
    const wrap = document.createElement("div");
    wrap.className = `bubble ${role === "user" ? "user" : "ai"}`;

    const pre = document.createElement("pre");
    pre.textContent = text || "";
    wrap.appendChild(pre);

    if (audioUrl) {
      const audio = document.createElement("audio");
      audio.controls = true;
      audio.src = audioUrl;
      wrap.appendChild(audio);
    }

    msgsEl.appendChild(wrap);
    wrap.scrollIntoView({ behavior: "smooth", block: "end" });
  }


  async function ask() {
    const question = qEl.value.trim();
    if (!question) return;

    setLoading(true);
    showError("");
    addBubble("user", question);
    qEl.value = "";

    try {
      const resp = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ question, with_audio: withAudioEl.checked }),
      });
      if (!resp.ok) {
        const txt = await resp.text().catch(() => "");
        throw new Error(`HTTP ${resp.status} ${txt}`);
      }
      const data = await resp.json();
      const aiText = data?.text || "";
      const audioUrl = data?.audio_url ? `${API_BASE}${data.audio_url}` : null;
      addBubble("ai", aiText, audioUrl);
    } catch (e) {
      console.error(e);
      showError(e.message || "Request failed");
    } finally {
      setLoading(false);
      qEl.focus();
    }
  }

  askBtn.addEventListener("click", ask);
  qEl.addEventListener("input", () => setLoading(false));
  qEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      ask();
    }
  });


  let voiceOn = false;
  let sr = null;
  let mediaRecorder = null;
  let fallbackTimer = null;

  function supportsWebSpeech() {
    return ("webkitSpeechRecognition" in window) || ("SpeechRecognition" in window);
  }
  function setVoiceUI(active, statusText) {
    voiceOn = active;
    voiceBtn.classList.toggle("active", !!active);
    voiceStatus.classList.toggle("hidden", !active);
    voiceStatus.innerHTML = `Voice mode: <b>${active ? (statusText || "listening") : "off"}</b>`;
  }
  function showInterim(text) {
    if (!text) { interimEl.classList.add("hidden"); interimEl.textContent = ""; return; }
    interimEl.classList.remove("hidden");
    interimEl.textContent = "🎙 " + text;
  }
  function secureContextHint() {
    if (!window.isSecureContext) {
      showError("Voice needs a secure context. Serve the page via http://localhost:5500 (not file://).");
      return false;
    }
    return true;
  }
  async function ensureMicPermission() {
    try {
      if (!navigator.permissions?.query) return true;
      const res = await navigator.permissions.query({ name: "microphone" });
      if (res.state === "denied") {
        showError("Microphone permission is blocked. Allow the mic in site settings, then reload.");
        return false;
      }
      return true;
    } catch { return true; }
  }

  function startWebSpeech() {
    console.log("[Voice] Starting Web Speech API…");
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    sr = new SR();
    sr.lang = "en-US";
    sr.continuous = true;
    sr.interimResults = true;

    sr.onstart = () => { console.log("[Voice] WebSpeech started"); setVoiceUI(true, "listening"); };
    sr.onresult = async (e) => {
      let interim = "", final = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) final += res[0].transcript;
        else interim += res[0].transcript;
      }
      showInterim(interim);
      if (final.trim()) {
        showInterim("");
        qEl.value = final.trim();
        await ask();
      }
    };
    sr.onerror = (e) => {
      console.warn("[Voice] WebSpeech error:", e);
      showError(`Voice error: ${e.error || e.message || "unknown"}. Falling back to recorder.`);
      stopWebSpeech(false);
      startFallbackRecorder();
    };
    sr.onend = () => { if (voiceOn) sr.start(); };

    try { sr.start(); }
    catch (e) {
      console.warn("[Voice] WebSpeech start() failed:", e);
      showError("Web Speech API failed to start. Falling back to recorder.");
      stopWebSpeech(false);
      startFallbackRecorder();
    }
  }
  function stopWebSpeech(updateUI = true) {
    try { sr && sr.stop(); } catch {}
    sr = null;
    showInterim("");
    if (updateUI) setVoiceUI(false, "off");
  }

  async function startFallbackRecorder() {
    console.log("[Voice] Starting fallback recorder…");
    try {
      const ok = await ensureMicPermission();
      if (!ok) { setVoiceUI(false, "off"); return; }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      const chunks = [];

      mediaRecorder.ondataavailable = (ev) => { if (ev.data.size) chunks.push(ev.data); };
      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/webm" });
        await sendBlobForSTT(blob);
        if (voiceOn) startFallbackRecorder();
      };

      mediaRecorder.start();
      setVoiceUI(true, "recording");
      showInterim("Listening…");


      fallbackTimer = setTimeout(() => {
        try { mediaRecorder.state !== "inactive" && mediaRecorder.stop(); } catch {}
      }, 5000);
    } catch (e) {
      console.error("[Voice] Fallback error:", e);
      showError("Microphone error. Check permissions and try again.");
      setVoiceUI(false, "off");
    }
  }
  async function sendBlobForSTT(blob) {
    const fd = new FormData();
    fd.append("file", blob, "speech.webm");
    try {
      const resp = await fetch(`${API_BASE}/api/transcribe`, {
        method: "POST",
        body: fd,
        credentials: "include",
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const text = (data?.text || "").trim();
      showInterim("");
      if (text) { qEl.value = text; await ask(); }
    } catch (e) {
      console.error("[Voice] STT failed:", e);
      showError("Transcription failed. Is the backend running and OPENAI_API_KEY set?");
    }
  }
  function stopFallbackRecorder() {
    if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null; }
    try { mediaRecorder && mediaRecorder.state !== "inactive" && mediaRecorder.stop(); } catch {}
    mediaRecorder = null;
    showInterim("");
    setVoiceUI(false, "off");
  }

  voiceBtn.addEventListener("click", async () => {
    console.log("[Voice] Button clicked. on=", voiceOn);
    if (!voiceOn) {
      showError("");
      if (!secureContextHint()) return;
      setVoiceUI(true, "starting…");
      if (supportsWebSpeech()) startWebSpeech();
      else await startFallbackRecorder();
    } else {
      if (sr) stopWebSpeech();
      if (mediaRecorder) stopFallbackRecorder();
      else setVoiceUI(false, "off");
    }
  });


  fetch(`${API_BASE}/health`).then(r => r.json()).then(j => {
    console.log("[SmartLibrarian] Backend health:", j);
  }).catch(() => {
    showError("Backend not reachable at " + API_BASE);
  });


  qEl.focus();
});
