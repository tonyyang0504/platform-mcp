/** Category verb vocabularies. Single source: the catalog's schema/vocab.json (catalog.ts finds it: the copy
 * packed into the npm package, or the checkout). */
import { vocab } from "./catalog.js";
import { isGeneric, vocab as genericVocab } from "./generic.js";

export interface Verb { title: string; description: string; read_only: boolean; destructive?: boolean; idempotent?: boolean; input: Record<string, unknown>; output: Record<string, unknown> }

export function loadAll(): Record<string, Record<string, Verb>> {
  return vocab() as Record<string, Record<string, Verb>>;
}
export function vocabFor(spec: { category: string; vocab?: Record<string, Verb>; adapter?: any }): Record<string, Verb> {
  if (isGeneric(spec)) return genericVocab(spec) as Record<string, Verb>; // a generic entry's own tool definitions (generic.ts)
  if (spec.vocab && Object.keys(spec.vocab).length) return spec.vocab;
  return loadAll()[spec.category];
}
