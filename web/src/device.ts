// What stays only on this device: the questions the learner snapped, word for word, so they can
// solve them again. The server hands each one over once and keeps no copy; photos are not kept.
import type { SourceQuestion } from "@questionize/shared";

const DB = "questionize";
const STORE = "questions";

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 2);
    req.onupgradeneeded = () => {
      const db = req.result;
      // Version 1 kept photos; once a question is read they are no longer needed.
      if (db.objectStoreNames.contains("photos")) db.deleteObjectStore("photos");
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE);
    };
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
    // Private browsing or storage turned off: nothing is kept.
    return undefined;
  }
}

export async function saveQuestion(entryId: number, question: SourceQuestion): Promise<boolean> {
  return (await run("readwrite", (s) => s.put(question, entryId))) !== undefined;
}

export async function loadQuestion(entryId: number): Promise<SourceQuestion | null> {
  return (await run<SourceQuestion>("readonly", (s) => s.get(entryId) as IDBRequest<SourceQuestion>)) ?? null;
}
