export type ScriptType = "presentation" | "dialogue" | "story" | "debate" | "analysis" | "daily recap" | "music";

export interface Slot {
  id: string;
  start_time: string; // "HH:MM"
  duration_sec: number;
  thematique: string;
  nb_intervenants: number;
  noms: string[];
  langue: string;
  type_script: ScriptType;
  sujet: string | null;
  script: string | null;
  image_path: string | null;
  audio_path: string | null;
  last_generated_at: string | null;
}

export type Programme = Slot[];

export type PlayerMode = "live" | "replay";
