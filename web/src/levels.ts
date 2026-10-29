import { LEVELS } from "@questionize/shared";

// The full level catalog stays available to the API and future subject packs.
// Set VITE_ALL_LEVELS=true at build time to show the wider audience in the app.
export const ALL_LEVELS_VISIBLE = import.meta.env.VITE_ALL_LEVELS === "true";
export const VISIBLE_LEVELS = ALL_LEVELS_VISIBLE ? LEVELS : LEVELS.filter((level) => ["gmat", "lsat", "gre"].includes(level.id));
export const DEFAULT_LEVEL = "gmat" as const;
