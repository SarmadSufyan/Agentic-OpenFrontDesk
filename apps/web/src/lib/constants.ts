import type { Day } from "./types";

export const GITHUB_URL = "https://github.com/SarmadSufyan/Agentic-OpenFrontDesk";

export const DAYS: { key: Day; label: string }[] = [
  { key: "mon", label: "Monday" },
  { key: "tue", label: "Tuesday" },
  { key: "wed", label: "Wednesday" },
  { key: "thu", label: "Thursday" },
  { key: "fri", label: "Friday" },
  { key: "sat", label: "Saturday" },
  { key: "sun", label: "Sunday" },
];

export const VERTICALS: { value: string; label: string }[] = [
  { value: "dental", label: "Dental or medical clinic" },
  { value: "salon", label: "Salon, spa or beauty" },
  { value: "legal", label: "Legal or accounting" },
  { value: "real_estate", label: "Real estate" },
  { value: "home_services", label: "Home services" },
  { value: "restaurant", label: "Restaurant or hospitality" },
  { value: "fitness", label: "Fitness or wellness" },
  { value: "education", label: "Education or training" },
  { value: "other", label: "Something else" },
];

export const TONES: { value: string; label: string; hint: string }[] = [
  { value: "friendly and professional", label: "Friendly", hint: "Warm, clear, and to the point" },
  { value: "calm and reassuring", label: "Reassuring", hint: "For clinics and sensitive topics" },
  { value: "concise and efficient", label: "Efficient", hint: "Short answers, no small talk" },
  { value: "upbeat and energetic", label: "Upbeat", hint: "For salons, gyms, hospitality" },
  { value: "formal and courteous", label: "Formal", hint: "For legal and financial firms" },
];

// Kokoro voices (the free self-hosted TTS). The worker applies the agent's voice per call.
export const VOICES: { value: string; label: string }[] = [
  { value: "af_heart", label: "Heart (US, female)" },
  { value: "af_bella", label: "Bella (US, female)" },
  { value: "af_nicole", label: "Nicole (US, female)" },
  { value: "am_michael", label: "Michael (US, male)" },
  { value: "am_adam", label: "Adam (US, male)" },
  { value: "bf_emma", label: "Emma (UK, female)" },
  { value: "bm_george", label: "George (UK, male)" },
];

export const HOURS_PRESETS: { label: string; days: Day[]; open: string; close: string }[] = [
  { label: "Weekdays 9 to 5", days: ["mon", "tue", "wed", "thu", "fri"], open: "09:00", close: "17:00" },
  { label: "Mon to Sat 9 to 6", days: ["mon", "tue", "wed", "thu", "fri", "sat"], open: "09:00", close: "18:00" },
  { label: "Every day 8 to 8", days: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"], open: "08:00", close: "20:00" },
];
