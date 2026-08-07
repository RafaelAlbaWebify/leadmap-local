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

## Phase 1: SMB shortlist

Goal: produce a real, human-reviewable SMB shortlist.

LEADS must show:

- business name;
- website/domain;
- sector/category;
- territory/location;
- current commercial state;
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
- qualification reason;
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
- likely service category;
- severity/priority;
- human-review status.

LEADS should store only references and status needed for the commercial funnel.

## Phase 4: Webify offer selection

Goal: turn approved Veridra findings into a service angle.

LEADS may track:

- approved for outreach;
- selected service category;
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
- qualified;
- shortlisted;
- sent to Veridra;
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

The first buildable slice is #99 + #100: shortlist plus Veridra handoff export.
