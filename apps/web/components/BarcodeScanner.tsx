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

/**
 * Scan a record's barcode to find it on Discogs — either with the live camera
 * or by uploading a photo. The decoded barcode is looked up server-side
 * (/collection/scan), and matches are shown to pick and add.
 *
 * Note: the live camera requires HTTPS (or localhost) and camera permission.
 * If the camera isn't available, the photo-upload path still works.
 */
export default function BarcodeScanner({ onAdded, onError }: { onAdded: () => void; onError: (s: string) => void }) {
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
    const url = URL.createObjectURL(file);
    try {
      const result = await readerRef.current.decodeFromImageUrl(url);
      const text = result.getText();
      setBarcode(text);
      lookup(text);
    } catch {
      onError("No barcode found in that image. Try a clearer, closer photo of the barcode.");
    } finally {
      URL.revokeObjectURL(url);
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
        Scan a record's barcode with your camera, or upload a photo of it. Requires a connected Discogs account.
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
        <label className="btn light" style={{ cursor: "pointer" }}>
          UPLOAD PHOTO
          <input
            type="file"
            accept="image/*"
            capture="environment"
            style={{ display: "none" }}
            onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
          />
        </label>
      </div>

      {barcode && <div className="muted small">Barcode: {barcode}</div>}
      {status && <div className="muted small">{status}</div>}

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

      <div className="scan-divider">
        <span>or, if there's no barcode</span>
      </div>

      <div className="photo-id-section">
        <div className="muted small">
          <strong>AI Photo ID</strong> — take a photo of the cover or label and we'll try to identify it.
          This is less reliable than a barcode: lighting, angle, and reissues sharing the same
          artwork can all throw it off, so double-check the match before adding.
        </div>
        <label className="btn light" style={{ cursor: "pointer", marginTop: 8 }}>
          {photoBusy ? "IDENTIFYING…" : "IDENTIFY BY PHOTO"}
          <input
            type="file"
            accept="image/*"
            capture="environment"
            style={{ display: "none" }}
            disabled={photoBusy}
            onChange={(e) => e.target.files?.[0] && identifyPhoto(e.target.files[0])}
          />
        </label>

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
                Couldn't identify anything from that photo{photoIdentified.notes ? ` — ${photoIdentified.notes}` : "."} Try a clearer photo, the barcode, or add it by hand.
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
    </div>
  );
}
