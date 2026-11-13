import React, { useState, useEffect, useRef } from 'react';

const backendPort = (location.port === '3000') ? ':8000' : (location.port ? `:${location.port}` : '');
const WS_URL = (location.protocol === 'https:' ? 'wss://' : 'ws://') + (location.hostname || 'localhost') + backendPort + '/ws/audio';
const API_URL = (location.protocol === 'https:' ? 'https://' : 'http://') + (location.hostname || 'localhost') + backendPort;
const AGENT_AUDIO_RATE = 16000;

const KNOWN = [
  ['Beneficiary ID', ['beneficiary_id', 'beneficiary_code', 'mcts_id']],
  ['Name', ['beneficiary_name', 'name', 'patient_name']],
  ['Visit type', ['visit_type']],
  ['Weight (kg)', ['weight_kg', 'weight']],
  ['Vaccinations due', ['vaccinations_due', 'vaccines_due', 'vaccinations', 'vaccines']],
  ['Next visit', ['next_visit_date', 'next_visit']]
];

export default function App() {
  const [lang, setLang] = useState('kn-IN');
  const [wsStatus, setWsStatus] = useState('Connecting'); // 'Connected', 'Connecting', 'Offline'
  const [live, setLive] = useState(false);
  const [stateText, setStateText] = useState('Tap and tell me about the visit');
  const [hintText, setHintText] = useState('Speak in your language. You can mix English words.');
  const [transcript, setTranscript] = useState('Nothing yet');
  const [isFinalTranscript, setIsFinalTranscript] = useState(false);
  const [sayText, setSayText] = useState('');
  const [danger, setDanger] = useState(null); // { title, msg }
  const [record, setRecord] = useState({});
  const [dbRecords, setDbRecords] = useState([]);
  const [dbFollowUps, setDbFollowUps] = useState([]);
  const [replyTime, setReplyTime] = useState('–');

  const wsRef = useRef(null);
  const audioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const processorRef = useRef(null);
  const playingSourcesRef = useRef([]);
  const playTimeRef = useRef(0);
  const lastVoiceRef = useRef(0);
  const waitingAudioRef = useRef(false);
  const timersRef = useRef([]);

  useEffect(() => {
    connectWS();
    loadDbRecords();
    loadFollowUps();

    return () => {
      cleanup();
    };
  }, []);

  const cleanup = () => {
    timersRef.current.forEach(clearTimeout);
    stopMic();
    stopAgentAudio();
    if (wsRef.current) wsRef.current.close();
  };

  const connectWS = () => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }
    setWsStatus('Connecting');
    const ws = new WebSocket(WS_URL);
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus('Connected');
      sendWs({ event: 'set_language', language: lang });
    };

    ws.onclose = () => {
      setWsStatus('Offline');
      setTimeout(connectWS, 2500);
    };

    ws.onerror = () => {
      setWsStatus('Offline');
    };

    ws.onmessage = async (e) => {
      if (typeof e.data === 'string') {
        try {
          const msg = JSON.parse(e.data);
          handleBackendEvent(msg);
        } catch (err) {
          console.error('Failed to parse WS msg', err);
        }
      } else {
        // Binary PCM from Timbre TTS
        playPCM(e.data);
      }
    };
  };

  const sendWs = (obj) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(obj));
    }
  };

  const loadDbRecords = async () => {
    try {
      const res = await fetch(`${API_URL}/records`);
      if (res.ok) {
        const data = await res.json();
        setDbRecords(data);
      }
    } catch (e) {
      console.warn('Could not load records', e);
    }
  };

  const loadFollowUps = async () => {
    try {
      const res = await fetch(`${API_URL}/follow-ups`);
      if (res.ok) {
        const data = await res.json();
        setDbFollowUps(data.follow_ups || []);
      }
    } catch (e) {
      console.warn('Could not load follow-ups', e);
    }
  };

  const handleBackendEvent = (msg) => {
    const { event } = msg;

    if (event === 'transcript') {
      setTranscript(msg.text);
      setIsFinalTranscript(Boolean(msg.is_final));
      if (!msg.is_final) {
        setStateText('Listening…');
      }
    } else if (event === 'state_update') {
      const rec = msg.record || {};
      setRecord(rec);
      if (msg.status === 'CONFIRMING' || msg.status === 'READBACK_PENDING') {
        setStateText('Checking with you…');
        setHintText('Reviewing recorded fields and reading back…');
      } else if (msg.status === 'SAVED') {
        setStateText('Saved');
        setHintText('Tap the mic for the next visit');
        setSayText('');
        loadDbRecords();
      }
    } else if (event === 'danger_alert') {
      setDanger({
        title: 'Refer to PHC now',
        msg: msg.alert || 'Danger sign detected'
      });
    } else if (event === 'agent_speech_start') {
      stopAgentAudio();
      setSayText(msg.text || '');
      setStateText('Agent is speaking');
      setHintText('Start talking to interrupt, or tap Confirm to save');
    } else if (event === 'agent_speech_end') {
      setStateText('Tap Confirm to save');
      setHintText('Say yes or tap Confirm and save to store record');
    } else if (event === 'no_speech_detected') {
      setStateText('Tap and tell me about the visit');
      setHintText('No speech detected. Tap mic and speak.');
    } else if (event === 'barge_in_detected') {
      stopAgentAudio();
      setStateText('Listening…');
      setHintText('Go ahead, I stopped talking');
    } else if (event === 'record_saved') {
      setStateText('Saved');
      setHintText('Tap the mic for the next visit');
      setSayText('');
      loadDbRecords();
      loadFollowUps();
    }
  };

  const playPCM = (buf) => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      }
      const ctx = audioContextRef.current;
      if (waitingAudioRef.current) {
        waitingAudioRef.current = false;
        setReplyTime(`${Math.round(performance.now() - lastVoiceRef.current)} ms`);
      }

      const numSamples = buf.byteLength >> 1;
      if (!numSamples) return;

      const int16 = new Int16Array(buf, 0, numSamples);
      const float32 = new Float32Array(numSamples);
      for (let i = 0; i < numSamples; i++) {
        float32[i] = int16[i] / 32768.0;
      }

      const audioBuffer = ctx.createBuffer(1, numSamples, AGENT_AUDIO_RATE);
      audioBuffer.copyToChannel(float32, 0);

      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);

      playTimeRef.current = Math.max(playTimeRef.current, ctx.currentTime + 0.02);
      source.start(playTimeRef.current);
      playTimeRef.current += audioBuffer.duration;

      playingSourcesRef.current.push(source);
      source.onended = () => {
        playingSourcesRef.current = playingSourcesRef.current.filter((s) => s !== source);
      };
    } catch (e) {
      console.error('Audio playback error', e);
    }
  };

  const stopAgentAudio = () => {
    playingSourcesRef.current.forEach((s) => {
      try {
        s.stop();
      } catch (e) {}
    });
    playingSourcesRef.current = [];
    playTimeRef.current = 0;
  };

  const startMic = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      mediaStreamRef.current = stream;

      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      }
      const ctx = audioContextRef.current;
      await ctx.resume();

      const source = ctx.createMediaStreamSource(stream);
      const proc = ctx.createScriptProcessor(2048, 1, 1);
      processorRef.current = proc;

      const ratio = ctx.sampleRate / 16000;
      let speaking = false;
      let quiet = 0;

      proc.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);

        const micEl = document.getElementById('mic');
        if (micEl) {
          micEl.style.setProperty('--lvl', Math.min(1, rms * 8));
        }

        if (rms > 0.03) {
          if (playingSourcesRef.current.length > 0) {
            stopAgentAudio();
            sendWs({ event: 'barge_in' });
          }
          speaking = true;
          quiet = 0;
          waitingAudioRef.current = false;
        } else if (speaking && ++quiet > 6) {
          speaking = false;
          lastVoiceRef.current = performance.now();
          waitingAudioRef.current = true;
        }

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          const numSamples = Math.floor(inputData.length / ratio);
          const pcm16 = new Int16Array(numSamples);
          for (let i = 0; i < numSamples; i++) {
            const v = Math.max(-1, Math.min(1, inputData[Math.floor(i * ratio)]));
            pcm16[i] = v * 32767;
          }
          wsRef.current.send(pcm16.buffer);
        }
      };

      source.connect(proc);
      proc.connect(ctx.destination);
    } catch (err) {
      console.error('Failed to access microphone', err);
      setStateText('Microphone is blocked');
      setHintText('Allow microphone in browser settings, then tap again');
      throw err;
    }
  };

  const stopMic = () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    const micEl = document.getElementById('mic');
    if (micEl) micEl.style.setProperty('--lvl', 0);
  };

  const toggleRecording = async () => {
    if (live) {
      setLive(false);
      stopMic();
      stopAgentAudio();
      setStateText('Checking with you…');
      setHintText('Concluded dictation. Processing note and reading back…');
      const cleanTx = (transcript === 'Nothing yet' || transcript === 'Listening…') ? '' : transcript.trim();
      sendWs({ event: 'stop_recording', text: cleanTx });
    } else {
      try {
        await startMic();
        setLive(true);
        setStateText('Listening…');
        setHintText('Speak your visit notes. Tap mic again when done to read back.');
        setTranscript('Listening…');
      } catch (e) {
        // Microphone access denied
      }
    }
  };

  const handleLanguageChange = (newLang) => {
    setLang(newLang);
    sendWs({ event: 'set_language', language: newLang });
  };

  const handleConfirmSave = () => {
    sendWs({ event: 'confirm_record' });
  };

  const handleCorrection = () => {
    if (!live) toggleRecording();
    else {
      setStateText('Listening…');
      setHintText('Say what to fix, for example: weight is 54 kilo');
    }
  };

  // Follow up list computation
  const followUps = [];

  // 1. In-progress visit follow-ups
  const activeLabel = (record.beneficiary_name && record.beneficiary_id)
    ? `${record.beneficiary_name} (ID: ${record.beneficiary_id})`
    : (record.beneficiary_name || (record.beneficiary_id ? `ID: ${record.beneficiary_id}` : 'Current note'));

  if (danger) {
    followUps.push({
      html: `Refer to PHC now: ${danger.msg}`,
      urgent: true,
      label: activeLabel
    });
  }
  if (record.next_visit_date) {
    followUps.push({
      html: `Next visit: ${record.next_visit_date}`,
      active: true,
      label: activeLabel
    });
  }
  if (Array.isArray(record.vaccinations_due) && record.vaccinations_due.length > 0) {
    followUps.push({
      html: `Vaccination due: ${record.vaccinations_due.join(', ')}`,
      active: true,
      label: activeLabel
    });
  }

  // 2. Saved database follow-ups (prebuilt seed records + previously saved visits)
  dbFollowUps.forEach((f) => {
    followUps.push({
      html: `${f.details} • ${f.date}`,
      urgent: f.urgent || f.type === 'URGENT_PHC_REFERRAL',
      label: f.label || (f.beneficiary_id ? `ID: ${f.beneficiary_id}` : 'Beneficiary')
    });
  });

  const hasRecord = Object.keys(record).some((k) => record[k] && !['id', 'created_at', 'updated_at', 'status'].includes(k));

  return (
    <main>
      <header>
        <div className="brand">
          <h1>Visit register</h1>
          <span className="subtitle">Gnani Prisma STT + Timbre TTS</span>
        </div>
        <div className="header-controls">
          <select
            id="lang"
            value={lang}
            onChange={(e) => handleLanguageChange(e.target.value)}
            aria-label="Language"
          >
            <option value="kn-IN">ಕನ್ನಡ (Kannada + English)</option>
            <option value="indic-auto">Auto (Kannada/Indic)</option>
            <option value="hi-IN">हिन्दी (Hindi + English)</option>
            <option value="te-IN">తెలుగు (Telugu + English)</option>
            <option value="ta-IN">தமிழ் (Tamil + English)</option>
            <option value="en-IN">English</option>
          </select>
          <div className="status-pill" id="statusPill">
            <span className={`dot ${wsStatus === 'Connected' ? 'on' : wsStatus === 'Offline' ? 'err' : ''}`} id="statusDot"></span>
            <span id="statusTxt">{wsStatus}</span>
          </div>
        </div>
      </header>

      {danger && (
        <div id="danger" className="on" role="alert">
          <b id="dgTitle">{danger.title}</b>
          <span id="dgMsg">{danger.msg}</span>
        </div>
      )}

      <section className="card stage" aria-live="polite">
        <button
          className={`mic ${live ? 'live' : ''}`}
          id="mic"
          onClick={toggleRecording}
          aria-label="Start or stop speaking"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <rect x="9" y="3" width="6" height="12" rx="3" fill="currentColor" />
            <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
          </svg>
        </button>
        <div id="state">{stateText}</div>
        <div id="hint">{hintText}</div>
      </section>

      <section className="card">
        <h2>What I heard</h2>
        <div id="tx">
          {transcript === 'Nothing yet' ? <i>Nothing yet</i> : transcript}
        </div>
      </section>

      <section className="card">
        <h2>
          Visit record {record.danger_flag && <span className="badge">DANGER FLAG</span>}
        </h2>
        <dl className="rows" id="form">
          {KNOWN.map(([label, keys]) => {
            const val = keys.map((k) => record[k]).find((v) => v !== undefined && v !== null && v !== '');
            const displayVal = Array.isArray(val) ? val.join(', ') : val;
            return (
              <React.Fragment key={label}>
                <dt>{label}</dt>
                <dd className={displayVal ? 'flash' : 'empty'}>
                  {displayVal || '–'}
                </dd>
              </React.Fragment>
            );
          })}
        </dl>

        <div className={`say ${sayText ? 'on' : ''}`} id="say">
          <span className="say-label">Agent read-back</span>
          <span id="sayText">{sayText}</span>
        </div>

        <div className="row">
          <button className="btn" id="fix" onClick={handleCorrection}>
            Say a correction
          </button>
          <button
            className="btn pri"
            id="save"
            disabled={!hasRecord}
            onClick={handleConfirmSave}
          >
            Confirm and save
          </button>
        </div>
      </section>

      <section className="card">
        <h2>
          Follow-up list{' '}
          {followUps.length > 0 && (
            <span style={{ fontWeight: 400, textTransform: 'none', fontSize: '13px', color: 'var(--mute)' }}>
              ({followUps.length})
            </span>
          )}
        </h2>
        <ul id="fu">
          {followUps.length > 0 ? (
            followUps.map((item, idx) => (
              <li key={idx}>
                {item.urgent && (
                  <span className="badge" style={{ marginRight: '6px' }}>URGENT</span>
                )}
                {item.active && (
                  <span style={{ display: 'inline-block', background: 'var(--amber-bg)', color: 'var(--amber)', fontSize: '11px', fontWeight: 700, padding: '2px 6px', borderRadius: '6px', marginRight: '6px' }}>ACTIVE</span>
                )}
                <b>{item.label}</b>: {item.html}
              </li>
            ))
          ) : (
            <li style={{ color: 'var(--mute)', listStyle: 'none', marginLeft: '-20px' }}>
              No upcoming follow-ups scheduled
            </li>
          )}
        </ul>
      </section>

      {/* Saved Database Records */}
      <section className="card">
        <h2>Saved in database ({dbRecords.length})</h2>
        <div id="dbList">
          {dbRecords.length > 0 ? (
            dbRecords.map((r, i) => (
              <div key={i} className="db-item">
                <div>
                  <strong>{r.beneficiary_name || (r.beneficiary_id ? `ID: ${r.beneficiary_id}` : 'N/A')}</strong> {r.beneficiary_name && r.beneficiary_id ? `(ID: ${r.beneficiary_id})` : ''} ({r.visit_type || 'Visit'}) &bull; {r.weight ? `${r.weight}kg` : ''}
                </div>
                <div style={{ color: 'var(--green)', fontSize: '11px', fontWeight: 'bold' }}>Saved</div>
              </div>
            ))
          ) : (
            <span style={{ color: 'var(--mute)', fontSize: '13px' }}>No records saved yet.</span>
          )}
        </div>
      </section>

      <footer>
        <span id="lat">Reply time: {replyTime}</span>
        <span style={{ fontSize: '12px', color: 'var(--mute)' }}>MoHFW ASHA Register &bull; Production</span>
      </footer>
    </main>
  );
}
