import { useState } from 'react';
import React from 'react';

interface TranscriptViewerProps {
  transcript: string;
  description?: string;
  onTranscriptChange?: (text: string) => void;
  onSave?: () => void;
  saving?: boolean;
  statusMsg?: string | null;
  readOnly?: boolean;
}

function tryParseJSON(s?: string) {
  if (!s) return null;
  try { 
    const o = JSON.parse(s); 
    return o && typeof o === 'object' ? o : null; 
  } catch { 
    return null; 
  }
}

export default function TranscriptViewer({ 
  transcript, 
  description, 
  onTranscriptChange,
  onSave,
  saving = false,
  statusMsg = null,
  readOnly = false
}: TranscriptViewerProps) {
  const [pretty, setPretty] = useState(true);
  const [textSize, setTextSize] = useState(16);
  const [displayHeight, setDisplayHeight] = useState(650);

  const parsed = tryParseJSON(transcript);

  return (
    <div className="card">
      {/* Transcript header with controls */}
      <div className="row" style={{ alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, flexWrap: 'wrap', gap: 8 }}>
        <h3 className="section-title" style={{ margin: 0 }}>Transcript</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <label className="text-xs text-gray-600" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={pretty} onChange={e => setPretty(e.target.checked)} />
            Pretty view
          </label>
          <label className="text-xs text-gray-600" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            Size: {textSize}px
            <input 
              type="range" 
              min="12" 
              max="24" 
              value={textSize} 
              onChange={e => setTextSize(Number(e.target.value))}
              style={{ width: 80 }}
            />
          </label>
          <label className="text-xs text-gray-600" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            Height: {displayHeight}px
            <input 
              type="range" 
              min="400" 
              max="1200" 
              step="50"
              value={displayHeight} 
              onChange={e => setDisplayHeight(Number(e.target.value))}
              style={{ width: 100 }}
            />
          </label>
        </div>
      </div>

      {/* Status message */}
      {statusMsg && (
        <div className="alert" style={{ marginBottom: 12 }}>
          {statusMsg}
        </div>
      )}

      {/* Transcript display */}
      {pretty && parsed ? (
        <div style={{...prettyWrap, fontSize: textSize, lineHeight: 1.8, minHeight: displayHeight}}>
          <Section title="Main Topic & Category" body={parsed.topic_category} textSize={textSize} />
          <Divider />
          <Section title="Onscreen Text" body={parsed.ocr} textSize={textSize} />
          <Divider />
          <Section title="Full Transcript" textSize={textSize}>
            <pre style={{...preStyle, fontSize: textSize}}>{parsed.transcript || '—'}</pre>
          </Section>
          <Divider />
          <Section title="Summary" body={parsed.summary} textSize={textSize} />
          <div style={{ padding: 12, color: '#9ca3af', fontSize: 12 }}>
            {new Intl.NumberFormat().format((parsed.transcript || '').length)} characters
          </div>
        </div>
      ) : (
        <textarea
          className="textarea"
          placeholder="Transcript will appear here…"
          value={transcript}
          onChange={e => onTranscriptChange?.(e.target.value)}
          style={{...taStyle, fontSize: textSize, minHeight: displayHeight}}
          disabled={readOnly}
        />
      )}

      {/* Save button (only if onSave provided) */}
      {onSave && !readOnly && (
        <>
          <div className="spacer" />
          <div className="row">
            <button className="btn btn-primary" onClick={onSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save to DB'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

/* ---- Styles and helpers ---- */
const prettyWrap: React.CSSProperties = { 
  border: '1px solid #1f2937', 
  background: '#0b1220', 
  borderRadius: 8, 
  overflow: 'hidden', 
  minHeight: 650 
};

const preStyle: React.CSSProperties = { 
  margin: 0, 
  whiteSpace: 'pre-wrap', 
  wordBreak: 'break-word', 
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace', 
  lineHeight: 1.8, 
  color: '#e5e7eb' 
};

const bodyStyle: React.CSSProperties = { 
  whiteSpace: 'pre-wrap', 
  wordBreak: 'break-word', 
  color: '#e5e7eb', 
  lineHeight: 1.8, 
  margin: 0 
};

const headerStyle: React.CSSProperties = { 
  color: '#93c5fd', 
  fontWeight: 700, 
  fontSize: 13, 
  letterSpacing: 0.2, 
  padding: '10px 12px 0', 
  textTransform: 'uppercase' 
};

const sectionWrap: React.CSSProperties = { 
  padding: '8px 16px 12px' 
};

const taStyle: React.CSSProperties = { 
  minHeight: 650, 
  padding: 20, 
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace', 
  lineHeight: 1.8, 
  background: '#0b1220', 
  color: '#e5e7eb', 
  borderColor: '#1f2937', 
  resize: 'vertical' 
};

function Section({ title, body, children, textSize = 16 }: { 
  title: string; 
  body?: string | null; 
  children?: React.ReactNode; 
  textSize?: number; 
}) {
  return (
    <div>
      <div style={headerStyle}>{title}</div>
      <div style={sectionWrap}>
        {children ? children : <p style={{...bodyStyle, fontSize: textSize}}>{(body || '').toString().trim() || '—'}</p>}
      </div>
    </div>
  );
}

function Divider() { 
  return <div style={{ height: 1, background: '#1f2937' }} />; 
}
