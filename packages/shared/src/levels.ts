// Learner levels and subjects as the apps show them.
import type { LevelId, QuestionType, Scene } from "./types";

export interface LevelInfo {
  id: LevelId;
  label: string;
  group: "School" | "College & adult" | "Test prep";
  detail: string;
}

export const LEVELS: LevelInfo[] = [
  { id: "elementary", label: "Grades 3–5", group: "School", detail: "Short, friendly passages. For a parent or teacher practicing with a child." },
  { id: "middle", label: "Grades 6–8", group: "School", detail: "Claims, evidence and assumptions in plain words." },
  { id: "high", label: "Grades 9–12", group: "School", detail: "High school arguments, SAT and ACT style." },
  { id: "college", label: "College & adult", group: "College & adult", detail: "Everyday critical thinking at a newspaper level." },
  { id: "gmat", label: "GMAT", group: "Test prep", detail: "Critical Reasoning and Reading Comprehension." },
  { id: "lsat", label: "LSAT", group: "Test prep", detail: "Logical Reasoning: precise, formal arguments." },
  { id: "gre", label: "GRE", group: "Test prep", detail: "Verbal reasoning on academic topics." },
];

export const levelInfo = (id: string | null | undefined): LevelInfo | undefined => LEVELS.find((l) => l.id === id);

/** Subjects, with the colors their thumbnails use. Critical Reasoning and Reading come first; others follow as subject packs arrive. */
export const SUBJECTS: Record<string, { name: string; short: string; from: string; to: string }> = {
  CR: { name: "Critical Reasoning", short: "Reasoning", from: "#3d6bf2", to: "#7a4fd3" },
  RC: { name: "Reading Comprehension", short: "Reading", from: "#e2557d", to: "#f29a4a" },
  SC: { name: "Sentence Correction", short: "Writing", from: "#13a38a", to: "#3bb5d8" },
  MATH: { name: "Math", short: "Math", from: "#f28a1b", to: "#f2c94c" },
  BIO: { name: "Biology", short: "Biology", from: "#2f9e57", to: "#9ccc3a" },
};

export const subjectOf = (family: QuestionType | string) => SUBJECTS[family] ?? SUBJECTS.CR;

export const SCENE_EMOJI: Record<Scene, string> = {
  everyday: "🏠", school: "🏫", science: "🔬", health: "🩺", nature: "🌳", animals: "🐾", city: "🏙️", business: "📈",
  technology: "💻", sports: "⚽", arts: "🎨", history: "🏛️", food: "🍎", law: "⚖️", space: "🚀", transport: "🚲",
};

const SCENE_WORDS: [Scene, RegExp][] = [
  ["transport", /\b(bike|bicycle|traffic|car|bus|train|road|street|commute|airline|flight)s?\b/i],
  ["health", /\b(hospital|doctor|patient|vaccine|disease|health|medic|clinic|diet)\w*/i],
  ["school", /\b(school|student|teacher|class|library|exam|university|college)\w*/i],
  ["science", /\b(researcher|scientist|study|experiment|laboratory|chemical|species)\w*/i],
  ["animals", /\b(dog|cat|bird|fish|animal|wildlife|pet)s?\b/i],
  ["nature", /\b(forest|river|climate|tree|ocean|farm|crop|weather|drought)s?\b/i],
  ["business", /\b(company|profit|sales|market|price|revenue|customer|store|investor)s?\b/i],
  ["technology", /\b(software|app|computer|phone|internet|robot|digital|online)s?\b/i],
  ["sports", /\b(team|player|coach|game|league|athlete|stadium)s?\b/i],
  ["arts", /\b(museum|artist|music|film|painting|theater|novel)s?\b/i],
  ["food", /\b(restaurant|food|meal|coffee|chef|recipe|grocery)\w*/i],
  ["law", /\b(court|law|judge|police|crime|policy|regulation|council|mayor)\w*/i],
  ["space", /\b(planet|space|astronaut|telescope|moon|mars)\b/i],
  ["history", /\b(ancient|century|historian|empire|war)\w*/i],
  ["city", /\b(city|town|downtown|neighborhood|resident)s?\b/i],
];

/** The item's scene, or a best guess from its passage for items written before scenes existed. */
export function sceneFor(item: { scene?: string | null; passage: string }): Scene {
  if (item.scene && item.scene in SCENE_EMOJI) return item.scene as Scene;
  return SCENE_WORDS.find(([, re]) => re.test(item.passage))?.[0] ?? "everyday";
}
