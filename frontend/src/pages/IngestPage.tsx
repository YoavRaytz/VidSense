import { useEffect, useRef, useState } from 'react';
import { ingestUrl, getStreamUrl, generateTranscript, getTranscript, putTranscript, getVideoMeta } from '../api';

export default function IngestPage(){
  const [link, setLink] = useState('');
  const [videoId, setVideoId] = useState<string | null>(null);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string>('');
  const [loading, setLoading] = useState<string | null>(null);

  // caption + multi-clip support
  const [description, setDescription] = useState<string>('');
  const [clipCount, setClipCount] = useState<number>(1);
  const [clip, setClip] = useState<number>(1);

  // batch/process-all state
  const [isBatch, setIsBatch] = useState(false);
  const [batchIdx, setBatchIdx] = useState(0); // 1-based
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // pretty view state
  const [pretty, setPretty] = useState(true);

  const videoRef = useRef<HTMLVideoElement | null>(null);

  function tryParseJSON(s?: string) {
    if (!s) return null;
    try { const o = JSON.parse(s); return o && typeof o === 'object' ? o : null; } catch { return null; }
  }
  const parsed = tryParseJSON(transcript);

  async function refreshStream(vId: string, c: number){
    const s = await getStreamUrl(vId, c);
    setStreamUrl(s.url);
    // restart playback from beginning when changing clip
    setTimeout(() => { videoRef.current?.load(); }, 0);
  }

  async function reloadTranscript(vId: string) {
    try {
      const t = await getTranscript(vId);
      setTranscript(t.text || '');
    } catch { /* ignore */ }
  }

  async function handleIngest(){
    setLoading('ingesting');
    setStatusMsg(null);
    try{
      const { video_id } = await ingestUrl(link);
      setVideoId(video_id);
      // fetch meta (caption + clip_count)
      const meta = await getVideoMeta(video_id).catch(()=>({ clip_count: 1, description: '' }));
      setClipCount(meta.clip_count || 1);
      setDescription(meta.description || '');
      setClip(1);
      await refreshStream(video_id, 1);
      await reloadTranscript(video_id);
    } finally { setLoading(null); }
  }

  async function handleGenerate(){
    if(!videoId) return;
    setLoading('transcribing');
    setStatusMsg(null);
    try{
      await generateTranscript(videoId, clip);
      await reloadTranscript(videoId);
      setStatusMsg(`✅ Transcribed clip ${clip}`);
    } catch (e: any) {
      setStatusMsg(`❌ Error: ${e?.message || e}`);
    } finally { setLoading(null); }
  }

  async function handleProcessAll() {
    if (!videoId) return;
    setIsBatch(true);
    setStatusMsg(null);
    try {
      for (let i = 1; i <= (clipCount || 1); i++) {
        setBatchIdx(i);
        setClip(i);                              // show current clip
        setStatusMsg(`Processing ${i}/${clipCount}…`);
        await refreshStream(videoId, i);         // switch player immediately
        await generateTranscript(videoId, i);    // append transcript for this clip
        await reloadTranscript(videoId);         // reflect appended text
      }
      setStatusMsg(`✅ Done. Processed ${clipCount} clip(s).`);
    } catch (e: any) {
      setStatusMsg(`❌ Error on clip ${batchIdx}: ${e?.message || e}`);
    } finally {
      setIsBatch(false);
    }
  }

  async function handleSave(){
    if(!videoId) return;
    setLoading('saving');
    setStatusMsg(null);
    try{ 
      await putTranscript(videoId, transcript);
      setStatusMsg('✅ Saved transcript.');
    } catch (e: any) {
      setStatusMsg(`❌ Save failed: ${e?.message || e}`);
    } finally { setLoading(null); }
  }

  // Load existing transcript if any
  useEffect(()=>{
    if(!videoId) return;
    getTranscript(videoId).then(t=> setTranscript(t.text)).catch(()=>{});
  }, [videoId]);

  // When clip changes manually, reload stream
  useEffect(()=>{
    if(!videoId) return;
    refreshStream(videoId, clip).catch(()=>{});
  }, [clip]);

  const disableActions = !!loading || isBatch;

  return (
    <div className="grid-2">
      {/* Left: video & actions */}
      <div className="card">
        <h3 className="section-title">Open a Video</h3>
        <div className="row" style={{marginBottom: 10}}>
          <input
            className="input"
            placeholder="Paste Instagram/URL…"
            value={link}
            onChange={e=>setLink(e.target.value)}
            disabled={disableActions}
          />
          <button className="btn btn-primary" onClick={handleIngest} disabled={!link || disableActions}>
            {loading==='ingesting'? '…' : 'Open'}
          </button>
        </div>

        {clipCount > 1 && (
          <div className="alert" style={{marginBottom: 10}}>
            📚 This post has <b>{clipCount}</b> videos.
          </div>
        )}

        {streamUrl ? (
          <>
            {clipCount > 1 && (
              <div className="row" style={{ marginBottom: 10, alignItems: 'center', gap: 8 }}>
                <button className="btn" onClick={()=> setClip(c => Math.max(1, c-1))} disabled={clip<=1 || disableActions}>« Prev</button>
                <div className="muted">Clip {clip} / {clipCount}</div>
                <button className="btn" onClick={()=> setClip(c => Math.min(clipCount, c+1))} disabled={clip>=clipCount || disableActions}>Next »</button>
              </div>
            )}
            <video ref={videoRef} src={streamUrl} controls className="video" />
            <div className="spacer" />
            <div className="row" style={{ gap: 8 }}>
              <button className="btn" onClick={handleGenerate} disabled={disableActions}>
                {loading==='transcribing'? 'Transcribing…' : `Get Transcript (clip ${clip})`}
              </button>
              {clipCount > 1 && (
                <button className="btn btn-primary" onClick={handleProcessAll} disabled={isBatch}>
                  {isBatch ? `Processing ${batchIdx}/${clipCount}…` : `Process All (${clipCount})`}
                </button>
              )}
            </div>
            {statusMsg && (
              <div className="alert" style={{ marginTop: 8 }}>
                {statusMsg}
              </div>
            )}
          </>
        ) : (
          <p className="muted" style={{margin: 0}}>Paste a URL and click <b>Open</b> to preview.</p>
        )}

        {description && (
          <div className="card" style={{ marginTop: 12 }}>
            <div className="section-title" style={{ marginBottom: 6 }}>Caption</div>
            <pre style={captionStyle}>{description}</pre>
          </div>
        )}
      </div>

      {/* Right: transcript viewer/editor (with pretty/JSON view) */}
      <div className="card">
        <div className="row" style={{ alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <h3 className="section-title" style={{ margin: 0 }}>Transcript</h3>
          <label className="text-xs text-gray-600" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={pretty} onChange={e => setPretty(e.target.checked)} />
            Pretty view
          </label>
        </div>

        {pretty && parsed ? (
          <div style={prettyWrap}>
            <Section title="Main Topic & Category" body={parsed.topic_category} />
            <Divider />
            <Section title="Onscreen Text" body={parsed.ocr} />
            <Divider />
            <Section title="Full Transcript"><pre style={preStyle}>{parsed.transcript || '—'}</pre></Section>
            <Divider />
            <Section title="Summary" body={parsed.summary} />
            <div style={{ padding: 12, color: '#9ca3af', fontSize: 12 }}>
              {new Intl.NumberFormat().format((parsed.transcript || '').length)} characters
            </div>
          </div>
        ) : (
          <textarea
            className="textarea"
            placeholder="Transcript will appear here…"
            value={transcript}
            onChange={e=>setTranscript(e.target.value)}
            style={taStyle}
            disabled={isBatch}
          />
        )}

        <div className="spacer" />
        <div className="row">
          <button className="btn btn-primary" onClick={handleSave} disabled={!videoId || disableActions}>
            {loading==='saving'? 'Saving…' : 'Save to DB'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---- small helpers / styles ---- */
const prettyWrap: React.CSSProperties = { border: '1px solid #1f2937', background: '#0b1220', borderRadius: 8, overflow: 'hidden' };
const preStyle: React.CSSProperties = { margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace', fontSize: 14, lineHeight: 1.55, color: '#e5e7eb' };
const bodyStyle: React.CSSProperties = { whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#e5e7eb', fontSize: 14, lineHeight: 1.55, margin: 0 };
const headerStyle: React.CSSProperties = { color: '#93c5fd', fontWeight: 700, fontSize: 13, letterSpacing: 0.2, padding: '10px 12px 0', textTransform: 'uppercase' };
const sectionWrap: React.CSSProperties = { padding: '6px 12px 10px' };
function Section({ title, body, children }: { title: string; body?: string | null; children?: React.ReactNode; }) {
  return (<div><div style={headerStyle}>{title}</div><div style={sectionWrap}>{children ? children : <p style={bodyStyle}>{(body || '').toString().trim() || '—'}</p>}</div></div>);
}
function Divider(){ return <div style={{ height: 1, background: '#1f2937' }} />; }
const taStyle: React.CSSProperties = { minHeight: 360, padding: 12, fontFamily:'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace', fontSize: 14, lineHeight: 1.55, background: '#0b1220', color: '#e5e7eb', borderColor: '#1f2937', resize: 'vertical' };
const captionStyle: React.CSSProperties = { margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 13, lineHeight: 1.5 };
