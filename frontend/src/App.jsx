import React, { useState, useEffect, useRef } from 'react';

const WS_URL = `ws://${window.location.hostname}:8000/ws/audio`;
const API_URL = `http://${window.location.hostname}:8000`;

export default function App() {
  const [selectedLanguage, setSelectedLanguage] = useState('indic-auto');
  const [wsConnected, setWsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const [agentText, setAgentText] = useState('');
  const [liveTranscript, setLiveTranscript] = useState('');
  const [customText, setCustomText] = useState('');
  const [dangerAlert, setDangerAlert] = useState(null);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Form State
  const [record, setRecord] = useState({
    beneficiary_id: '',
    visit_type: '',
    weight: '',
    vaccinations_due: [],
    supplements_given: [],
    next_visit_date: '',
    status: 'IDLE'
  });

  // Database Records
  const [savedRecords, setSavedRecords] = useState([]);

  const wsRef = useRef(null);
  const audioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const processorRef = useRef(null);
  const playbackContextRef = useRef(null);
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);

  // Connect WebSocket
  useEffect(() => {
    connectWebSocket();
    loadSavedRecords();

    return () => {
      if (wsRef.current) wsRef.current.close();
      stopMicrophone();
    };
  }, []);

  const connectWebSocket = () => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
    };

    ws.onclose = () => {
      setWsConnected(false);
      setTimeout(connectWebSocket, 3000);
    };

    ws.onmessage = async (event) => {
      if (event.data instanceof Blob) {
        // Binary audio chunk from Gnani Timbre TTS
        const arrayBuffer = await event.data.arrayBuffer();
        queueAudioForPlayback(arrayBuffer);
      } else {
        try {
          const data = jsonParse(event.data);
          handleServerEvent(data);
        } catch (e) {
          console.error('Failed to parse WS message', e);
        }
      }
    };
  };

  const jsonParse = (str) => JSON.parse(str);

  const handleServerEvent = (data) => {
    const { event } = data;

    if (event === 'transcript') {
      setLiveTranscript(data.text);
    } else if (event === 'state_update') {
      const rec = data.record || {};
      setRecord({
        beneficiary_id: rec.beneficiary_id || '',
        visit_type: rec.visit_type || '',
        weight: rec.weight !== null && rec.weight !== undefined ? rec.weight : '',
        vaccinations_due: rec.vaccinations_due || [],
        supplements_given: rec.supplements_given || [],
        next_visit_date: rec.next_visit_date || '',
        status: data.status || 'UPDATED'
      });
      setSavedSuccess(false);
    } else if (event === 'danger_alert') {
      setDangerAlert({
        alert: data.alert,
        signs: data.signs || []
      });
    } else if (event === 'agent_speech_start') {
      setAgentSpeaking(true);
      setAgentText(data.text);
    } else if (event === 'agent_speech_end') {
      setAgentSpeaking(false);
    } else if (event === 'record_saved') {
      setSavedSuccess(true);
      loadSavedRecords();
    } else if (event === 'barge_in_detected') {
      stopAudioPlayback();
      setAgentSpeaking(false);
    }
  };

  const loadSavedRecords = async () => {
    try {
      const res = await fetch(`${API_URL}/records`);
      if (res.ok) {
        const data = await res.json();
        setSavedRecords(data);
      }
    } catch (e) {
      console.warn('Could not load records', e);
    }
  };

  // Audio Playback
  const queueAudioForPlayback = async (arrayBuffer) => {
    if (!playbackContextRef.current) {
      playbackContextRef.current = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    }
    const ctx = playbackContextRef.current;
    if (ctx.state === 'suspended') {
      await ctx.resume();
    }

    // Convert raw 16-bit PCM to AudioBuffer
    const int16Array = new Int16Array(arrayBuffer);
    if (int16Array.length === 0) return;

    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    const audioBuffer = ctx.createBuffer(1, float32Array.length, 16000);
    audioBuffer.copyToChannel(float32Array, 0);

    audioQueueRef.current.push(audioBuffer);
    if (!isPlayingRef.current) {
      playNextQueuedAudio();
    }
  };

  const playNextQueuedAudio = () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }

    isPlayingRef.current = true;
    const ctx = playbackContextRef.current;
    const buffer = audioQueueRef.current.shift();

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.onended = () => {
      playNextQueuedAudio();
    };
    source.start();
  };

  const stopAudioPlayback = () => {
    audioQueueRef.current = [];
    isPlayingRef.current = false;
  };

  // Microphone Capture (16kHz PCM streaming)
  const toggleMicrophone = async () => {
    if (isRecording) {
      stopMicrophone();
    } else {
      await startMicrophone();
    }
  };

  const startMicrophone = async () => {
    try {
      stopAudioPlayback();
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

        const inputData = e.inputBuffer.getChannelData(0);
        // Convert Float32 to 16-bit PCM
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        wsRef.current.send(pcm16.buffer);
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);
      setIsRecording(true);
    } catch (err) {
      alert('Could not access microphone: ' + err.message);
    }
  };

  const stopMicrophone = () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    setIsRecording(false);
  };

  // Text Dictation (No Talking Option)
  const sendTextNote = (textToSend) => {
    const text = textToSend || customText;
    if (!text || !wsRef.current) return;

    wsRef.current.send(JSON.stringify({ event: 'text_note', text }));
    setCustomText('');
  };

  const confirmAndSave = () => {
    if (!wsRef.current) return;
    wsRef.current.send(JSON.stringify({ event: 'confirm_record' }));
  };

  const changeLanguage = (lang) => {
    setSelectedLanguage(lang);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ event: 'set_language', language: lang }));
    }
  };

  const clearForm = () => {
    if (!wsRef.current) return;
    wsRef.current.send(JSON.stringify({ event: 'clear_record' }));
    setDangerAlert(null);
    setLiveTranscript('');
    setAgentText('');
    setSavedSuccess(false);
  };

  return (
    <div className="min-h-screen bg-slate-100 p-4 md:p-8 flex flex-col items-center">
      {/* Container */}
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-md border border-slate-200 overflow-hidden">
        
        {/* Header */}
        <div className="bg-teal-800 text-white px-6 py-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-lg font-bold">ASHA Voice Field Register</h1>
            <p className="text-xs text-teal-200">Gnani Prisma STT + Timbre TTS + Groq</p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedLanguage}
              onChange={(e) => changeLanguage(e.target.value)}
              className="bg-teal-900 text-white text-xs px-2.5 py-1 rounded border border-teal-600 focus:outline-none"
            >
              <option value="indic-auto">Auto-Detect (Hindi + Kannada)</option>
              <option value="hi-IN">Hindi (हिन्दी)</option>
              <option value="kn-IN">Kannada (ಕನ್ನಡ)</option>
              <option value="te-IN">Telugu (తెలుగు)</option>
              <option value="ta-IN">Tamil (தமிழ்)</option>
            </select>
            <div className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${wsConnected ? 'bg-green-400' : 'bg-red-400'}`}></span>
              <span className="text-xs text-teal-100">{wsConnected ? 'Live' : 'Offline'}</span>
            </div>
          </div>
        </div>

        {/* Emergency Danger Alert Banner */}
        {dangerAlert && (
          <div className="bg-red-50 border-l-4 border-red-600 p-4 m-4 rounded">
            <div className="flex items-start">
              <div>
                <p className="text-sm font-bold text-red-800">MoHFW Urgent Referral Alert</p>
                <p className="text-xs text-red-700 mt-1">{dangerAlert.alert}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {dangerAlert.signs.map((s, idx) => (
                    <span key={idx} className="bg-red-200 text-red-900 text-xs px-2 py-0.5 rounded font-medium">
                      {s.name}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Agent Speech Status */}
        {agentText && (
          <div className="bg-teal-50 border-b border-teal-100 p-4 flex items-start gap-3">
            <span className="text-xs bg-teal-600 text-white px-2 py-1 rounded font-semibold">Agent Voice</span>
            <div className="flex-1">
              <p className="text-sm text-teal-900 font-medium">"{agentText}"</p>
              {agentSpeaking && <span className="text-xs text-teal-600 font-bold animate-pulse">Playing voice audio...</span>}
            </div>
          </div>
        )}

        {/* Main Body */}
        <div className="p-6 space-y-6">

          {/* 1. Voice Speaking Section */}
          <div className="flex flex-col items-center justify-center p-6 bg-slate-50 rounded-xl border border-slate-200">
            <button
              onClick={toggleMicrophone}
              className={`w-24 h-24 rounded-full flex flex-col items-center justify-center shadow-lg transition-all ${
                isRecording
                  ? 'bg-red-600 text-white ring-4 ring-red-300 animate-pulse'
                  : 'bg-teal-700 text-white hover:bg-teal-800'
              }`}
            >
              <span className="text-sm font-bold">{isRecording ? 'Listening...' : 'Tap to Speak'}</span>
              <span className="text-[10px] opacity-80 mt-1">{isRecording ? 'Tap to stop' : 'Microphone'}</span>
            </button>
            <p className="text-xs text-slate-500 mt-3 text-center">
              {isRecording
                ? 'Speak in Hindi, Kannada, Tamil, or English code-mix'
                : 'Tap to speak your visit notes hands-free'}
            </p>
            {liveTranscript && (
              <div className="mt-3 text-xs bg-white px-3 py-1.5 rounded border border-slate-300 text-slate-700 w-full text-center">
                Spoken: "{liveTranscript}"
              </div>
            )}
          </div>

          {/* 2. Structured Visit Card Preview */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center justify-between border-b pb-3 mb-4">
              <h2 className="text-sm font-bold text-slate-800">Visit Record Form</h2>
              <span className="text-xs px-2 py-0.5 rounded font-semibold bg-slate-100 text-slate-600">
                {record.status}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-400 block">Beneficiary ID</span>
                <span className="font-semibold text-slate-800 text-sm">{record.beneficiary_id || '-'}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Visit Type</span>
                <span className="font-semibold text-slate-800 text-sm">{record.visit_type || '-'}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Weight</span>
                <span className="font-semibold text-slate-800 text-sm">
                  {record.weight ? `${record.weight} kg` : '-'}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block">Next Visit Date</span>
                <span className="font-semibold text-slate-800 text-sm">{record.next_visit_date || '-'}</span>
              </div>
              <div className="col-span-2">
                <span className="text-slate-400 block">Vaccinations Administered</span>
                <span className="font-semibold text-slate-800">
                  {record.vaccinations_due && record.vaccinations_due.length > 0
                    ? record.vaccinations_due.join(', ')
                    : '-'}
                </span>
              </div>
            </div>

            {/* Confirmation Buttons */}
            <div className="mt-5 pt-4 border-t flex gap-2 justify-end">
              <button
                onClick={clearForm}
                className="px-3 py-1.5 text-xs text-slate-600 border border-slate-300 rounded hover:bg-slate-50"
              >
                Clear Form
              </button>
              <button
                onClick={confirmAndSave}
                className="px-4 py-1.5 text-xs font-semibold bg-teal-700 text-white rounded hover:bg-teal-800"
              >
                Confirm and Save to SQLite
              </button>
            </div>

            {savedSuccess && (
              <p className="text-xs text-green-700 font-semibold mt-2 text-right">
                Record saved successfully to database!
              </p>
            )}
          </div>

          {/* 3. If You Don't Want to Talk (Preset Buttons & Text Input) */}
          <div className="bg-slate-50 rounded-xl border border-slate-200 p-4">
            <h3 className="text-xs font-bold text-slate-700 mb-2">Test Without Talking (Click or Type)</h3>
            
            {/* Quick Preset Buttons */}
            <div className="grid grid-cols-2 gap-2 mb-3">
              <button
                onClick={() =>
                  sendTextNote(
                    'Beneficiary ID 1042, Sunita Devi ka 3rd ANC checkup kiya. Weight 52 kilo hai. TT injection de diya, IFA goli dedi. Next visit 25 November.'
                  )
                }
                className="text-left p-2 text-xs bg-white border border-slate-300 rounded hover:bg-teal-50"
              >
                <span className="font-bold block text-slate-800">1. Hindi ANC Visit</span>
                <span className="text-slate-500 text-[10px]">ID 1042, 52kg, TT injection</span>
              </button>

              <button
                onClick={() => sendTextNote('Nahi, weight 54 kilo hai.')}
                className="text-left p-2 text-xs bg-white border border-slate-300 rounded hover:bg-teal-50"
              >
                <span className="font-bold block text-slate-800">2. Fix Weight Mistake</span>
                <span className="text-slate-500 text-[10px]">"Nahi, weight 54 kilo hai"</span>
              </button>

              <button
                onClick={() =>
                  sendTextNote(
                    'Beneficiary ID 1042, Sunita avara 3rd ANC checkup madidini. Weight 52 kilo ide. TT injection kottidini, agla visit 25 November.'
                  )
                }
                className="text-left p-2 text-xs bg-amber-50 border border-amber-200 rounded hover:bg-amber-100"
              >
                <span className="font-bold block text-amber-900">3. Kannada ANC Visit</span>
                <span className="text-amber-700 text-[10px]">Sunita avara ANC, 52 kilo</span>
              </button>

              <button
                onClick={() =>
                  sendTextNote(
                    'Beneficiary ID 2088, newborn visit. Maguvige thumba jwara ide mathu haalu kudiyuttilla.'
                  )
                }
                className="text-left p-2 text-xs bg-amber-50 border border-amber-200 rounded hover:bg-amber-100"
              >
                <span className="font-bold block text-amber-900">4. Kannada Danger Sign</span>
                <span className="text-amber-700 text-[10px]">Thumba jwara + haalu kudiyalla</span>
              </button>

              <button
                onClick={() =>
                  sendTextNote(
                    'Beneficiary ID 2088, newborn visit. Baby ka wazan 2.6 kilo hai, baby ko tez bukhar hai aur doodh nahi pi raha.'
                  )
                }
                className="text-left p-2 text-xs bg-red-50 border border-red-200 rounded hover:bg-red-100"
              >
                <span className="font-bold block text-red-800">5. Hindi Newborn Danger</span>
                <span className="text-red-600 text-[10px]">High fever + not feeding</span>
              </button>

              <button
                onClick={() =>
                  sendTextNote('Beneficiary 3012, 7th month pregnancy visit. Patient ko bleeding ho raha hai aur sar dard hai.')
                }
                className="text-left p-2 text-xs bg-red-50 border border-red-200 rounded hover:bg-red-100"
              >
                <span className="font-bold block text-red-800">6. Hindi Pregnancy Danger</span>
                <span className="text-red-600 text-[10px]">Vaginal bleeding alert</span>
              </button>
            </div>

            {/* Custom Text Input */}
            <div className="flex gap-2">
              <input
                type="text"
                value={customText}
                onChange={(e) => setCustomText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendTextNote()}
                placeholder="Type your visit note here in Hindi or English..."
                className="flex-1 text-xs px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-teal-600"
              />
              <button
                onClick={() => sendTextNote()}
                className="px-4 py-2 text-xs font-semibold bg-teal-800 text-white rounded hover:bg-teal-900"
              >
                Send Note
              </button>
            </div>
          </div>

          {/* 4. Saved Daily Register Table */}
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <h3 className="text-xs font-bold text-slate-700 mb-2">
              Daily Field Register (Saved in SQLite: {savedRecords.length} records)
            </h3>
            {savedRecords.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No visits saved yet.</p>
            ) : (
              <div className="divide-y divide-slate-100 text-xs">
                {savedRecords.map((r) => (
                  <div key={r.id} className="py-2 flex items-center justify-between">
                    <div>
                      <span className="font-bold text-slate-800">ID: {r.beneficiary_id || 'Unknown'}</span>
                      <span className="text-slate-500 ml-2">({r.visit_type || 'Visit'})</span>
                      <span className="text-slate-500 ml-2">• {r.weight ? `${r.weight}kg` : ''}</span>
                    </div>
                    <div>
                      {r.is_urgent_referral ? (
                        <span className="text-[10px] font-bold bg-red-100 text-red-800 px-2 py-0.5 rounded">
                          Urgent Referral
                        </span>
                      ) : (
                        <span className="text-[10px] font-semibold bg-green-100 text-green-800 px-2 py-0.5 rounded">
                          Saved
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
