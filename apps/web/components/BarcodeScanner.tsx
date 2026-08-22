"use client";

import { useEffect, useRef, useState } from "react";
import { BrowserMultiFormatReader } from "@zxing/browser";
import { apiGet, apiPost } from "../lib/api";

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

  useEffect(() => {
    readerRef.current = new BrowserMultiFormatReader();
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
  }

  async function startCamera() {
    setStatus("");
    setHits([]);
    setBarcode(null);
    if (!readerRef.current || !videoRef.current) return;
    setScanning(true);
    try {
      controlsRef.current = await readerRef.current.decodeFromVideoDevice(
        undefined, // default camera (rear on phones)
        videoRef.current,
        (result, _err, controls) => {
          if (result) {
            controls.stop();
            controlsRef.current = null;
            setScanning(false);
            const text = result.getText();
            setBarcode(text);
            lookup(text);
          }
        }
      );
    } catch (e) {
      setScanning(false);
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
        <video ref={videoRef} className={scanning ? "scan-video on" : "scan-video"} muted playsInline />
        {scanning && <div className="scan-reticle" />}
      </div>

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
    </div>
  );
}
