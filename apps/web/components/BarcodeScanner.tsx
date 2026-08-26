"use client";

import { useEffect, useRef, useState } from "react";
import { BrowserMultiFormatReader } from "@zxing/browser";
import { BarcodeFormat, DecodeHintType } from "@zxing/library";
import { apiGet, apiPost, apiUpload } from "../lib/api";

type DiscogsHit = {
  discogs_id: number;
  title: string;
  year: number | null;
  country: string | null;
  label: string | null;
  catno: string | null;
  thumb: string | null;
};

type BatchItem = {
  id: string;
  fileName: string;
  previewUrl: string;
  status: "waiting" | "checking barcode" | "looking up" | "identifying cover" | "done" | "error";
  barcode: string | null;
  identified: { artist: string | null; title: string | null; confidence: string; notes: string } | null;
  hits: DiscogsHit[];
  message: string;
  added: boolean;
};

/**
 * Scan a record's barcode to find it on Discogs — either with the live camera
 * or by uploading a photo. The decoded barcode is looked up server-side
 * (/collection/scan), and matches are shown to pick and add.
 *
 * Note: the live camera requires HTTPS (or localhost) and camera permission.
 * If the camera isn't available, the photo-upload path still works.
 */
export default function BarcodeScanner({
  onAdded,
  onRefresh,
  onError,
}: {
  onAdded: () => void;
  onRefresh: () => void;
  onError: (s: string) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const readerRef = useRef<BrowserMultiFormatReader | null>(null);
  const controlsRef = useRef<{ stop: () => void } | null>(null);
  const [scanning, setScanning] = useState(false);
  const [barcode, setBarcode] = useState<string | null>(null);
  const [hits, setHits] = useState<DiscogsHit[]>([]);
  const [status, setStatus] = useState("");
  const [target, setTarget] = useState("collection");
  const [hint, setHint] = useState("");
  const hintTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [photoBusy, setPhotoBusy] = useState(false);
  const [photoIdentified, setPhotoIdentified] = useState<{
    artist: string | null;
    title: string | null;
    confidence: string;
    notes: string;
  } | null>(null);
  const [photoHits, setPhotoHits] = useState<DiscogsHit[]>([]);
  const [uploadBusy, setUploadBusy] = useState(false);

  const [batch, setBatch] = useState<BatchItem[]>([]);
  const [batchBusy, setBatchBusy] = useState(false);

  useEffect(() => {
    // Constrain to the barcode formats actually printed on record sleeves
    // (UPC/EAN), and turn on TRY_HARDER — without it, ZXing's default pass
    // is tuned for speed over accuracy and can miss real barcodes that are
    // slightly angled, distant, or under uneven lighting, which was
    // previously making the camera preview show but never actually detect.
    const hints = new Map();
    hints.set(DecodeHintType.POSSIBLE_FORMATS, [
      BarcodeFormat.UPC_A,
      BarcodeFormat.UPC_E,
      BarcodeFormat.EAN_13,
      BarcodeFormat.EAN_8,
      BarcodeFormat.CODE_128,
    ]);
    hints.set(DecodeHintType.TRY_HARDER, true);
    readerRef.current = new BrowserMultiFormatReader(hints);
    return () => stopCamera();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function stopCamera() {
    try {
      controlsRef.current?.stop();
    } catch {
      /* ignore */
    }
    controlsRef.current = null;
    setScanning(false);
    setHint("");
    if (hintTimerRef.current) {
      clearTimeout(hintTimerRef.current);
      hintTimerRef.current = null;
    }
  }

  async function startCamera() {
    setStatus("");
    setHits([]);
    setBarcode(null);
    setHint("");
    if (!readerRef.current || !videoRef.current) return;
    setScanning(true);
    // If nothing's detected after a few seconds, this is almost always a
    // positioning/lighting issue rather than a broken scanner — say so,
    // since a silent camera preview with no feedback looks like it's frozen.
    hintTimerRef.current = setTimeout(() => {
      setHint("Still looking — move closer, fill the frame with the barcode, and avoid glare.");
    }, 4000);
    try {
      controlsRef.current = await readerRef.current.decodeFromConstraints(
        // Explicitly request the rear camera. Letting ZXing pick a default
        // device is ambiguous across browsers/versions and can silently
        // select the front-facing camera on some phones — which looks
        // exactly like "the camera works but never scans anything," since
        // the user is pointing the back of the phone at the barcode while
        // the front camera captures their face instead.
        { video: { facingMode: { ideal: "environment" } } },
        videoRef.current,
        (result, _err, controls) => {
          if (result) {
            controls.stop();
            controlsRef.current = null;
            setScanning(false);
            setHint("");
            if (hintTimerRef.current) {
              clearTimeout(hintTimerRef.current);
              hintTimerRef.current = null;
            }
            const text = result.getText();
            setBarcode(text);
            lookup(text);
          }
        }
      );
    } catch (e) {
      setScanning(false);
      setHint("");
      onError("Couldn't start the camera. Grant camera permission, or upload a photo instead.");
    }
  }

  async function onFile(file: File) {
    setStatus("");
    setHits([]);
    setBarcode(null);
    if (!readerRef.current) return;
    setUploadBusy(true);
    try {
      const url = URL.createObjectURL(file);
      let decoded: string | null = null;
      try {
        const result = await readerRef.current.decodeFromImageUrl(url);
        decoded = result.getText();
      } catch {
        // No barcode readable in the photo — not an error, just means this is
        // probably a cover/label shot, so we try AI identification below.
      } finally {
        URL.revokeObjectURL(url);
      }

      if (decoded) {
        setBarcode(decoded);
        setStatus("Looking up barcode…");
        try {
          const r = await apiGet<{ results: DiscogsHit[] }>(`/collection/scan?barcode=${encodeURIComponent(decoded)}`);
          if (r.results.length) {
            setHits(r.results);
            setStatus("");
            return;
          }
          setStatus("Found a barcode, but no Discogs match for it. Trying to identify the cover instead…");
        } catch (e) {
          // A real error (e.g. Discogs not connected) — show it and stop,
          // rather than also failing the AI fallback for the same reason.
          setStatus("");
          onError((e as Error).message);
          return;
        }
      } else {
        setStatus("No barcode found in that photo — trying to identify the cover instead…");
      }

      // One photo, two detection methods: barcode first (fast, exact), then
      // AI cover/label recognition as the automatic fallback — no separate
      // button needed, since "Scan" should just work either way.
      await identifyPhoto(file);
      setStatus("");
    } finally {
      setUploadBusy(false);
    }
  }

  async function lookup(code: string) {
    setStatus("Looking up…");
    try {
      const r = await apiGet<{ results: DiscogsHit[] }>(`/collection/scan?barcode=${encodeURIComponent(code)}`);
      setHits(r.results);
      setStatus(r.results.length ? "" : "No Discogs match for that barcode. You can add it by hand instead.");
    } catch (e) {
      setStatus("");
      onError((e as Error).message);
    }
  }

  async function add(hit: DiscogsHit) {
    try {
      await apiPost("/collection/from-discogs", { discogs_release_id: hit.discogs_id, target });
      onAdded();
    } catch (e) {
      onError((e as Error).message);
    }
  }

  async function identifyPhoto(file: File) {
    setPhotoBusy(true);
    setPhotoIdentified(null);
    setPhotoHits([]);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await apiUpload<{
        identified: { artist: string | null; title: string | null; confidence: string; notes: string };
        results: DiscogsHit[];
      }>("/collection/identify-photo", formData);
      setPhotoIdentified(res.identified);
      setPhotoHits(res.results);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setPhotoBusy(false);
    }
  }

  function updateBatchItem(id: string, patch: Partial<BatchItem>) {
    setBatch((prev) => prev.map((it) => (it.id === id ? { ...it, ...patch } : it)));
  }

  async function processBatchFiles(files: FileList) {
    const MAX_BATCH = 5;
    const fileArray = Array.from(files).slice(0, MAX_BATCH);
    const skipped = files.length - fileArray.length;

    const items: BatchItem[] = fileArray.map((f, i) => ({
      id: `${Date.now()}-${i}`,
      fileName: f.name,
      previewUrl: URL.createObjectURL(f),
      status: "waiting",
      barcode: null,
      identified: null,
      hits: [],
      message: "",
      added: false,
    }));
    setBatch(items);
    setBatchBusy(true);
    if (skipped > 0) {
      onError(`Only the first ${MAX_BATCH} photos are processed at once — ${skipped} were skipped.`);
    }

    // Processed one at a time, not in parallel: each photo may trigger a real
    // AI call on the backend, and running five of those simultaneously would
    // both be harder to show clear progress for and needlessly hammer the
    // identification service all at once.
    for (let i = 0; i < fileArray.length; i++) {
      const file = fileArray[i];
      const id = items[i].id;
      updateBatchItem(id, { status: "checking barcode" });

      let decoded: string | null = null;
      if (readerRef.current) {
        const url = URL.createObjectURL(file);
        try {
          const result = await readerRef.current.decodeFromImageUrl(url);
          decoded = result.getText();
        } catch {
          // no barcode in this photo — fine, we'll try AI identification below
        } finally {
          URL.revokeObjectURL(url);
        }
      }

      if (decoded) {
        updateBatchItem(id, { status: "looking up", barcode: decoded });
        try {
          const r = await apiGet<{ results: DiscogsHit[] }>(`/collection/scan?barcode=${encodeURIComponent(decoded)}`);
          if (r.results.length) {
            updateBatchItem(id, { status: "done", hits: r.results });
            continue;
          }
          // barcode read fine, but no Discogs match -- fall through to AI below
        } catch (e) {
          updateBatchItem(id, { status: "error", message: (e as Error).message });
          continue;
        }
      }

      updateBatchItem(id, { status: "identifying cover" });
      try {
        const formData = new FormData();
        formData.append("file", file);
        const res = await apiUpload<{
          identified: { artist: string | null; title: string | null; confidence: string; notes: string };
          results: DiscogsHit[];
        }>("/collection/identify-photo", formData);
        updateBatchItem(id, { status: "done", identified: res.identified, hits: res.results });
      } catch (e) {
        updateBatchItem(id, { status: "error", message: (e as Error).message });
      }
    }
    setBatchBusy(false);
  }

  async function addFromBatchItem(itemId: string, hit: DiscogsHit) {
    try {
      await apiPost("/collection/from-discogs", { discogs_release_id: hit.discogs_id, target });
      updateBatchItem(itemId, { added: true });
      onRefresh();
    } catch (e) {
      onError((e as Error).message);
    }
  }

  return (
    <div className="add-form">
      <div className="target-toggle">
        <button className={target === "collection" ? "tgl active" : "tgl"} onClick={() => setTarget("collection")} type="button">
          In my collection
        </button>
        <button className={target === "wantlist" ? "tgl active" : "tgl"} onClick={() => setTarget("wantlist")} type="button">
          On my wantlist
        </button>
      </div>
      <div className="muted small">
        Point your camera at a barcode, or upload a photo — of the barcode, or the cover if there
        isn't one. Requires a connected Discogs account.
      </div>

      <div className="scan-stage">
        <video ref={videoRef} className={scanning ? "scan-video on" : "scan-video"} muted autoPlay playsInline />
        {scanning && <div className="scan-reticle" />}
      </div>
      {hint && <div className="muted small">{hint}</div>}

      <div className="add-row">
        {!scanning ? (
          <button className="btn greenbtn" onClick={startCamera}>USE CAMERA</button>
        ) : (
          <button className="btn light" onClick={stopCamera}>STOP</button>
        )}
        <label className="btn light" style={{ cursor: uploadBusy ? "default" : "pointer" }}>
          {uploadBusy ? "SCANNING…" : "UPLOAD PHOTO"}
          <input
            type="file"
            accept="image/*"
            capture="environment"
            style={{ display: "none" }}
            disabled={uploadBusy}
            onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
          />
        </label>
      </div>

      {barcode && <div className="muted small">Barcode: {barcode}</div>}
      {status && <div className="muted small">{status}</div>}

      <div className="scan-divider">
        <span>adding several at once?</span>
      </div>

      <div className="muted small">
        Upload up to 5 photos together — covers work best; a label photo works too if there's no
        sleeve. Each one gets scanned for a barcode first, then AI cover ID if that doesn't find a match.
      </div>
      <label className="btn light" style={{ cursor: batchBusy ? "default" : "pointer", marginTop: 8 }}>
        {batchBusy ? "PROCESSING…" : "UPLOAD 2–5 PHOTOS"}
        <input
          type="file"
          accept="image/*"
          multiple
          style={{ display: "none" }}
          disabled={batchBusy}
          onChange={(e) => e.target.files && e.target.files.length > 0 && processBatchFiles(e.target.files)}
        />
      </label>

      {batch.length > 0 && (
        <div className="batch-list">
          {batch.map((item) => (
            <div className="batch-item" key={item.id}>
              <img src={item.previewUrl} alt="" className="batch-thumb" />
              <div className="batch-body">
                <div className="muted small">{item.fileName}</div>

                {item.status !== "done" && item.status !== "error" && (
                  <div className="muted small">{item.status}…</div>
                )}
                {item.status === "error" && <div className="muted small">Couldn't process this one: {item.message}</div>}

                {item.status === "done" && item.identified && !item.identified.artist && !item.identified.title && (
                  <div className="muted small">
                    No barcode and couldn't identify the cover{item.identified.notes ? ` — ${item.identified.notes}` : "."}
                  </div>
                )}
                {item.status === "done" && item.identified?.artist && (
                  <div className="muted small">
                    AI thinks: <strong>{[item.identified.artist, item.identified.title].filter(Boolean).join(" — ")}</strong>
                    {" "}({item.identified.confidence})
                  </div>
                )}

                {item.added && <div className="muted small">✓ Added</div>}

                {!item.added && item.hits.length > 0 && (
                  <div className="hit-list">
                    {item.hits.slice(0, 3).map((hit) => (
                      <div className="hit" key={hit.discogs_id}>
                        {hit.thumb && <img src={hit.thumb} alt="" />}
                        <div className="hit-body">
                          <div>{hit.title}</div>
                          <div className="muted small">{[hit.year, hit.country, hit.label].filter(Boolean).join(" · ")}</div>
                        </div>
                        <button className="btn-small" onClick={() => addFromBatchItem(item.id, hit)}>ADD</button>
                      </div>
                    ))}
                  </div>
                )}
                {item.status === "done" && !item.added && item.hits.length === 0 && item.barcode && (
                  <div className="muted small">Found a barcode, but no Discogs match for it.</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="hit-list">
        {hits.map((hit) => (
          <div className="hit" key={hit.discogs_id}>
            {hit.thumb && <img src={hit.thumb} alt="" />}
            <div className="hit-body">
              <div>{hit.title}</div>
              <div className="muted small">{[hit.year, hit.country, hit.label, hit.catno].filter(Boolean).join(" · ")}</div>
            </div>
            <button className="btn-small" onClick={() => add(hit)}>ADD</button>
          </div>
        ))}
      </div>

      {(photoBusy || photoIdentified || photoHits.length > 0) && (
        <div className="photo-id-section">
          <div className="muted small">
            <strong>AI Photo ID</strong> — since no barcode matched, we tried identifying the cover
            instead. This is less reliable than a barcode: lighting, angle, and reissues sharing the
            same artwork can all throw it off, so double-check the match before adding.
          </div>

          {photoBusy && <div className="muted small" style={{ marginTop: 8 }}>Identifying…</div>}

          {photoIdentified && (
            <div className="photo-id-result">
              {photoIdentified.artist || photoIdentified.title ? (
                <>
                  <div className="muted small">
                    AI thinks this is: <strong>{[photoIdentified.artist, photoIdentified.title].filter(Boolean).join(" — ")}</strong>
                    {" "}({photoIdentified.confidence} confidence)
                  </div>
                  {photoIdentified.notes && <div className="muted small">{photoIdentified.notes}</div>}
                </>
              ) : (
                <div className="muted small">
                  Couldn't identify anything from that photo{photoIdentified.notes ? ` — ${photoIdentified.notes}` : "."} Try a clearer photo, or add it by hand.
                </div>
              )}
            </div>
          )}

          {photoHits.length > 0 && (
            <div className="hit-list">
              {photoHits.map((hit) => (
                <div className="hit" key={hit.discogs_id}>
                  {hit.thumb && <img src={hit.thumb} alt="" />}
                  <div className="hit-body">
                    <div>{hit.title}</div>
                    <div className="muted small">{[hit.year, hit.country, hit.label, hit.catno].filter(Boolean).join(" · ")}</div>
                  </div>
                  <button className="btn-small" onClick={() => add(hit)}>ADD</button>
                </div>
              ))}
          </div>
        )}
      </div>
      )}
    </div>
  );
}
