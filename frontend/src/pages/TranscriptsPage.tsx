import { useEffect, useMemo, useState } from "react";
import { listTranscripts, getTranscript, updateTranscript } from "../api";
import VideoPlayer from "../components/VideoPlayer";

type TranscriptDoc = {
  video_id: string;
  title?: string | null;
  url: string;
  media_path?: string | null;
  text: string; // may be plain text or JSON string (full result)
};

type ParsedPayload = {
  topic_category?: string | null;
  ocr?: string | null;
  transcript?: string | null;
  summary?: string | null;
  [k: string]: any;
};

function tryParseJSON(s?: string): ParsedPayload | null {
  if (!s) return null;
  try {
    const obj = JSON.parse(s);
    if (obj && typeof obj === "object") return obj as ParsedPayload;
  } catch {}
  return null;
}

export default function TranscriptsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [doc, setDoc] = useState<TranscriptDoc | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDoc, setLoadingDoc] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveOk, setSaveOk] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  // Editable fields
  const [editTranscript, setEditTranscript] = useState<string>(""); // structured-mode transcript
  const [editWhole, setEditWhole] = useState<string>("");            // plain-text (or full JSON string)

  // Load list
  useEffect(() => {
    (async () => {
      try {
        setLoadingList(true);
        setError(null);
        const list = await listTranscripts();
        setItems(Array.isArray(list) ? list : []);
      } catch (e: any) {
        setError("Failed to load transcripts list: " + (e?.message || "Unknown error"));
      } finally {
        setLoadingList(false);
      }
    })();
  }, []);

  // Load selected doc
  useEffect(() => {
    if (!selected) {
      setDoc(null);
      return;
    }
    (async () => {
      try {
        setLoadingDoc(true);
        setError(null);
        setSaveOk(false);
        const d = await getTranscript(selected);
        setDoc(d);
        // Initialize editors based on content
        const parsed = tryParseJSON(d?.text);
        if (parsed && typeof parsed === "object") {
          setEditTranscript(parsed.transcript || "");
          setEditWhole(d.text || "");
        } else {
          setEditTranscript("");
          setEditWhole(d.text || "");
        }
      } catch (e: any) {
        setError("Failed to load transcript: " + (e?.message || "Unknown error"));
      } finally {
        setLoadingDoc(false);
      }
    })();
  }, [selected]);

  const parsed = useMemo(() => tryParseJSON(doc?.text), [doc]);

  const dirty =
    parsed
      ? (editTranscript || "") !== (parsed.transcript || "")
      : (editWhole || "") !== (doc?.text || "");

  async function onSave() {
    if (!doc) return;
    setSaving(true);
    setSaveOk(false);
    setError(null);
    try {
      let payloadText: string;

      if (parsed) {
        // keep structure but update only transcript field
        const updated: ParsedPayload = { ...parsed, transcript: editTranscript };
        payloadText = JSON.stringify(updated, null, 2);
      } else {
        // plain text (or fully pasted JSON as text)
        payloadText = editWhole;
      }

      const updatedDoc = await updateTranscript(doc.video_id, payloadText);
      // Refresh doc + list
      setDoc(updatedDoc);
      const list = await listTranscripts();
      setItems(Array.isArray(list) ? list : []);
      setSaveOk(true);
    } catch (e: any) {
      setError("Save failed: " + (e?.message || "Unknown error"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid" style={{ gridTemplateColumns: "300px 1fr", gap: 16 }}>
      {/* Sidebar */}
      <aside className="border rounded p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="font-semibold">Videos</div>
          <div className="text-xs px-2 py-1 rounded bg-gray-100">{items.length}</div>
        </div>

        {loadingList && <div className="text-sm text-gray-500">⏳ Loading…</div>}

        {!loadingList && items.length === 0 && (
          <div className="text-sm text-gray-600">
            📭 No videos yet. Use the Ingest page to add one.
          </div>
        )}

        <ul className="divide-y mt-2">
          {items.map((it: any) => (
            <li
              key={it.video_id}
              onClick={() => setSelected(it.video_id)}
              className={`py-2 cursor-pointer ${selected === it.video_id ? "bg-gray-100 rounded px-2" : "px-2 hover:bg-gray-50 rounded"}`}
              title={it.url}
            >
              <div className="text-sm font-medium truncate">
                {it.title || it.video_id}
              </div>
              <div className="text-xs text-gray-500 truncate">{it.url}</div>
            </li>
          ))}
        </ul>
      </aside>

      {/* Main */}
      <section className="border rounded p-4">
        {error && (
          <div className="mb-3 p-3 border border-red-200 bg-red-50 rounded text-sm">
            <strong>Error:</strong> {error}
          </div>
        )}

        {loadingDoc && <div className="text-gray-500">⏳ Loading transcript…</div>}

        {!loadingDoc && doc && (
          <>
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-lg font-semibold">
                  {doc.title || doc.video_id}
                </h2>
                <a
                  className="text-sm text-blue-600"
                  href={doc.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  🔗 Open source
                </a>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={onSave}
                  disabled={saving || !dirty}
                  className={`px-3 py-2 rounded text-white ${saving || !dirty ? "bg-gray-400" : "bg-green-600 hover:bg-green-700"}`}
                >
                  {saving ? "Saving…" : "Save"}
                </button>
                {saveOk && <span className="text-green-600 text-sm">✅ Saved</span>}
                {dirty && !saving && <span className="text-amber-600 text-xs">Unsaved changes</span>}
              </div>
            </div>

            {/* Video */}
            <div className="mb-4">
              <VideoPlayer media_path={doc.media_path} />
            </div>

            {/* Structured vs Plain */}
            {parsed ? (
              <div className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <InfoCard title="Main Topic & Category">
                    <pre className="whitespace-pre-wrap break-words text-sm">
                      {parsed.topic_category || "—"}
                    </pre>
                  </InfoCard>
                  <InfoCard title="Onscreen Text">
                    <pre className="whitespace-pre-wrap break-words text-sm">
                      {parsed.ocr || "—"}
                    </pre>
                  </InfoCard>
                </div>

                <InfoCard title="Full Transcript (editable)">
                  <textarea
                    className="w-full border rounded p-3 h-72 font-mono text-sm"
                    value={editTranscript}
                    onChange={(e) => setEditTranscript(e.target.value)}
                    placeholder="Transcript…"
                  />
                </InfoCard>

                <div className="flex items-center gap-2">
                  <label className="text-sm">
                    <input
                      type="checkbox"
                      className="mr-2"
                      checked={showRaw}
                      onChange={(e) => setShowRaw(e.target.checked)}
                    />
                    Show raw JSON
                  </label>
                </div>

                {showRaw && (
                  <InfoCard title="Raw JSON">
                    <pre className="p-3 bg-gray-50 border rounded overflow-auto text-xs">
{JSON.stringify(parsed, null, 2)}
                    </pre>
                  </InfoCard>
                )}

                <InfoCard title="Summary">
                  <pre className="whitespace-pre-wrap break-words text-sm">
                    {parsed.summary || "—"}
                  </pre>
                </InfoCard>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-sm text-gray-600">
                  Plain text mode (no JSON structure detected)
                </div>
                <textarea
                  className="w-full border rounded p-3 h-96 font-mono text-sm"
                  value={editWhole}
                  onChange={(e) => setEditWhole(e.target.value)}
                  placeholder="Transcript text…"
                />
              </div>
            )}
          </>
        )}

        {!loadingDoc && !doc && !error && (
          <div className="text-gray-500">👈 Select a video from the list</div>
        )}
      </section>
    </div>
  );
}

function InfoCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border rounded p-3">
      <div className="text-sm font-semibold mb-2">{title}</div>
      {children}
    </div>
  );
}
