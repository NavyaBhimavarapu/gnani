/**
 * VoiceDose - Patient Voice Interaction App
 * Handles:
 * - Language selection (Telugu, Hindi, English)
 * - Fetching active medication dose
 * - Timbre TTS reminder speech playback
 * - MediaRecorder browser audio capture with visualizer
 * - Prisma STT transcription submission & intent confirmation
 * - Spoken response autoplay
 */

// Application state
const state = {
  currentLang: "te-IN",
  activeDose: null,
  patient: null,
  isRecording: false,
  mediaRecorder: null,
  audioChunks: [],
  audioStream: null,
  audioContext: null,
  isPlayingAudio: false,
};

// UI Localized strings for language switches
const I18N = {
  "te-IN": {
    greeting: "నమస్కారం, అనసూయ గారు!",
    condition: "74 ఏళ్ళు • రక్తపోటు (BP) & మధుమేహం",
    listenReminder: "రిమైండర్ వినండి (Timbre TTS)",
    voiceHeading: "మీ గొంతుతో సమాధానం ఇవ్వండి",
    voiceSubheading: 'కింది పెద్ద మైక్ బటన్ నొక్కి మాట్లాడండి: "వేసుకున్నాను" (Taken) లేదా "ఇంకా లేదు" (Not yet) లేదా "తర్వాత" (Snooze)',
    tapToSpeak: "మాట్లాడటానికి నొక్కండి",
    listening: "వింటున్నాను... మాట్లాడండి!",
    processing: "Gnani Prisma STT తో ప్రాసెస్ చేస్తోంది...",
    instruction: "ఒకసారి నొక్కి మాట్లాడండి, పూర్తయ్యాక మళ్ళీ నొక్కండి",
    quickPhrases: [
      { text: "వేసుకున్నాను", label: "✅ వేసుకున్నాను (Taken)", type: "pill-taken" },
      { text: "ఇంకా తీసుకోలేదు", label: "⏳ ఇంకా లేదు (Not Yet)", type: "pill-notyet" },
      { text: "పది నిమిషాల తర్వాత", label: "⏰ తర్వాత / స్నూజ్ (Snooze)", type: "pill-snooze" },
      { text: "మందు వేసుకున్నాను అండి", label: "💊 మందు వేసుకున్నాను", type: "pill-taken" },
    ],
  },
  "hi-IN": {
    greeting: "नमस्ते, अनसूया जी!",
    condition: "74 वर्ष • ब्लड प्रेशर & शुगर",
    listenReminder: "रिमाइंडर सुनें (Timbre TTS)",
    voiceHeading: "अपनी आवाज़ से जवाब दें",
    voiceSubheading: 'नीचे बड़े माइक बटन को दबाकर बोलें: "दवाई ले ली है" (Taken) या "अभी नहीं ली" (Not yet) या "बाद में याद दिलाना" (Snooze)',
    tapToSpeak: "बोलने के लिए दबाएं",
    listening: "सुन रहे हैं... कृपया बोलिए!",
    processing: "Gnani Prisma STT आवाज़ पहचान रहा है...",
    instruction: "एक बार दबाकर बोलें, पूरा होने पर दोबारा दबाएं",
    quickPhrases: [
      { text: "दवाई ले ली है", label: "✅ दवाई ले ली है (Taken)", type: "pill-taken" },
      { text: "अभी नहीं ली", label: "⏳ अभी नहीं ली (Not Yet)", type: "pill-notyet" },
      { text: "दस मिनट बाद याद दिलाना", label: "⏰ बाद में (Snooze)", type: "pill-snooze" },
      { text: "हाँ खा ली", label: "💊 हाँ खा ली", type: "pill-taken" },
    ],
  },
  "en-IN": {
    greeting: "Hello, Anasuya ji!",
    condition: "74 yrs • Hypertension & Diabetes",
    listenReminder: "Listen to Reminder (Timbre TTS)",
    voiceHeading: "Reply with Your Voice",
    voiceSubheading: 'Tap the big microphone below and say: "I took it" (Taken) or "Not yet" (Not yet) or "Remind me in 10 minutes" (Snooze)',
    tapToSpeak: "Tap to Speak",
    listening: "Listening... Please speak!",
    processing: "Transcribing with Gnani Prisma STT...",
    instruction: "Tap once to start recording, tap again when finished",
    quickPhrases: [
      { text: "I have taken my medicine", label: "✅ I have taken it (Taken)", type: "pill-taken" },
      { text: "Not yet", label: "⏳ Not yet (Not Yet)", type: "pill-notyet" },
      { text: "Remind me in 10 minutes", label: "⏰ Remind later (Snooze)", type: "pill-snooze" },
      { text: "Already took it", label: "💊 Already took it", type: "pill-taken" },
    ],
  },
};

