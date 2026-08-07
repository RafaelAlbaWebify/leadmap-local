# Webify commercial acquisition roadmap

LEADS is now part of the wider Webify Digital Solutions commercial system. The immediate objective is not to finish LEADS as a standalone product. The objective is to use LEADS to produce a real SMB prospect shortlist, pass selected domains into Veridra, support Webify outreach, and learn a repeatable customer-acquisition process.

## Operating test

Before substantial LEADS work, ask:

> Does this materially shorten or improve the route from search -> qualified SMB -> Veridra audit -> Webify outreach -> paying customer?

If not, backlog it.

## System workflow

1. LEADS discovers suitable SMBs.
2. LEADS collects and structures public business and website/domain evidence.
3. LEADS deduplicates and qualifies prospects.
4. A human selects businesses worth deeper investigation.
5. Selected websites/domains are handed to Veridra.
6. Veridra performs evidence-based website assessment.
7. A human selects commercially meaningful problems.
8. Webify Business determines the service/offer.
9. Outreach starts manually.
10. Commercial conversations and proposals are tracked.
11. First payment and delivery are recorded.
12. Repeatable weekly acquisition metrics are reviewed.

## System responsibilities

- LEADS answers: Is this potentially a customer?
- Veridra answers: What is demonstrably wrong with the website?
- Webify Business answers: Is that problem worth selling a solution to?

LEADS should not perform deep technical website qualification. Veridra should not optimize for the largest number of findings. Webify Business should not create outreach until a human has verified the evidence, business relevance, fixability and offer fit.

## Webify Qualification v0.1

The purpose of LEADS qualification is not to identify websites with the most problems. It is to identify businesses most likely to buy and benefit from the EUR 299 Webify Website Fix.

Use two consecutive filters rather than one complicated score:

1. Stage A: LEADS commercial qualification decides whether the company itself is worth investigating.
2. Stage B: Veridra opportunity qualification investigates selected websites/domains and classifies evidence by commercial usefulness.

This prevents Veridra from wasting resources auditing every discovered business.

### Stage A: LEADS commercial qualification

LEADS should first determine whether the company itself is worth investigating.

| Criterion | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Active real business | doubtful/inactive | probably active | clearly active |
| Website commercial importance | incidental | useful | important for leads/bookings/credibility |
| Business economic value | very low-value transactions | moderate | one customer likely worth hundreds+ |
| Business size/fit | unsuitable | borderline | owner-managed SMB, roughly 2-30 staff |
| Decision-maker reachability | none | generic contact only | owner/manager identifiable |
| Website/platform manageability | complex/high-risk | uncertain | conventional manageable SMB site |
| Existing agency/internal team | clearly present | unclear | apparently none |

Maximum score: 14.

Initial rule:

- 11-14: send to Veridra.
- 8-10: hold / secondary.
- 0-7: reject.

Automatic rejection overrides the score when any of the following is true:

- inactive or closed business;
- large enterprise or public organisation;
- complex ecommerce or custom application;
- obviously sophisticated internal marketing/web operation;
- website essentially irrelevant to obtaining business;
- no legitimate contact route;
- obvious indication Webify could not safely deliver the likely work.

Stage A should produce a clear human-reviewable reason, not just a number. The shortlist should explain why the business is commercially plausible for Webify and why it is or is not worth sending to Veridra.

### Stage B: Veridra opportunity qualification

Once a business passes Stage A, Veridra looks for commercially useful evidence. Findings should be classified by commercial usefulness, not just technical severity.

#### A: Direct commercial problem

Commercial opportunity score: 4.

Best outreach material. Examples:

- broken enquiry/contact form;
- booking/request-a-quote flow does not work;
- important page returns an error;
- obvious broken mobile functionality;
- important navigation link broken;
- phone/email CTA malfunction;
- severe loading problem on key landing page;
- HTTPS/browser warning;
- critical information unavailable to visitors.

#### B: Strong visibility/usability problem

Commercial opportunity score: 3.

Good potential outreach material. Examples:

- important pages accidentally non-indexable;
- malformed robots/indexation configuration;
- broken sitemap;
- substantial broken internal links;
- major metadata problems across important pages;
- serious mobile presentation problem;
- extremely oversized assets;
- obviously poor Core Web/technical performance where remediation is straightforward;
- canonical configuration sending search engines to the wrong URLs.

#### C: Credibility / quality problem

Commercial opportunity score: 2.

Useful mainly in combination. Examples:

- inconsistent business/contact information;
- missing important trust information;
- obvious structured-data problems;
- poor social-preview metadata;
- inaccessible forms;
- widespread missing alt descriptions;
- basic accessibility problems;
- weak security configuration that can sensibly be fixed.

#### D: Technical hygiene

Commercial opportunity score: 1.

Normally not enough to contact somebody. Examples:

- CSP improvements;
- HSTS tuning;
- DMARC/SPF improvements;
- referrer policy;
- minor schema opportunities;
- AI-crawler directives;
- llms.txt;
- minor HTML cleanliness;
- small optimisation opportunities.

D findings may become upsells or supporting evidence, but Webify should resist turning technically interesting observations into fake sales urgency.

### Outreach approval threshold

A business becomes approved for outreach only when one of these routes is satisfied:

1. At least one A finding.
2. At least two B findings.
3. One B finding plus at least two C findings.

AND:

> The important problems can realistically be addressed within the EUR 299 package or naturally lead to a clearly scoped higher quote.

A finding is not automatically an opportunity. For example, a severe performance problem caused by a proprietary booking platform may be real, but if Webify cannot change it safely then it is not a Webify Website Fix opportunity.

