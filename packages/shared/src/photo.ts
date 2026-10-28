// Shrinks a photo in the browser before upload, so a phone picture fits the server's 6 MB limit.
// The blob is what the learner keeps on their own device; the data URL is what the server reads once.
const MAX_SIDE = 1600;

export interface PreparedPhoto {
  dataUrl: string;
  blob: Blob;
  width: number;
  height: number;
}

export async function preparePhoto(file: Blob): Promise<PreparedPhoto> {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
  const blob = await (await fetch(dataUrl)).blob();
  return { dataUrl, blob, width: canvas.width, height: canvas.height };
}
