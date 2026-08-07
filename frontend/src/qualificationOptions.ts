import type { QualificationStatus } from "./types";

export const qualificationOptions: Array<{ value: QualificationStatus; label: string }> = [
  { value: "new", label: "New" },
  { value: "needs_review", label: "Needs review" },
  { value: "qualified", label: "Qualified" },
  { value: "shortlisted", label: "Shortlisted for Webify" },
  { value: "sent_to_veridra", label: "Sent to Veridra" },
  { value: "veridra_reviewed", label: "Veridra reviewed" },
  { value: "approved_for_outreach", label: "Approved for outreach" },
  { value: "contacted", label: "Contacted" },
  { value: "responded", label: "Responded" },
  { value: "conversation", label: "Conversation" },
  { value: "proposal", label: "Proposal" },
  { value: "customer", label: "Customer" },
  { value: "unsuitable", label: "Unsuitable" },
  { value: "duplicate", label: "Duplicate" },
  { value: "archived", label: "Archived" }
];
