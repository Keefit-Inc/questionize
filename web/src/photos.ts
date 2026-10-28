// The learner's own photos stay in this browser (IndexedDB), keyed by error-log entry id.
// The server reads each photo once and deletes it, so this is the only copy we keep anywhere.
const DB = "questionize";
const STORE = "photos";

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function run<T>(mode: IDBTransactionMode, fn: (store: IDBObjectStore) => IDBRequest<T>): Promise<T | undefined> {
  try {
    const db = await open();
    return await new Promise<T>((resolve, reject) => {
      const req = fn(db.transaction(STORE, mode).objectStore(STORE));
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  } catch {
    // Private browsing or storage turned off: the photo simply isn't kept.
    return undefined;
  }
}

export async function savePhoto(entryId: number, blob: Blob): Promise<void> {
  await run("readwrite", (s) => s.put(blob, entryId));
}

/** An object URL for the entry's photo, or null if this browser doesn't have it. */
export async function photoUrl(entryId: number): Promise<string | null> {
  const blob = await run<Blob>("readonly", (s) => s.get(entryId) as IDBRequest<Blob>);
  return blob ? URL.createObjectURL(blob) : null;
}
