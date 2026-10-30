import type { BrowserMultiFormatReader } from "@zxing/browser";

// Photos straight off a phone camera are usually 12–50 megapixels and several
// MB, often HEIC on iPhones. Sent as-is they fail in three ways: the AI
// service rejects images over 5MB, the API rejects anything that isn't
// JPEG/PNG/WebP or is over 8MB, and decoding a barcode from a 50MP canvas
// either runs out of memory (iOS caps canvas size) or takes so long it looks
// frozen. Everything here works on a downscaled copy instead.

// The AI vision model gains nothing from images larger than this on the long
// edge, so it's the upload size for cover/label identification.
const UPLOAD_MAX_EDGE = 1568;
// Barcode reading is tried at a couple of sizes: small is fast and enough when
// the barcode fills the frame; larger helps when it's a small part of the shot.
const BARCODE_EDGES = [1280, 2400];

export function loadImage(file: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Couldn't read that photo. Try a JPEG or PNG."));
    };
    img.src = url;
  });
}

function toCanvas(img: HTMLImageElement, maxEdge: number): HTMLCanvasElement {
  const scale = Math.min(1, maxEdge / Math.max(img.naturalWidth, img.naturalHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(img.naturalWidth * scale);
  canvas.height = Math.round(img.naturalHeight * scale);
  canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
  return canvas;
}

type NativeBarcodeDetector = {
  detect(source: CanvasImageSource): Promise<{ rawValue: string }[]>;
};

function nativeDetector(): NativeBarcodeDetector | null {
  // Chrome on Android ships a built-in, hardware-accelerated barcode reader
  // that copes with blur and angles far better than ZXing. Safari doesn't
  // have it, so ZXing remains the fallback.
  const Ctor = (globalThis as { BarcodeDetector?: new (opts: { formats: string[] }) => NativeBarcodeDetector })
    .BarcodeDetector;
  if (!Ctor) return null;
  try {
    return new Ctor({ formats: ["ean_13", "ean_8", "upc_a", "upc_e", "code_128"] });
  } catch {
    return null;
  }
}

/** Find a barcode in a photo, or null if there isn't a readable one. */
export async function readBarcode(img: HTMLImageElement, zxing: BrowserMultiFormatReader | null): Promise<string | null> {
  const native = nativeDetector();
  for (const edge of BARCODE_EDGES) {
    const canvas = toCanvas(img, edge);
    if (native) {
      try {
        const found = await native.detect(canvas);
        if (found.length) return found[0].rawValue;
      } catch {
        // fall through to ZXing
      }
    }
    if (zxing) {
      try {
        return zxing.decodeFromCanvas(canvas).getText();
      } catch {
        // nothing found at this size
      }
    }
    if (Math.max(img.naturalWidth, img.naturalHeight) <= edge) break; // larger sizes would be identical
  }
  return null;
}

/** A small JPEG copy of the photo, suitable for the AI upload endpoints. */
export async function prepareForUpload(img: HTMLImageElement): Promise<File> {
  const canvas = toCanvas(img, UPLOAD_MAX_EDGE);
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
  if (!blob) throw new Error("Couldn't prepare that photo for upload.");
  return new File([blob], "photo.jpg", { type: "image/jpeg" });
}
