import { useEffect, useRef, useState } from 'react';
import { ingestUrl, getStreamUrl, generateTranscript, getTranscript, putTranscript } from '../api';

export default function IngestPage(){
  const [link, setLink] = useState('');
  const [videoId, setVideoId] = useState<string | null>(null);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string>('');
  const [loading, setLoading] = useState<string | null>(null);
  const [pretty, setPretty] = useState(true);            // << add pretty toggle
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // --- helpers for “pretty” view ---
  function tryParseJSON(s?: string) {
    if (!s) return null;
    try {
      const obj = JSON.parse(s);
      return obj && typeof obj === 'object' ? obj : null;
    } catch { return null; }
  }
  const parsed = tryParseJSON(transcript);

  async function handleIngest(){
    setLoading('ingesting');
    try{
      const { video_id } = await ingestUrl(link);
      setVideoId(video_id);
      const s = await getStreamUrl(video_id);
      setStreamUrl(s.url);
    } finally { setLoading(null); }
  }

  async function handleGenerate(){
    if(!videoId) return;
    setLoading('transcribing');
    try{
      const t = await generateTranscript(videoId);
      setTranscript(t.text || '');
    } finally { setLoading(null); }
  }

  async function handleSave(){
    if(!videoId) return;
    setLoading('saving');
    try{ await putTranscript(videoId, transcript); }
    finally{ setLoading(null); }
  }

  useEffect(()=>{
    if(!videoId) return;
    getTranscript(videoId).then(t=> setTranscript(t.text)).catch(()=>{});
  }, [videoId]);

  return (
    <div className="grid-2">
      {/* Left column: video & actions */}
      <div className="card">
        <h3 className="section-title">Open a Video</h3>
        <div className="row" style={{marginBottom: 10}}>
          <input
            className="input"
            placeholder="Paste Instagram/URL…"
            value={link}
            onChange={e=>setLink(e.target.value)}
          />
          <button className="btn btn-primary" onClick={handleIngest} disabled={!link || !!loading}>
            {loading==='ingesting'? '…' : 'Open'}
          </button>
        </div>

        {streamUrl ? (
          <>
            <video ref={videoRef} src={streamUrl} controls className="video" />
            <div className="spacer" />
            <div className="row">
              <button className="btn" onClick={handleGenerate} disabled={!!loading}>
                {loading==='transcribing'? 'Transcribing…' : 'Get Transcript'}
              </button>
            </div>
          </>
        ) : (
          <p className="muted" style={{margin: 0}}>Paste a URL and click <b>Open</b> to preview.</p>
        )}
      </div>

      {/* Right column: transcript viewer/editor */}
      <div className="card">
        <div className="row" style={{ alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <h3 className="section-title" style={{ margin: 0 }}>Transcript</h3>
          <label className="text-xs text-gray-600" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={pretty} onChange={e => setPretty(e.target.checked)} />
            Pretty view
          </label>
        </div>

        {/* Pretty formatted view when transcript is JSON and toggle is ON */}
        {pretty && parsed ? (
          <div style={prettyWrap}>
            <Section title="Main Topic & Category" body={parsed.topic_category} />
            <Divider />
            <Section title="Onscreen Text" body={parsed.ocr} />
            <Divider />
            <Section title="Full Transcript">
              <pre style={preStyle}>{parsed.transcript || '—'}</pre>
            </Section>
            <Divider />
            <Section title="Summary" body={parsed.summary} />
            <div style={{ padding: 12, color: '#9ca3af', fontSize: 12 }}>
              {new Intl.NumberFormat().format((parsed.transcript || '').length)} characters
            </div>
          </div>
        ) : (
          // Plain editable text (also shown if it's not JSON)
          <textarea
            className="textarea"
            placeholder="Transcript will appear here…"
            value={transcript}
            onChange={e=>setTranscript(e.target.value)}
            style={taStyle}
          />
        )}

        <div className="spacer" />
        <div className="row">
          <button className="btn btn-primary" onClick={handleSave} disabled={!videoId || !!loading}>
            {loading==='saving'? 'Saving…' : 'Save to DB'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------- Pretty view helpers (inline styles + tiny components) ---------- */

const prettyWrap: React.CSSProperties = {
  border: '1px solid #1f2937',
  background: '#0b1220',
  borderRadius: 8,
  overflow: 'hidden'
};

const preStyle: React.CSSProperties = {
  margin: 0,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace',
  fontSize: 14,
  lineHeight: 1.55,
  color: '#e5e7eb',
};

const bodyStyle: React.CSSProperties = {
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  color: '#e5e7eb',
  fontSize: 14,
  lineHeight: 1.55,
  margin: 0,
};

const headerStyle: React.CSSProperties = {
  color: '#93c5fd',
  fontWeight: 700,
  fontSize: 13,
  letterSpacing: 0.2,
  padding: '10px 12px 0',
  textTransform: 'uppercase',
};

const sectionWrap: React.CSSProperties = { padding: '6px 12px 10px' };

function Section({
  title,
  body,
  children,
}: {
  title: string;
  body?: string | null;
  children?: React.ReactNode;
}) {
  return (
    <div>
      <div style={headerStyle}>{title}</div>
      <div style={sectionWrap}>
        {children ? (
          children
        ) : (
          <p style={bodyStyle}>{(body || '').toString().trim() || '—'}</p>
        )}
      </div>
    </div>
  );
}

function Divider() {
  return <div style={{ height: 1, background: '#1f2937' }} />;
}

// nicer textarea styling for plain mode
const taStyle: React.CSSProperties = {
  minHeight: 360,
  padding: 12,
  fontFamily:
    'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace',
  fontSize: 14,
  lineHeight: 1.55,
  background: '#0b1220',
  color: '#e5e7eb',
  borderColor: '#1f2937',
  resize: 'vertical',
};
