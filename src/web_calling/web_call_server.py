from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


PROJECT_SRC = Path(__file__).resolve().parents[1]
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from q3_market_components.market_component import Q3MarketComponent  # noqa: E402
from voice_agent.lendingkart_agent import LendingkartVoiceAgent  # noqa: E402
from voice_agent.stt import SttResult, get_stt_provider  # noqa: E402
from voice_agent.tts import get_tts_provider  # noqa: E402


HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Lendingkart Voice Agent</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8fb;
      --panel: #ffffff;
      --ink: #17202a;
      --muted: #64748b;
      --line: #d9e1ec;
      --accent: #0f766e;
      --accent-2: #2563eb;
      --danger: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    header {
      padding: 18px 22px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      line-height: 1.2;
    }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 330px;
      gap: 18px;
      padding: 18px;
      max-width: 1180px;
      margin: 0 auto;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .toolbar {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      padding: 14px;
      border-bottom: 1px solid var(--line);
    }
    button {
      border: 0;
      border-radius: 6px;
      padding: 10px 14px;
      font-size: 14px;
      cursor: pointer;
      background: var(--accent);
      color: white;
    }
    button.secondary { background: var(--accent-2); }
    button.neutral { background: #475569; }
    button.danger { background: var(--danger); }
    button:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }
    .status {
      color: var(--muted);
      font-size: 13px;
      min-height: 18px;
    }
    .mic-meter {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-width: 145px;
      color: var(--muted);
      font-size: 12px;
    }
    .mic-bar {
      width: 62px;
      height: 8px;
      border: 1px solid var(--line);
      background: #edf2f7;
      overflow: hidden;
    }
    .mic-fill {
      display: block;
      width: 0%;
      height: 100%;
      background: var(--accent);
      transition: width 80ms linear;
    }
    .conversation {
      height: min(62vh, 680px);
      min-height: 420px;
      overflow-y: auto;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .msg {
      max-width: 78%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 11px 12px;
      line-height: 1.4;
      white-space: pre-wrap;
    }
    .user {
      align-self: flex-end;
      background: #e8f3ff;
    }
    .agent {
      align-self: flex-start;
      background: #eefaf5;
    }
    .meta {
      display: block;
      margin-top: 7px;
      font-size: 12px;
      color: var(--muted);
    }
    .side {
      padding: 14px;
      display: grid;
      gap: 14px;
      align-content: start;
    }
    .side h2 {
      margin: 0 0 8px 0;
      font-size: 15px;
    }
    .side p, .side li {
      font-size: 13px;
      color: var(--muted);
      line-height: 1.45;
    }
    .side ul {
      padding-left: 18px;
      margin: 6px 0 0;
    }
    textarea {
      width: 100%;
      min-height: 86px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      font-family: inherit;
      font-size: 14px;
    }
    audio {
      display: block;
      width: 100%;
      margin-top: 8px;
    }
    .citations {
      margin-top: 8px;
      display: grid;
      gap: 6px;
    }
    .citation {
      display: block;
      color: #1d4ed8;
      font-size: 12px;
      text-decoration: none;
    }
    @media (max-width: 840px) {
      main { grid-template-columns: 1fr; }
      .conversation { height: 58vh; min-height: 360px; }
      .msg { max-width: 92%; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Lendingkart Voice Agent</h1>
    <span class="status" id="sessionLabel"></span>
  </header>
  <main>
    <section class="panel">
      <div class="toolbar">
        <select id="agentMode" title="Agent mode">
          <option value="q1_lendingkart">Q1 Lendingkart KB</option>
          <option value="q3_philippines">Q3 Philippines</option>
          <option value="q3_indonesia">Q3 Indonesia</option>
        </select>
        <select id="q3Register" title="Q3 response language" hidden></select>
        <button id="startBtn">Record</button>
        <button id="interruptBtn" class="neutral" disabled>Talk Now</button>
        <button id="stopBtn" class="danger" disabled>Send Recording</button>
        <button id="sendBtn" class="secondary">Send Text</button>
        <button id="resetBtn" class="neutral">New Session</button>
        <label class="status"><input type="checkbox" id="continuousToggle" checked /> Auto-record after reply</label>
        <span class="mic-meter">
          Mic
          <span class="mic-bar"><span class="mic-fill" id="micFill"></span></span>
          <span id="micLabel">idle</span>
        </span>
        <span class="status" id="status">Ready</span>
      </div>
      <div class="conversation" id="conversation"></div>
    </section>
    <aside class="panel side">
      <div>
        <h2>Live Transcript</h2>
        <textarea id="transcriptBox" placeholder="Speak with the mic button, or type a question here."></textarea>
      </div>
      <div>
        <h2>How To Demo</h2>
        <ul>
          <li>Tap Record, speak naturally, then tap Send Recording.</li>
          <li>The server transcribes the recording after you send it.</li>
          <li>The agent response plays as WAV audio when available.</li>
          <li>Ask another question to continue the same session.</li>
        </ul>
      </div>
      <div>
        <h2>Good Test Questions</h2>
        <ul>
          <li>What processing fee will I need to pay?</li>
          <li>Can I apply online?</li>
          <li>What documents are required?</li>
          <li>What happens if I miss an EMI?</li>
          <li>Can I speak to a human advisor?</li>
        </ul>
      </div>
    </aside>
  </main>
  <script>
    const statusEl = document.getElementById("status");
    const conversationEl = document.getElementById("conversation");
    const transcriptBox = document.getElementById("transcriptBox");
    const startBtn = document.getElementById("startBtn");
    const stopBtn = document.getElementById("stopBtn");
    const sendBtn = document.getElementById("sendBtn");
    const resetBtn = document.getElementById("resetBtn");
    const interruptBtn = document.getElementById("interruptBtn");
    const agentMode = document.getElementById("agentMode");
    const q3Register = document.getElementById("q3Register");
    const continuousToggle = document.getElementById("continuousToggle");
    const sessionLabel = document.getElementById("sessionLabel");
    const micFill = document.getElementById("micFill");
    const micLabel = document.getElementById("micLabel");

    let sessionId = localStorage.getItem("lk_voice_session_id");
    if (!sessionId) {
      sessionId = `web_${Date.now()}_${Math.random().toString(16).slice(2)}`;
      localStorage.setItem("lk_voice_session_id", sessionId);
    }
    sessionLabel.textContent = `Session: ${sessionId}`;

    const SpeechRecognition = null; // Use server-side Whisper as the source of truth for recorded turns.
    let recognition = null;
    let isListening = false;
    let isRecordingTurn = false;
    let isSendingTurn = false;
    let currentAudio = null;
    let manualStopRequested = false;
    let activeFinalText = "";
    let activeInterimText = "";
    let emptyRestartCount = 0;
    let speechEndTimer = null;
    let noAnswerTimer = null;
    let pendingAutoRecordTimer = null;
    let audioAutoplayFallbackTimer = null;
    let heardInputThisRecording = false;
    let cancelWithoutReplyRequested = false;
    let mediaStream = null;
    let audioContext = null;
    let audioSource = null;
    let audioProcessor = null;
    let audioChunks = [];
    let recordingSampleRate = 0;
    const MAX_EMPTY_RESTARTS = 8;
    const AUTO_NO_ANSWER_TIMEOUT_MS = 5000;
    const SPEECH_RMS_THRESHOLD = 0.012;
    const q3RegisterOptions = {
      q3_philippines: [
        { value: "auto", label: "Auto language" },
        { value: "taglish", label: "Taglish" },
        { value: "filipino", label: "Filipino/Tagalog" },
        { value: "english", label: "English" }
      ],
      q3_indonesia: [
        { value: "auto", label: "Auto register" },
        { value: "formal_id", label: "Formal Bahasa" },
        { value: "colloquial_id", label: "Colloquial Bahasa" },
        { value: "regional_javanese_id", label: "Javanese-influenced" }
      ]
    };

    function setStatus(text) {
      statusEl.textContent = text;
    }

    function makeNewSessionId() {
      return `${agentMode.value}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    }

    function updateQ3RegisterSelector(resetValue=false) {
      const options = q3RegisterOptions[agentMode.value];
      q3Register.innerHTML = "";
      if (!options) {
        q3Register.hidden = true;
        q3Register.disabled = true;
        q3Register.value = "auto";
        return;
      }
      options.forEach((option) => {
        const node = document.createElement("option");
        node.value = option.value;
        node.textContent = option.label;
        q3Register.appendChild(node);
      });
      q3Register.hidden = false;
      q3Register.disabled = false;
      if (resetValue || !options.some((option) => option.value === q3Register.value)) {
        q3Register.value = "auto";
      }
    }

    function selectedQ3Register() {
      return q3Register.hidden ? "auto" : q3Register.value;
    }
    updateQ3RegisterSelector(false);

    function updateMicMeter(level, label=null) {
      const percent = Math.max(0, Math.min(100, Math.round(level * 100)));
      micFill.style.width = `${percent}%`;
      micLabel.textContent = label || `${percent}%`;
    }

    function clearNoAnswerTimer() {
      if (noAnswerTimer) {
        clearTimeout(noAnswerTimer);
        noAnswerTimer = null;
      }
    }

    function clearAutoRecordTimers() {
      if (pendingAutoRecordTimer) {
        clearTimeout(pendingAutoRecordTimer);
        pendingAutoRecordTimer = null;
      }
      if (audioAutoplayFallbackTimer) {
        clearTimeout(audioAutoplayFallbackTimer);
        audioAutoplayFallbackTimer = null;
      }
    }

    function queueAutoRecordAfterAgent(delayMs=350) {
      clearAutoRecordTimers();
      pendingAutoRecordTimer = setTimeout(() => {
        pendingAutoRecordTimer = null;
        if (continuousToggle.checked && !isRecordingTurn && !isSendingTurn) {
          startListening(true);
        }
      }, delayMs);
    }

    function markInputHeard() {
      heardInputThisRecording = true;
      clearNoAnswerTimer();
    }

    function armNoAnswerTimer(fromAutoListen) {
      clearNoAnswerTimer();
      if (!fromAutoListen || heardInputThisRecording) return;
      noAnswerTimer = setTimeout(() => {
        noAnswerTimer = null;
        if (!heardInputThisRecording && isRecordingTurn && !isSendingTurn) {
          cancelRecordingWithoutReply("No answer detected for 5 seconds. Auto-record turned off.");
        }
      }, AUTO_NO_ANSWER_TIMEOUT_MS);
    }

    function setIdleControls() {
      startBtn.textContent = "Record";
      startBtn.disabled = false;
      stopBtn.disabled = true;
      sendBtn.disabled = false;
      updateMicMeter(0, "idle");
    }

    function setRecordingControls() {
      startBtn.textContent = "Recording...";
      startBtn.disabled = true;
      stopBtn.disabled = false;
      sendBtn.disabled = true;
    }

    function setSendingControls() {
      startBtn.textContent = "Record";
      startBtn.disabled = true;
      stopBtn.disabled = true;
      sendBtn.disabled = true;
    }

    function stopCurrentAudio() {
      clearAutoRecordTimers();
      if (currentAudio && !currentAudio.paused) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
      }
      currentAudio = null;
      interruptBtn.disabled = true;
    }

    function appendMessage(role, text, payload) {
      const item = document.createElement("div");
      item.className = `msg ${role}`;
      item.textContent = text;

      if (payload && payload.meta) {
        const meta = document.createElement("span");
        meta.className = "meta";
        meta.textContent = payload.meta;
        item.appendChild(meta);
      }

      if (payload && payload.audioUrl) {
        const audio = document.createElement("audio");
        audio.controls = true;
        audio.autoplay = true;
        audio.src = payload.audioUrl;
        audio.onplay = () => {
          if (audioAutoplayFallbackTimer) {
            clearTimeout(audioAutoplayFallbackTimer);
            audioAutoplayFallbackTimer = null;
          }
          currentAudio = audio;
          interruptBtn.disabled = false;
        };
        audio.onended = () => {
          currentAudio = null;
          interruptBtn.disabled = true;
          if (continuousToggle.checked && role === "agent") {
            queueAutoRecordAfterAgent(350);
          }
        };
        audio.onpause = () => {
          if (currentAudio === audio && audio.currentTime === 0) {
            currentAudio = null;
            interruptBtn.disabled = true;
          }
        };
        item.appendChild(audio);
        if (continuousToggle.checked && role === "agent") {
          audioAutoplayFallbackTimer = setTimeout(() => {
            audioAutoplayFallbackTimer = null;
            if (audio.paused && audio.currentTime === 0) {
              queueAutoRecordAfterAgent(0);
            }
          }, 3500);
        }
      } else if (payload && payload.autoRecordAfter && continuousToggle.checked && role === "agent") {
        queueAutoRecordAfterAgent(650);
      }

      if (payload && payload.citations && payload.citations.length) {
        const wrap = document.createElement("div");
        wrap.className = "citations";
        payload.citations.slice(0, 3).forEach((citation) => {
          const link = document.createElement("a");
          link.className = "citation";
          link.href = citation.url || "#";
          link.target = "_blank";
          link.rel = "noopener";
          link.textContent = citation.label || citation.source_id || citation.record_id;
          wrap.appendChild(link);
        });
        item.appendChild(wrap);
      }

      conversationEl.appendChild(item);
      conversationEl.scrollTop = conversationEl.scrollHeight;
    }

    async function playGreeting() {
      setStatus("Preparing greeting...");
      try {
        const response = await fetch("/api/greeting", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            mode: agentMode.value,
            response_register: selectedQ3Register()
          })
        });
        if (!response.ok) {
          setStatus("Ready");
          return;
        }
        const payload = await response.json();
        appendMessage("agent", payload.spoken_text, {
          audioUrl: payload.audio_url,
          meta: `${payload.mode}${payload.response_register ? ` | ${payload.response_register}` : ""} | greeting`,
          autoRecordAfter: true
        });
        setStatus("Greeting ready");
      } catch (error) {
        setStatus(`Greeting skipped: ${error.message}`);
      }
    }

    function clearSpeechEndTimer() {
      if (speechEndTimer) {
        clearTimeout(speechEndTimer);
        speechEndTimer = null;
      }
    }

    function scheduleRecognitionRestart(fromAutoListen=false) {
      clearSpeechEndTimer();
      if (manualStopRequested || !isRecordingTurn) return;
      speechEndTimer = setTimeout(() => {
        speechEndTimer = null;
        if (!manualStopRequested && isRecordingTurn && !isListening) {
          startListening(fromAutoListen, true);
        }
      }, 350);
    }

    async function cancelRecordingWithoutReply(message) {
      cancelWithoutReplyRequested = true;
      manualStopRequested = true;
      clearSpeechEndTimer();
      clearNoAnswerTimer();
      clearAutoRecordTimers();
      continuousToggle.checked = false;
      if (recognition && isListening) {
        try {
          recognition.stop();
        } catch {}
      }
      await stopCallerAudioRecording();
      isRecordingTurn = false;
      isListening = false;
      isSendingTurn = false;
      recognition = null;
      activeFinalText = "";
      activeInterimText = "";
      transcriptBox.value = "";
      heardInputThisRecording = false;
      setIdleControls();
      setStatus(message);
    }

    function blobToBase64(blob) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          const result = String(reader.result || "");
          resolve(result.includes(",") ? result.split(",")[1] : result);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      });
    }

    function mergeAudioChunks(chunks) {
      const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
      const samples = new Float32Array(totalLength);
      let offset = 0;
      chunks.forEach((chunk) => {
        samples.set(chunk, offset);
        offset += chunk.length;
      });
      return samples;
    }

    function writeAscii(view, offset, text) {
      for (let i = 0; i < text.length; i++) {
        view.setUint8(offset + i, text.charCodeAt(i));
      }
    }

    function encodeWav(samples, sampleRate) {
      const bytesPerSample = 2;
      const blockAlign = bytesPerSample;
      const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample);
      const view = new DataView(buffer);
      writeAscii(view, 0, "RIFF");
      view.setUint32(4, 36 + samples.length * bytesPerSample, true);
      writeAscii(view, 8, "WAVE");
      writeAscii(view, 12, "fmt ");
      view.setUint32(16, 16, true);
      view.setUint16(20, 1, true);
      view.setUint16(22, 1, true);
      view.setUint32(24, sampleRate, true);
      view.setUint32(28, sampleRate * blockAlign, true);
      view.setUint16(32, blockAlign, true);
      view.setUint16(34, 16, true);
      writeAscii(view, 36, "data");
      view.setUint32(40, samples.length * bytesPerSample, true);
      let offset = 44;
      for (let i = 0; i < samples.length; i++, offset += 2) {
        const sample = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      }
      return buffer;
    }

    async function startCallerAudioRecording() {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!navigator.mediaDevices || !AudioContextClass) {
        return false;
      }
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });
        audioContext = new AudioContextClass();
        recordingSampleRate = audioContext.sampleRate || 16000;
        audioChunks = [];
        audioSource = audioContext.createMediaStreamSource(mediaStream);
        audioProcessor = audioContext.createScriptProcessor(4096, 1, 1);
        audioProcessor.onaudioprocess = (event) => {
          if (!isRecordingTurn && !isListening) return;
          const input = event.inputBuffer.getChannelData(0);
          audioChunks.push(new Float32Array(input));
          let sum = 0;
          for (let i = 0; i < input.length; i++) {
            sum += input[i] * input[i];
          }
          const rms = Math.sqrt(sum / input.length);
          updateMicMeter(Math.min(1, rms * 8));
          if (rms >= SPEECH_RMS_THRESHOLD) {
            markInputHeard();
          }
        };
        audioSource.connect(audioProcessor);
        audioProcessor.connect(audioContext.destination);
        return true;
      } catch (error) {
        setStatus(`Recording unavailable: ${error.message}. Transcript mode only.`);
        return false;
      }
    }

    async function stopCallerAudioRecording() {
      try {
        if (audioProcessor) {
          audioProcessor.disconnect();
          audioProcessor.onaudioprocess = null;
        }
        if (audioSource) {
          audioSource.disconnect();
        }
        if (mediaStream) {
          mediaStream.getTracks().forEach((track) => track.stop());
        }
        if (audioContext && audioContext.state !== "closed") {
          await audioContext.close();
        }
        const chunks = audioChunks;
        const sampleRate = recordingSampleRate || 16000;
        audioContext = null;
        audioSource = null;
        audioProcessor = null;
        mediaStream = null;
        audioChunks = [];
        recordingSampleRate = 0;
        updateMicMeter(0, "idle");
        if (!chunks.length) return null;
        const samples = mergeAudioChunks(chunks);
        if (!samples.length) return null;
        const wavBuffer = encodeWav(samples, sampleRate);
        const blob = new Blob([wavBuffer], { type: "audio/wav" });
        const base64 = await blobToBase64(blob);
        return {
          base64,
          mime_type: "audio/wav",
          byte_count: blob.size,
          sample_rate: sampleRate,
          encoding: "pcm_s16le"
        };
      } catch {
        return null;
      }
    }

    async function finalizeRecordingAndSend() {
      manualStopRequested = true;
      cancelWithoutReplyRequested = false;
      clearSpeechEndTimer();
      clearNoAnswerTimer();
      clearAutoRecordTimers();
      setSendingControls();
      if (recognition && isListening) {
        try {
          recognition.stop();
        } catch {
          finishCurrentRecording();
        }
      } else {
        await finishCurrentRecording();
      }
    }

    async function finishCurrentRecording() {
      if (isSendingTurn) return;
      if (cancelWithoutReplyRequested) {
        cancelWithoutReplyRequested = false;
        return;
      }
      isSendingTurn = true;
      manualStopRequested = true;
      clearSpeechEndTimer();
      clearNoAnswerTimer();
      clearAutoRecordTimers();
      setSendingControls();
      setStatus("Sending recording...");
      const browserText = (activeFinalText || activeInterimText || transcriptBox.value).trim();
      const callerAudio = await stopCallerAudioRecording();
      const text = callerAudio ? "" : browserText;
      isRecordingTurn = false;
      isListening = false;
      recognition = null;
      if (text || callerAudio) {
        await sendTurn(text, callerAudio);
      } else {
        isSendingTurn = false;
        activeFinalText = "";
        activeInterimText = "";
        transcriptBox.value = "";
        setIdleControls();
        setStatus("No transcript captured. Please record again or type the question.");
      }
    }

    async function sendTurn(text, callerAudio=null) {
      const transcript = text.trim();
      if (!transcript && !callerAudio) {
        setStatus("Nothing to send");
        setIdleControls();
        return;
      }
      const needsServerTranscription = !transcript && callerAudio;
      isSendingTurn = true;
      setSendingControls();
      if (transcript) {
        appendMessage("user", transcript);
      }
      transcriptBox.value = "";
      setStatus(needsServerTranscription ? "Transcribing recording..." : "Thinking...");

      try {
        const response = await fetch("/api/turn", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            transcript,
            mode: agentMode.value,
            response_register: selectedQ3Register(),
            caller_audio: callerAudio
          })
        });

        if (!response.ok) {
          let errorPayload = {};
          try {
            errorPayload = await response.json();
          } catch {
            errorPayload = { error: await response.text() };
          }
          if (errorPayload.heard_text) {
            transcriptBox.value = errorPayload.heard_text;
          }
          const confidence = errorPayload.stt_confidence !== undefined ? ` Confidence: ${errorPayload.stt_confidence}.` : "";
          setStatus(errorPayload.error_type === "low_confidence_stt" ? "Please repeat or edit transcript." : "Could not transcribe recording.");
          appendMessage("agent", `${errorPayload.error || "Could not process the recording."}${confidence}`);
          return;
        }

        const payload = await response.json();
        if (needsServerTranscription) {
          appendMessage("user", payload.customer_transcript || "[Audio sent for transcription]", {
            meta: payload.stt ? `${payload.stt.provider} STT` : "server STT"
          });
        }
        appendMessage("agent", payload.spoken_text, {
          audioUrl: payload.audio_url,
          citations: payload.citations,
          meta: `${payload.mode}${payload.response_register ? ` | ${payload.response_register}` : ""} | ${payload.action} | ${payload.retrieval_status} | ${payload.latency_ms.end_to_end} ms`
        });
        setStatus("Ready");
      } catch (error) {
        setStatus("Error");
        appendMessage("agent", `Error: ${error.message}`);
      } finally {
        isSendingTurn = false;
        if (!isRecordingTurn) setIdleControls();
      }
    }

    async function startListening(fromAutoListen=false, preserveTranscript=false) {
      if (isListening) {
        setRecordingControls();
        return;
      }
      stopCurrentAudio();
      clearSpeechEndTimer();
      clearNoAnswerTimer();
      clearAutoRecordTimers();
      manualStopRequested = false;
      cancelWithoutReplyRequested = false;
      const hasActiveRecording = Boolean(mediaStream || audioContext || audioChunks.length);
      if (hasActiveRecording) {
        preserveTranscript = true;
      }
      if (!preserveTranscript && !isRecordingTurn) {
        activeFinalText = "";
        activeInterimText = "";
        heardInputThisRecording = false;
        transcriptBox.value = "";
        const audioStarted = await startCallerAudioRecording();
        if (!audioStarted && !SpeechRecognition) {
          setIdleControls();
          setStatus("Microphone recording is unavailable. Type the question instead.");
          return;
        }
        isRecordingTurn = true;
        emptyRestartCount = 0;
      }
      if (!isRecordingTurn) isRecordingTurn = true;
      setRecordingControls();
      if (!preserveTranscript) {
        armNoAnswerTimer(fromAutoListen);
      }
      if (!SpeechRecognition) {
        setStatus(fromAutoListen ? "Listening... answer now, or auto-record will stop after 5 seconds." : "Recording audio only... tap Send Recording when done.");
        return;
      }
      recognition = new SpeechRecognition();
      recognition.lang = "en-IN";
      recognition.interimResults = true;
      recognition.continuous = true;

      recognition.onstart = () => {
        isListening = true;
        setStatus("Recording... tap Send Recording when done.");
        setRecordingControls();
      };
      recognition.onresult = (event) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const text = event.results[i][0].transcript;
          if (event.results[i].isFinal) activeFinalText += `${text} `;
          else interim += text;
        }
        activeInterimText = interim;
        transcriptBox.value = (activeFinalText || interim).trim();
        if ((activeFinalText || interim).trim()) {
          emptyRestartCount = 0;
          markInputHeard();
        }
      };
      recognition.onerror = (event) => {
        isListening = false;
        if (event.error === "no-speech" && !manualStopRequested && emptyRestartCount < MAX_EMPTY_RESTARTS) {
          emptyRestartCount += 1;
          setStatus("Still recording...");
          setRecordingControls();
          scheduleRecognitionRestart(fromAutoListen);
          return;
        }
        if (!manualStopRequested && isRecordingTurn) {
          setStatus(`Speech recognition paused: ${event.error}. Tap Send Recording when done.`);
          setRecordingControls();
          return;
        }
        setStatus(`Mic error: ${event.error}`);
        setIdleControls();
      };
      recognition.onend = () => {
        isListening = false;
        recognition = null;
        const text = (activeFinalText || activeInterimText || transcriptBox.value).trim();
        if (manualStopRequested) {
          if (cancelWithoutReplyRequested) {
            cancelWithoutReplyRequested = false;
            return;
          }
          finishCurrentRecording();
          return;
        }
        if (!manualStopRequested && !text && emptyRestartCount < MAX_EMPTY_RESTARTS) {
          emptyRestartCount += 1;
          setStatus("Still recording...");
          setRecordingControls();
          scheduleRecognitionRestart(fromAutoListen);
          return;
        }
        if (!manualStopRequested && isRecordingTurn) {
          setStatus("Recording... tap Send Recording when done.");
          setRecordingControls();
          if (emptyRestartCount < MAX_EMPTY_RESTARTS || text) {
            scheduleRecognitionRestart(fromAutoListen);
          }
          return;
        }
        setIdleControls();
        setStatus(fromAutoListen ? "Ready. Tap Record or Talk Now." : "Ready");
      };
      try {
        recognition.start();
      } catch (error) {
        isListening = false;
        if (isRecordingTurn) {
          setRecordingControls();
          setStatus(`Speech recognition paused: ${error.message}. Tap Send Recording when done.`);
        } else {
          setIdleControls();
          setStatus(`Could not start mic: ${error.message}`);
        }
      }
    }

    startBtn.addEventListener("click", () => startListening(false));

    stopBtn.addEventListener("click", () => {
      finalizeRecordingAndSend();
    });

    interruptBtn.addEventListener("click", () => startListening(false));

    sendBtn.addEventListener("click", () => sendTurn(transcriptBox.value));
    transcriptBox.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        sendTurn(transcriptBox.value);
      }
    });
    resetBtn.addEventListener("click", async () => {
      manualStopRequested = true;
      cancelWithoutReplyRequested = false;
      clearSpeechEndTimer();
      clearNoAnswerTimer();
      clearAutoRecordTimers();
      if (recognition && isListening) {
        try { recognition.stop(); } catch {}
      }
      await stopCallerAudioRecording();
      isRecordingTurn = false;
      isListening = false;
      isSendingTurn = false;
      setIdleControls();
      sessionId = makeNewSessionId();
      localStorage.setItem("lk_voice_session_id", sessionId);
      sessionLabel.textContent = `Session: ${sessionId}`;
      conversationEl.innerHTML = "";
      transcriptBox.value = "";
      stopCurrentAudio();
      setStatus("New session ready");
      playGreeting();
    });

    agentMode.addEventListener("change", async () => {
      manualStopRequested = true;
      cancelWithoutReplyRequested = false;
      clearSpeechEndTimer();
      clearNoAnswerTimer();
      clearAutoRecordTimers();
      if (recognition && isListening) {
        try { recognition.stop(); } catch {}
      }
      await stopCallerAudioRecording();
      isRecordingTurn = false;
      isListening = false;
      isSendingTurn = false;
      setIdleControls();
      updateQ3RegisterSelector(true);
      sessionId = makeNewSessionId();
      localStorage.setItem("lk_voice_session_id", sessionId);
      sessionLabel.textContent = `Session: ${sessionId}`;
      conversationEl.innerHTML = "";
      transcriptBox.value = "";
      stopCurrentAudio();
      setStatus("Mode changed. New session ready.");
      playGreeting();
    });
    q3Register.addEventListener("change", () => {
      setStatus("Q3 response language changed.");
    });
    setTimeout(() => playGreeting(), 250);
  </script>
</body>
</html>
"""


@dataclass
class WebSession:
    session_id: str
    turns: list[dict[str, Any]] = field(default_factory=list)

    @property
    def last_agent_text(self) -> str | None:
        if not self.turns:
            return None
        return self.turns[-1].get("agent", {}).get("spoken_text")


class TurnInputError(ValueError):
    def __init__(self, message: str, **payload: Any) -> None:
        super().__init__(message)
        self.payload = {"error": message, **payload}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_slug(value: str, fallback: str = "session") -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return (slug or fallback)[:90]


def contextualize_short_turn(transcript: str, previous_agent_text: str | None) -> str:
    lowered = transcript.lower().strip()
    if not previous_agent_text:
        return transcript
    short_followups = {
        "yes",
        "yes please",
        "sure",
        "ok",
        "okay",
        "tell me",
        "tell me more",
        "continue",
        "go ahead",
    }
    if lowered in short_followups or len(lowered.split()) <= 3:
        return f"Previous agent message: {previous_agent_text}. Customer follow-up: {transcript}"
    return transcript


def greeting_for_mode(mode: str, response_register: str | None = None) -> tuple[str, str | None]:
    if mode == "q1_lendingkart":
        return (
            "Hello, welcome to the Lendingkart business loan assistant. I can help with eligibility, "
            "documents, loan amount, fees, application steps, or repayment questions. How can I help you today?",
            None,
        )
    if mode == "q3_philippines":
        return (
            "Magandang araw po. Tutulungan ko po kayo sa life insurance coverage, premium, beneficiary, "
            "o rider options. Ano po ang gusto ninyong itanong?",
            "filipino_native_greeting",
        )
    if mode == "q3_indonesia":
        return (
            "Selamat siang. Saya bisa bantu soal cicilan, jatuh tempo, denda, tenor, DP, "
            "atau opsi pembiayaan. Ada yang bisa saya bantu?",
            "indonesian_native_greeting",
        )
    raise ValueError(f"Unsupported agent mode: {mode}")


class WebCallApp:
    def __init__(
        self,
        project_root: Path,
        output_dir: Path,
        tts_provider_name: str,
        stt_provider_name: str,
        stt_min_confidence: float,
    ) -> None:
        self.project_root = project_root
        self.output_dir = output_dir
        self.tts_provider_name = tts_provider_name
        self.stt_provider_name = stt_provider_name
        self.stt_min_confidence = stt_min_confidence
        self.agent = LendingkartVoiceAgent.from_project_root(project_root)
        self.q3_market_components = {
            "q3_philippines": Q3MarketComponent.from_component_dir(
                PROJECT_SRC / "q3_market_components" / "philippines"
            ),
            "q3_indonesia": Q3MarketComponent.from_component_dir(
                PROJECT_SRC / "q3_market_components" / "indonesia"
            ),
        }
        self.tts_provider = get_tts_provider(tts_provider_name)
        self.stt_provider = None if stt_provider_name == "none" else get_stt_provider(stt_provider_name)
        self.sessions: dict[str, WebSession] = {}
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_session(self, session_id: str) -> WebSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = WebSession(session_id=session_id)
        return self.sessions[session_id]

    def handle_turn(
        self,
        session_id: str,
        transcript: str,
        mode: str = "q1_lendingkart",
        response_register: str | None = None,
        caller_audio: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        clean_transcript = transcript.strip()
        if mode not in {"q1_lendingkart", "q3_philippines", "q3_indonesia"}:
            raise ValueError(f"Unsupported agent mode: {mode}")

        session = self.get_session(session_id)
        turn_number = len(session.turns) + 1
        session_dir = self.output_dir / safe_slug(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        caller_audio_saved = self.save_caller_audio(session_dir, turn_number, caller_audio)
        stt_result: SttResult | None = None
        stt_error: str | None = None

        if not clean_transcript:
            stt_started = time.perf_counter()
            stt_result, stt_error = self.transcribe_saved_caller_audio(caller_audio_saved)
            stt_ended = time.perf_counter()
            if stt_result and stt_result.transcript.strip():
                confidence = stt_result.confidence
                if stt_result.provider == "windows_sapi" and confidence is not None and confidence < self.stt_min_confidence:
                    heard = stt_result.transcript.strip()
                    raise TurnInputError(
                        (
                            f"I heard '{heard}', but confidence was only {confidence:.2f}. "
                            "Please repeat more clearly, move closer to the mic, or edit the text box and send as text."
                        ),
                        error_type="low_confidence_stt",
                        heard_text=heard,
                        stt_confidence=round(confidence, 3),
                        stt_provider=stt_result.provider,
                        caller_audio=caller_audio_saved,
                    )
                clean_transcript = stt_result.transcript.strip()
            else:
                reason = stt_error or "No usable caller audio was received."
                raise TurnInputError(
                    f"No transcript captured, and server-side STT could not recover it. {reason}",
                    error_type="stt_failed",
                    stt_provider=self.stt_provider_name,
                    caller_audio=caller_audio_saved,
                )
        else:
            stt_started = started
            stt_ended = started

        agent_query = contextualize_short_turn(clean_transcript, session.last_agent_text)
        agent_started = time.perf_counter()
        if mode == "q1_lendingkart":
            agent_response = self.agent.respond(agent_query, session_id=session_id)
            spoken_text = agent_response["response"]["spoken_text"]
            action = agent_response["response"]["action"]
            retrieval_status = agent_response["response"]["retrieval_status"]
            citations = agent_response["grounding"]["citations"]
            response_payload = agent_response
        else:
            q3_result = self.q3_market_components[mode].respond(
                clean_transcript,
                response_register=response_register,
            )
            localized_response = q3_result.localized_response
            spoken_text = localized_response.response_text
            action = localized_response.action
            retrieval_status = q3_result.retrieval_status
            citations = q3_result.citations
            response_payload = q3_result.to_dict()
        agent_ended = time.perf_counter()

        audio_path = session_dir / f"turn_{turn_number:02d}_agent_response.wav"
        tts_started = time.perf_counter()
        tts_result = self.tts_provider.synthesize(spoken_text, audio_path)
        tts_ended = time.perf_counter()

        audio_url = None
        if tts_result.audio_path:
            audio_url = f"/audio/{safe_slug(session_id)}/{Path(tts_result.audio_path).name}"

        turn = {
            "turn_number": turn_number,
            "generated_at_utc": utc_now(),
            "mode": mode,
            "response_register": localized_response.response_register if mode != "q1_lendingkart" else None,
            "customer": {
                "transcript": clean_transcript,
                "agent_query": agent_query,
                "stt_provider": stt_result.provider if stt_result else "browser_web_speech_api_or_typed_text",
                "stt": stt_result.to_dict() if stt_result else None,
                "stt_error": stt_error,
                "caller_audio": caller_audio_saved,
            },
            "agent": {
                "spoken_text": spoken_text,
                "action": action,
                "retrieval_status": retrieval_status,
                "citations": citations,
                "audio_path": tts_result.audio_path,
                "audio_url": audio_url,
                "raw_response": response_payload,
            },
            "latency_ms": {
                "stt": round((stt_ended - stt_started) * 1000, 3),
                "agent_response": round((agent_ended - agent_started) * 1000, 3),
                "tts": round((tts_ended - tts_started) * 1000, 3),
                "end_to_end": round((tts_ended - started) * 1000, 3),
            },
        }
        session.turns.append(turn)
        self.write_session_artifacts(session)

        return {
            "session_id": session_id,
            "mode": mode,
            "response_register": turn["response_register"],
            "turn_number": turn_number,
            "customer_transcript": clean_transcript,
            "spoken_text": turn["agent"]["spoken_text"],
            "action": turn["agent"]["action"],
            "retrieval_status": turn["agent"]["retrieval_status"],
            "citations": citations,
            "audio_url": audio_url,
            "latency_ms": turn["latency_ms"],
            "tts": tts_result.to_dict(),
            "stt": stt_result.to_dict() if stt_result else None,
            "stt_error": stt_error,
            "caller_audio": caller_audio_saved,
        }

    def handle_greeting(
        self,
        session_id: str,
        mode: str = "q1_lendingkart",
        response_register: str | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        if mode not in {"q1_lendingkart", "q3_philippines", "q3_indonesia"}:
            raise ValueError(f"Unsupported agent mode: {mode}")

        spoken_text, greeting_register = greeting_for_mode(mode, response_register)
        session_dir = self.output_dir / safe_slug(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        audio_path = session_dir / f"greeting_{safe_slug(mode)}.wav"

        tts_started = time.perf_counter()
        tts_result = self.tts_provider.synthesize(spoken_text, audio_path)
        tts_ended = time.perf_counter()

        audio_url = None
        if tts_result.audio_path:
            audio_url = f"/audio/{safe_slug(session_id)}/{Path(tts_result.audio_path).name}"

        return {
            "session_id": session_id,
            "mode": mode,
            "response_register": greeting_register if mode != "q1_lendingkart" else None,
            "spoken_text": spoken_text,
            "audio_url": audio_url,
            "action": "greeting",
            "retrieval_status": "scripted_greeting",
            "latency_ms": {
                "tts": round((tts_ended - tts_started) * 1000, 3),
                "end_to_end": round((tts_ended - started) * 1000, 3),
            },
            "tts": tts_result.to_dict(),
        }

    def transcribe_saved_caller_audio(
        self,
        caller_audio_saved: dict[str, Any] | None,
    ) -> tuple[SttResult | None, str | None]:
        if self.stt_provider is None:
            return None, "Server-side STT is disabled."
        if not caller_audio_saved or not caller_audio_saved.get("audio_path"):
            return None, "No caller audio file was saved."
        audio_path = Path(str(caller_audio_saved["audio_path"]))
        if not audio_path.exists():
            return None, f"Caller audio file does not exist: {audio_path}"
        if self.stt_provider_name == "windows_sapi" and audio_path.suffix.lower() != ".wav":
            return None, f"Windows SAPI can only transcribe WAV audio, received {audio_path.suffix or 'unknown'}."
        try:
            return self.stt_provider.transcribe(audio_path=audio_path), None
        except Exception as exc:
            message = str(exc)
            if "Speech Recognition is not available" in message or "Recognition engines cannot be found" in message:
                message = (
                    "Windows Speech Recognition is not installed on this machine. "
                    "Use Chrome/Edge browser speech recognition, type the transcript, "
                    "or run with --stt-provider openai after configuring an API key."
                )
            return None, message

    def save_caller_audio(
        self,
        session_dir: Path,
        turn_number: int,
        caller_audio: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not caller_audio or not caller_audio.get("base64"):
            return None

        mime_type = str(caller_audio.get("mime_type") or "audio/webm").lower()
        if "wav" in mime_type:
            extension = ".wav"
        elif "ogg" in mime_type:
            extension = ".ogg"
        elif "mp4" in mime_type or "m4a" in mime_type:
            extension = ".m4a"
        else:
            extension = ".webm"

        try:
            raw = base64.b64decode(str(caller_audio["base64"]), validate=False)
        except Exception as exc:
            return {
                "audio_path": None,
                "mime_type": mime_type,
                "byte_count": 0,
                "source": "browser_web_audio_recorder",
                "error": f"Could not decode caller audio: {exc}",
            }
        audio_path = session_dir / f"turn_{turn_number:02d}_customer{extension}"
        audio_path.write_bytes(raw)
        return {
            "audio_path": str(audio_path),
            "mime_type": mime_type,
            "byte_count": len(raw),
            "source": "browser_web_audio_recorder",
        }

    def write_session_artifacts(self, session: WebSession) -> None:
        session_dir = self.output_dir / safe_slug(session.session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        json_path = session_dir / "session.json"
        json_path.write_text(
            json.dumps(
                {
                    "session_id": session.session_id,
                    "generated_at_utc": utc_now(),
                    "turn_count": len(session.turns),
                    "turns": session.turns,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        transcript_lines = [f"Session: {session.session_id}", f"Turns: {len(session.turns)}", ""]
        for turn in session.turns:
            transcript_lines.append(f"Customer {turn['turn_number']}: {turn['customer']['transcript']}")
            transcript_lines.append(f"Agent {turn['turn_number']}: {turn['agent']['spoken_text']}")
            if turn["agent"]["citations"]:
                citation = turn["agent"]["citations"][0]
                transcript_lines.append(f"Top source: {citation.get('label')} ({citation.get('url')})")
            transcript_lines.append("")
        (session_dir / "transcript.txt").write_text("\n".join(transcript_lines), encoding="utf-8")


def make_handler(app: WebCallApp) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "LendingkartWebCall/1.0"

        def log_message(self, format: str, *args: Any) -> None:
            if sys.stderr:
                sys.stderr.write(
                    "%s - - [%s] %s\n"
                    % (self.client_address[0], self.log_date_time_string(), format % args)
                )

        def send_text(self, status: int, body: str, content_type: str = "text/plain; charset=utf-8") -> None:
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def send_json(self, status: int, payload: dict[str, Any]) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/index.html"}:
                self.send_text(HTTPStatus.OK, HTML_PAGE, "text/html; charset=utf-8")
                return

            if parsed.path.startswith("/audio/"):
                relative = parsed.path.removeprefix("/audio/").replace("/", "\\")
                audio_path = app.output_dir / relative
                if not audio_path.exists() or not audio_path.is_file():
                    self.send_text(HTTPStatus.NOT_FOUND, "Audio not found")
                    return
                content_type = mimetypes.guess_type(str(audio_path))[0] or "audio/wav"
                data = audio_path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            if parsed.path == "/api/session":
                params = parse_qs(parsed.query)
                session_id = (params.get("session_id") or [""])[0]
                session = app.get_session(session_id) if session_id else None
                self.send_json(HTTPStatus.OK, {"session": session.__dict__ if session else None})
                return

            self.send_text(HTTPStatus.NOT_FOUND, "Not found")

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path not in {"/api/turn", "/api/greeting"}:
                self.send_text(HTTPStatus.NOT_FOUND, "Not found")
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                session_id = str(payload.get("session_id") or f"web_{int(time.time())}")
                mode = str(payload.get("mode") or "q1_lendingkart")
                response_register = str(payload.get("response_register") or "auto")
                if parsed.path == "/api/greeting":
                    result = app.handle_greeting(
                        session_id,
                        mode=mode,
                        response_register=response_register,
                    )
                else:
                    transcript = str(payload.get("transcript") or "")
                    caller_audio = payload.get("caller_audio")
                    result = app.handle_turn(
                        session_id,
                        transcript,
                        mode=mode,
                        response_register=response_register,
                        caller_audio=caller_audio,
                    )
                self.send_json(HTTPStatus.OK, result)
            except TurnInputError as exc:
                self.send_json(HTTPStatus.BAD_REQUEST, exc.payload)
            except Exception as exc:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    return Handler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the browser web-calling interface for the Lendingkart voice agent.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--tts-provider", default="windows_sapi", choices=["windows_sapi", "text_only"])
    parser.add_argument(
        "--stt-provider",
        default="windows_sapi",
        choices=["windows_sapi", "faster_whisper", "openai", "none"],
    )
    parser.add_argument("--stt-min-confidence", type=float, default=0.30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    output_dir = args.output_dir or (project_root / "demos" / "web_calling")
    app = WebCallApp(
        project_root=project_root,
        output_dir=output_dir.resolve(),
        tts_provider_name=args.tts_provider,
        stt_provider_name=args.stt_provider,
        stt_min_confidence=args.stt_min_confidence,
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))
    print(f"Web calling interface: http://{args.host}:{args.port}")
    print(f"Session artifacts: {output_dir.resolve()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web calling server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