// DOM elements
const langButtonsContainer = document.getElementById("langButtonsContainer");
const patientGreeting = document.getElementById("patientGreeting");
const patientCondition = document.getElementById("patientCondition");
const liveDate = document.getElementById("liveDate");
const liveClock = document.getElementById("liveClock");

const doseSlotBadge = document.getElementById("doseSlotBadge");
const doseStatusBadge = document.getElementById("doseStatusBadge");
const medName = document.getElementById("medName");
const medDosage = document.getElementById("medDosage");
const medPurpose = document.getElementById("medPurpose");
const medInstructionsText = document.getElementById("medInstructionsText");

const btnListenReminder = document.getElementById("btnListenReminder");
const listenLabel = document.getElementById("listenLabel");
const listenIcon = document.getElementById("listenIcon");

const btnRecord = document.getElementById("btnRecord");
const micStatusLabel = document.getElementById("micStatusLabel");
const micInstruction = document.getElementById("micInstruction");
const voiceActionHeading = document.getElementById("voiceActionHeading");
const voiceActionSubheading = document.getElementById("voiceActionSubheading");
const waveformVisualizer = document.getElementById("waveformVisualizer");

const interactionResultCard = document.getElementById("interactionResultCard");
const resultEngineTag = document.getElementById("resultEngineTag");
const resultIntentBadge = document.getElementById("resultIntentBadge");
const resultTranscriptText = document.getElementById("resultTranscriptText");
const resultConfirmationText = document.getElementById("resultConfirmationText");

const quickPhrasesRow = document.getElementById("quickPhrasesRow");
const ttsAudioPlayer = document.getElementById("ttsAudioPlayer");

/**
 * Initialize app on page load
 */
document.addEventListener("DOMContentLoaded", () => {
  initLiveClock();
  setupLanguageSwitchers();
  setupAudioReminder();
  setupVoiceRecording();
  loadPatientAndDose();
  renderQuickPhrases();
});

/**
 * Keep top header clock updated
 */
function initLiveClock() {
  const update = () => {
    const now = new Date();
    liveDate.textContent = now.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
    liveClock.textContent = now.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };
  update();
  setInterval(update, 1000);
}

/**
 * Language switcher event listeners
 */
function setupLanguageSwitchers() {
  const buttons = langButtonsContainer.querySelectorAll(".lang-pill");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.currentLang = btn.getAttribute("data-lang");
      applyLanguageChanges();
    });
  });
}

function applyLanguageChanges() {
  const l = I18N[state.currentLang] || I18N["te-IN"];
  patientGreeting.textContent = l.greeting;
  patientCondition.textContent = l.condition;
  listenLabel.textContent = l.listenReminder;
  voiceActionHeading.textContent = l.voiceHeading;
  voiceActionSubheading.innerHTML = l.voiceSubheading;
  micStatusLabel.textContent = state.isRecording ? l.listening : l.tapToSpeak;
  micInstruction.textContent = l.instruction;
  renderQuickPhrases();
}

/**
 * Render fail-safe quick simulation test pills
 */
function renderQuickPhrases() {
  const l = I18N[state.currentLang] || I18N["te-IN"];
  quickPhrasesRow.innerHTML = "";

  l.quickPhrases.forEach((item) => {
    const pill = document.createElement("button");
    pill.className = `phrase-pill ${item.type}`;
    pill.innerHTML = item.label;
    pill.addEventListener("click", () => {
      simulateSpokenResponse(item.text);
    });
    quickPhrasesRow.appendChild(pill);
  });
}

/**
 * Load patient profile and today's active dose from backend
 */
async function loadPatientAndDose() {
  try {
    const res = await fetch("/api/patient");
    if (!res.ok) throw new Error("Failed to load patient data");
    const data = await res.json();
    state.patient = data.patient;
    state.activeDose = data.active_dose;
    updateDoseUI(state.activeDose);
  } catch (err) {
    console.error("Error loading patient & dose:", err);
  }
}

/**
 * Update active dose card in the UI
 */
