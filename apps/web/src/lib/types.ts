// Shapes returned by the OpenFrontDesk API (see src/ofd/schemas/* in the backend).

export type Role = "owner" | "admin" | "member";

export interface TokenOut {
  access_token: string;
  refresh_token: string;
  token_type: string;
  tenant_id: string | null;
}

export interface Membership {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  role: Role;
}

export interface Me {
  user: { id: string; email: string; name: string | null; is_active: boolean; created_at: string };
  memberships: Membership[];
  is_admin: boolean;
}

export type Day = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun";
export type BusinessHours = Partial<Record<Day, [string, string] | null>>;

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  vertical: string | null;
  timezone: string;
  business_hours: BusinessHours;
  address: Record<string, unknown>;
  settings: Record<string, unknown>;
  plan: string;
  created_at: string;
}

export interface Agent {
  id: string;
  name: string;
  voice: string;
  greeting: string;
  tone: string;
  persona: Record<string, unknown>;
  escalation_rules: Record<string, unknown>;
  booking_rules: { slot_minutes?: number; services?: string[] } & Record<string, unknown>;
  is_active: boolean;
}

export type DocStatus = "pending" | "processing" | "ready" | "failed";

export interface KnowledgeDoc {
  id: string;
  title: string;
  source_type: string;
  status: DocStatus;
  char_count: number;
  chunk_count: number;
  error: string | null;
  created_at: string;
}

export interface SearchHit {
  text: string;
  score: number;
  source_title: string | null;
}

export interface Call {
  id: string;
  direction: string;
  status: string;
  outcome: string | null;
  caller_number: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number;
  cost_cents: number;
  created_at: string;
}

export interface CallDetail extends Call {
  transcript: { role: string; text: string }[];
  summary: string | null;
  latency_ms: Record<string, unknown>;
}

export interface Booking {
  id: string;
  customer_name: string | null;
  customer_phone: string | null;
  service: string | null;
  start_at: string;
  end_at: string | null;
  status: string;
  created_at: string;
}

export interface Lead {
  id: string;
  name: string | null;
  phone: string | null;
  email: string | null;
  intent: string | null;
  message: string | null;
  created_at: string;
}

export interface Analytics {
  calls_total: number;
  calls_by_outcome: Record<string, number>;
  bookings_total: number;
  leads_total: number;
  minutes_total: number;
  avg_latency_ms: number | null;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatReply {
  reply: string;
  sources: string[];
  session_id?: string | null;
}

export interface VoiceAcquire {
  status: "granted" | "queued";
  capacity?: number | null;
  session_ttl?: number | null;
  url?: string | null;
  token?: string | null;
  room?: string | null;
  identity?: string | null;
  position?: number | null;
  active?: number | null;
}

export interface EventType {
  type: string;
  description: string;
}

export interface Webhook {
  id: string;
  url: string;
  description: string | null;
  events: string[];
  is_active: boolean;
  failure_count: number;
  last_status: number | null;
  last_delivery_at: string | null;
  created_at: string;
  secret_hint: string;
  secret?: string;
}

export interface Delivery {
  id: string;
  event_id: string;
  event: string;
  success: boolean;
  status_code: number | null;
  attempts: number;
  error: string | null;
  duration_ms: number | null;
  created_at: string;
}

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string;
  key?: string;
}

export interface ContactOptions {
  needs: Record<string, string>;
  team_sizes: string[];
  budgets: string[];
  scheduling_enabled: boolean;
}

export interface ContactAccepted {
  id: string | null;
  status: string;
  scheduling_url: string | null;
  message: string;
}

export type ContactStatus = "new" | "contacted" | "scheduled" | "won" | "lost" | "spam";

export interface ContactRequest {
  id: string;
  name: string;
  email: string;
  company: string | null;
  phone: string | null;
  website: string | null;
  team_size: string | null;
  needs: string[];
  budget: string | null;
  message: string;
  status: ContactStatus;
  notes: string | null;
  meeting_at: string | null;
  meeting_link: string | null;
  handled_by: string | null;
  last_contacted_at: string | null;
  user_id: string | null;
  tenant_id: string | null;
  source: string | null;
  created_at: string;
}

export interface ContactPage {
  items: ContactRequest[];
  total: number;
  counts: Record<ContactStatus, number>;
}

export interface VoiceSessions {
  capacity: number;
  active: { tenant: string; expires_in: number }[];
  queue: string[];
}

export interface AllowlistEntry {
  email: string;
  note: string | null;
  created_at: string;
}