### Human review gate

Do not let LEADS or Veridra automatically trigger outreach yet.

Every candidate reaching the threshold requires manual review:

1. Is the evidence actually correct? Open the site and reproduce it.
2. Would an owner care? Translate the technical finding into a business consequence.
3. Can Webify fix it? No speculative promises.
4. Is EUR 299 plausible? Estimate effort before contact.
5. Is there a natural, non-spammy reason to write? The outreach must be specific.

Only then set the candidate to approved for outreach.

### Prospect record v0.1

For now, a table is sufficient. Preserve these fields when repetition warrants software support:

| Field | Example |
| --- | --- |
| Business | Murphy Roofing Ltd |
| Domain | example.ie |
| Sector | Roofing |
| Location | Cork |
| Estimated SMB fit | Strong |
| Website importance | High |
| Contact | Owner / general email |
| Platform | WordPress |
| LEADS score | 13/14 |
| Veridra A | 1 |
| Veridra B | 2 |
| Veridra C | 4 |
| Best observation | Quote form fails |
| Webify fixable? | Yes |
| Estimated effort | 2.5 h |
| Likely offer | Website Fix EUR 299 |
| Human verified | Yes |
| Outreach status | Approved |
| Rejection/loss reason | - |

### Rejection taxonomy

Track why candidates fail from the beginning. This will show whether the ICP, discovery source, Veridra criteria or Webify offer is wrong.

Use:

- BUSINESS_INACTIVE
- TOO_SMALL_LOW_VALUE
- TOO_LARGE
- WEBSITE_NOT_IMPORTANT
- INTERNAL_WEB_TEAM
- AGENCY_PRESENT
- NO_CONTACT_ROUTE
- TECH_TOO_COMPLEX
- NO_MEANINGFUL_FINDINGS
- FINDINGS_NOT_FIXABLE
- FIX_TOO_LARGE_FOR_OFFER
- LOW_COMMERCIAL_IMPACT
- EVIDENCE_UNCERTAIN
- DUPLICATE
- OTHER

Later, measure the funnel as a real conversion chain, for example:

> 100 discovered -> 45 rejected before scan -> 55 scanned -> 18 meaningful -> 9 commercially fixable -> 5 contacted -> customer outcomes.

This is more useful than counting how many websites Veridra audited.

### Website Fix offer wording

Avoid promising a flat "up to 3 fixes" as if all fixes are equal.

Preferred wording:

> A defined Website Fix scope agreed before payment, normally covering up to three bounded priority issues.

The scope, not the number three, controls the work.

## Phase 1: SMB shortlist

Goal: produce a real, human-reviewable SMB shortlist of businesses likely to buy and benefit from the EUR 299 Webify Website Fix.

LEADS must show:

- business name;
- website/domain;
- sector/category;
- territory/location;
- current commercial state;
- Stage A qualification score;
- Stage A decision: send to Veridra, hold / secondary, or reject;
- automatic rejection reason, when applicable;
- why this business may be worth Webify investigation;
- basic evidence summary.

Do not build website assessment here. That belongs to Veridra.

## Phase 2: Veridra handoff

Goal: export selected shortlisted prospects so Veridra/Webify can continue without rediscovering the business.

Minimum handoff fields:

- business name;
- website/domain;
- sector/category;
- territory/location;
- discovery status;
- Stage A qualification score;
- Stage A decision;
- qualification reason;
- automatic rejection reason, when applicable;
- evidence summary;
- timestamp.

CSV and JSON exports are enough before direct integration.

## Phase 3: Veridra assessment intake contract

Goal: define the contract between LEADS and Veridra.

Veridra should return or produce:

- domain;
- observed issue;
- evidence;
- commercial meaning;
- commercial opportunity class: A, B, C or D;
- likely service category;
- severity/priority;
- Webify fixability estimate;
- estimated effort;
- human-review status.

LEADS should store only references and status needed for the commercial funnel.

## Phase 4: Webify offer selection

Goal: turn approved Veridra findings into a service angle.

LEADS may track:

- approved for outreach;
- selected service category;
- likely offer;
- estimated effort;
- outreach rationale;
- link/reference to Veridra assessment.

Offer packaging, pricing and proposal text belong to the Webify Business workflow unless later evidence proves they should be inside LEADS.

## Phase 5: Manual outreach tracking

Goal: track manual contact outcomes.

Allowed states include:

- contacted;
- responded;
- conversation;
- not interested;
- follow-up later;
- proposal requested.

No automatic outbound messaging in this phase.

## Phase 6: Proposal and customer outcome

Goal: record first customer outcome.

LEADS may track:

- proposal sent;
- customer won/lost;
- revenue amount;
- close notes;
- external proposal link.

Do not build invoicing or payment processing here.

## Phase 7: Repeatable acquisition loop

Goal: learn which discovery paths produce customers.

Track conversion through:

- discovered;
- website found;
- Stage A qualified;
- shortlisted;
- sent to Veridra;
- Veridra meaningful finding;
- commercially fixable;
- approved after human review;
- contacted;
- response;
- conversation;
- proposal;
- customer;
- revenue.

The output should guide the next sector, territory and search query.

## Current implementation anchor

Issue #98 is the commercial milestone. Phase issues #99 through #105 split that milestone into executable slices.

The first implemented slice was #99 + #100: shortlist plus Veridra handoff export.

The next LEADS slice should not be outreach templates. The next operational move is to select the first 10 Webify Website Fix candidates using Stage A qualification, then hand the qualified set to Veridra and bring the results back to Webify Business for commercial decision.