function updateDoseUI(dose) {
  if (!dose) return;
  state.activeDose = dose;

  medName.textContent = dose.medicine_name;
  medDosage.textContent = dose.dosage;
  medPurpose.textContent = dose.purpose || "Medication";
  medInstructionsText.textContent = dose.instructions || "Take with water";

  // Slot badge
  doseSlotBadge.textContent = `${getSlotIcon(dose.slot_name)} ${dose.slot_name} Dose • ${dose.scheduled_time}`;

  // Status badge
  updateStatusBadge(dose.status);
}

function getSlotIcon(slot) {
  if (slot === "Morning") return "🌅";
  if (slot === "Afternoon") return "☀️";
  if (slot === "Evening") return "🌇";
  if (slot === "Night") return "🌙";
  return "⏰";
}

function updateStatusBadge(status) {
  doseStatusBadge.className = `status-badge status-${status}`;
  if (status === "taken") {
    doseStatusBadge.textContent = "✅ Dose Taken & Logged";
  } else if (status === "snoozed") {
    doseStatusBadge.textContent = "⏰ Snoozed (10 mins)";
  } else if (status === "missed") {
    doseStatusBadge.textContent = "⚠️ Missed";
  } else {
    doseStatusBadge.textContent = "● Pending Confirmation";
  }
}

/**
 * Step 1: Reminder is spoken aloud in the chosen language using Gnani Timbre TTS
 */
function setupAudioReminder() {
  btnListenReminder.addEventListener("click", async () => {
    if (!state.activeDose) return;

    if (state.isPlayingAudio) {
      ttsAudioPlayer.pause();
      state.isPlayingAudio = false;
      resetListenButton();
      return;
    }

    try {
      listenLabel.textContent = "Synthesizing Speech (Gnani Timbre)...";
      btnListenReminder.disabled = true;

      const res = await fetch("/api/reminder-speech", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dose_id: state.activeDose.id,
          language_code: state.currentLang,
        }),
      });

      if (!res.ok) {
        throw new Error(`TTS API failed with HTTP ${res.status}`);
      }

      const blob = await res.blob();
      const audioUrl = URL.createObjectURL(blob);
      ttsAudioPlayer.src = audioUrl;

      btnListenReminder.disabled = false;
      btnListenReminder.classList.add("playing");
      listenIcon.textContent = "⏹️";
      listenLabel.textContent = "Speaking Reminder aloud...";
      state.isPlayingAudio = true;

      await ttsAudioPlayer.play();

      ttsAudioPlayer.onended = () => {
        resetListenButton();
      };
    } catch (err) {
      console.error("Reminder playback error:", err);
      alert(`Could not play reminder speech: ${err.message}`);
      resetListenButton();
    }
  });
}

function resetListenButton() {
  state.isPlayingAudio = false;
  btnListenReminder.disabled = false;
  btnListenReminder.classList.remove("playing");
  listenIcon.textContent = "🔊";
  const l = I18N[state.currentLang] || I18N["te-IN"];
  listenLabel.textContent = l.listenReminder;
}

/**
 * Step 2: The user replies by voice via a big mic button (record audio in browser)
 */
function setupVoiceRecording() {
  btnRecord.addEventListener("click", () => {
    if (state.isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  });
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.audioStream = stream;
    state.audioChunks = [];

    // Check supported types (prefer webm, fallback to ogg or wav)
    let options = {};
    if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
      options = { mimeType: "audio/webm;codecs=opus" };
    } else if (MediaRecorder.isTypeSupported("audio/webm")) {
      options = { mimeType: "audio/webm" };
    } else if (MediaRecorder.isTypeSupported("audio/ogg")) {
      options = { mimeType: "audio/ogg" };
    }

    state.mediaRecorder = new MediaRecorder(stream, options);

    state.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        state.audioChunks.push(event.data);
      }
    };

    state.mediaRecorder.onstop = () => {
      const mimeType = state.mediaRecorder.mimeType || "audio/webm";
      const audioBlob = new Blob(state.audioChunks, { type: mimeType });
      // Stop tracks to release mic
      if (state.audioStream) {
        state.audioStream.getTracks().forEach((track) => track.stop());
      }
      // Send audio to Gnani STT
      sendAudioToPrismaSTT(audioBlob);
    };

    state.mediaRecorder.start();
    state.isRecording = true;

    // UI Updates for recording
    btnRecord.classList.add("recording");
    waveformVisualizer.classList.add("active");
    const l = I18N[state.currentLang] || I18N["te-IN"];
    micStatusLabel.textContent = l.listening;
    micInstruction.textContent = "Speaking... click again to finish.";
  } catch (err) {
    console.error("Microphone access error:", err);
    alert(
      "Microphone access denied or not available. You can also use the 'Quick Test Voice Phrases' below to test with 1-click!"
    );
  }
}

