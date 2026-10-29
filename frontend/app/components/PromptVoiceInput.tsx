"use client";
import { useEffect, useRef, useState } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

function pcmWav(samples: Float32Array) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const text = (offset: number, value: string) => [...value].forEach((char, index) => view.setUint8(offset + index, char.charCodeAt(0)));
  text(0, "RIFF"); view.setUint32(4, 36 + samples.length * 2, true); text(8, "WAVE");
  text(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, 24000, true); view.setUint32(28, 48000, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true); text(36, "data");
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((sample, index) => { const value = Math.max(-1, Math.min(1, sample)); view.setInt16(44 + index * 2, value < 0 ? value * 32768 : value * 32767, true); });
  return new File([buffer], "prompt-dictation.wav", { type: "audio/wav" });
}

export default function PromptVoiceInput({ token, workspace, available, disabled = false, onTranscript }: {
  token: string; workspace: string; available: boolean; disabled?: boolean; onTranscript: (value: string) => void;
}) {
  const [consent, setConsent] = useState(false);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (timer.current) clearTimeout(timer.current);
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach(track => track.stop());
    };
  }, []);

  async function transcribe(chunks: BlobPart[], mime: string) {
    if (!mounted.current) return;
    setBusy(true); setError("");
    try {
      const context = new AudioContext();
      let decoded: AudioBuffer;
      try { decoded = await context.decodeAudioData(await new Blob(chunks, { type: mime }).arrayBuffer()); }
      finally { await context.close(); }
      if (decoded.duration > 60 || decoded.duration < 0.5) throw new Error("Record between half a second and 60 seconds.");
      const length = Math.ceil(decoded.duration * 24000);
      const target = new OfflineAudioContext(1, length, 24000);
      const source = target.createBufferSource(); source.buffer = decoded; source.connect(target.destination); source.start();
      const rendered = await target.startRendering();
      const audio = pcmWav(rendered.getChannelData(0));
      const form = new FormData(); form.append("workspace_id", workspace); form.append("consent", "true"); form.append("file", audio);
      const response = await fetch(BASE + "/api/v1/prompts/transcribe", { method: "POST", headers: { Authorization: "Bearer " + token }, body: form });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Voice transcription failed.");
      if (data.provenance !== "live_meta" || typeof data.transcript !== "string" || !data.transcript.trim()) throw new Error("No live transcript was returned; sample text was not inserted.");
      if (mounted.current) onTranscript(data.transcript.trim());
    } catch (reason) {
      if (mounted.current) setError(reason instanceof Error ? reason.message : "Could not transcribe this recording.");
    } finally { if (mounted.current) setBusy(false); }
  }

  async function begin() {
    if (!available || !consent || disabled || busy) return;
    setError("");
    try {
      const input = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.current = input;
      const chunks: BlobPart[] = [];
      const device = new MediaRecorder(input); recorder.current = device;
      device.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      device.onstop = () => {
        input.getTracks().forEach(track => track.stop()); stream.current = null;
        if (timer.current) clearTimeout(timer.current);
        if (mounted.current) setRecording(false);
        void transcribe(chunks, device.mimeType || "audio/webm");
      };
      device.start(); setRecording(true);
      timer.current = setTimeout(() => { if (device.state === "recording") device.stop(); }, 60000);
    } catch {
      stream.current?.getTracks().forEach(track => track.stop()); stream.current = null;
      setError("Microphone access is unavailable. Check browser permission and try again.");
    }
  }

  function stop() { if (recorder.current?.state === "recording") recorder.current.stop(); }

  return <div className="prompt-voice">
    <label className="prompt-voice-consent"><input type="checkbox" checked={consent} disabled={!available || disabled || busy || recording} onChange={event => setConsent(event.target.checked)} />
      <span>Send this recording to Meta for transcription</span></label>
    <div className="prompt-voice-row"><button type="button" className={recording ? "secondary prompt-voice-stop" : "secondary prompt-voice-button"}
      disabled={disabled || busy || (!available) || (!recording && !consent)} onClick={recording ? stop : begin}>
      {busy ? <><span className="research-spinner"/>Transcribing…</> : recording ? "Stop & transcribe" : <><svg aria-hidden="true" viewBox="0 0 20 20" width="16" height="16"><rect x="7" y="2" width="6" height="11" rx="3"/><path d="M4.5 9.5a5.5 5.5 0 0 0 11 0M10 15v3m-3 0h6"/></svg>Record voice prompt</>}
    </button><span className="field-help">Up to 60 seconds. Audio is not saved; review the transcript before submitting your prompt.</span></div>
    {!available && <p className="field-help">Voice dictation needs live Meta inference enabled. No sample transcript will be substituted.</p>}
    {error && <p className="inline-warning" role="alert">{error}</p>}
  </div>;
}