function stopRecording() {
  if (!state.mediaRecorder || !state.isRecording) return;
  state.isRecording = false;
  state.mediaRecorder.stop();

  // UI Updates for processing
  btnRecord.classList.remove("recording");
  btnRecord.classList.add("processing");
  waveformVisualizer.classList.remove("active");
  const l = I18N[state.currentLang] || I18N["te-IN"];
  micStatusLabel.textContent = l.processing;
}

/**
 * Step 3: Send audio to Gnani Prisma STT, match transcript against keywords
 * Step 4: Log in SQLite and speak confirmation with Timbre
 */
async function sendAudioToPrismaSTT(audioBlob) {
  if (!state.activeDose) return;

  try {
    const formData = new FormData();
    formData.append("audio", audioBlob, "elder_response.webm");
    formData.append("dose_id", state.activeDose.id);
    formData.append("language_code", state.currentLang);

    const res = await fetch("/api/process-voice", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || `Server error: HTTP ${res.status}`);
    }

    const data = await res.json();
    handleVoiceProcessingSuccess(data);
  } catch (err) {
    console.error("Voice processing error:", err);
    alert(`Voice processing error: ${err.message}`);
  } finally {
    btnRecord.classList.remove("processing");
    const l = I18N[state.currentLang] || I18N["te-IN"];
    micStatusLabel.textContent = l.tapToSpeak;
    micInstruction.textContent = l.instruction;
  }
}

/**
 * Handle successful voice processing (STT + Intent match + TTS confirmation)
 */
function handleVoiceProcessingSuccess(data) {
  // 1. Show Result Card
  interactionResultCard.classList.add("visible");
  resultTranscriptText.textContent = `"${data.transcript}"`;
  resultConfirmationText.textContent = data.confirmation_text;

  // 2. Intent badge styling
  resultIntentBadge.className = "status-badge";
  if (data.intent === "taken") {
    resultIntentBadge.classList.add("status-taken");
    resultIntentBadge.textContent = "Intent: Taken ✅";
  } else if (data.intent === "snooze") {
    resultIntentBadge.classList.add("status-snoozed");
    resultIntentBadge.textContent = "Intent: Snooze ⏰";
  } else if (data.intent === "not_yet") {
    resultIntentBadge.classList.add("status-pending");
    resultIntentBadge.textContent = "Intent: Not Yet ⏳";
  } else {
    resultIntentBadge.textContent = "Intent: Unclear 🤔";
  }

  // 3. Update Dose status in the UI
  if (data.dose) {
    updateDoseUI(data.dose);
  }

  // 4. Autoplay spoken confirmation from Gnani Timbre TTS
  if (data.audio_base64) {
    playBase64Audio(data.audio_base64);
  }
}

/**
 * Helper to play base64-encoded audio returned from Timbre TTS
 */
function playBase64Audio(base64String) {
  try {
    const audioSrc = `data:audio/wav;base64,${base64String}`;
    ttsAudioPlayer.src = audioSrc;
    ttsAudioPlayer.play().catch((err) => {
      console.warn("Autoplay was prevented by browser policy; user can click to hear:", err);
    });
  } catch (err) {
    console.error("Audio playback failure:", err);
  }
}

/**
 * Simulation helper for 60-second video demo or environments without physical mic
 */
async function simulateSpokenResponse(phraseText) {
  if (!state.activeDose) return;

  btnRecord.classList.add("processing");
  const l = I18N[state.currentLang] || I18N["te-IN"];
  micStatusLabel.textContent = `Processing "${phraseText}"...`;

  try {
    const res = await fetch("/api/simulate-voice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dose_id: state.activeDose.id,
        text: phraseText,
        language_code: state.currentLang,
      }),
    });

    if (!res.ok) {
      throw new Error(`Simulation failed: HTTP ${res.status}`);
    }

    const data = await res.json();
    handleVoiceProcessingSuccess(data);
  } catch (err) {
    console.error("Simulation error:", err);
    alert(`Simulation failed: ${err.message}`);
  } finally {
    btnRecord.classList.remove("processing");
    micStatusLabel.textContent = l.tapToSpeak;
  }
}
