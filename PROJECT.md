# Electronic Equipment Activity Log (eEAL) — Project Spec

**Source document:** Cipla Bommasandra, *Equipment Activity Log*, Doc No. 1035-A-0008/F1/6
**Status:** Draft v0.1
**Owner:** Kumar
**Date:** 2026-08-06

---

## Problem Statement

Equipment activity (cleaning status, PM completion, line clearance, campaign changeovers) is currently recorded on paper log sheets (Doc No. 1035-A-0008/F1/6) at each piece of equipment. Paper logs are slow to fill, hard to search or aggregate, prone to transcription errors, and require manual reconciliation against SOP 1035-A-0072 campaign-length rules. There is no automated way to flag an equipment item that has exceeded cleaning validity (Type A/B/C/G) or campaign length before the next batch starts, so overdue cleaning can go unnoticed until a line clearance check catches it.

This affects shop-floor operators (who fill the log), engineers (who log PM), QA (who verifies and audits it), and production section heads (who own equipment/area readiness and are accountable for it during audits). The cost of not solving it: delayed batch starts, deviation/CAPA risk from missed cleaning validity, and slow retrieval of records during audits.

## Goals

1. Replace the paper Equipment Activity Log with a web-based entry form that captures the same fields, per equipment, with the same field-level meaning as the source SOP.
2. Automatically compute and surface cleaning/PM validity status (e.g., "Type A valid until <date>", "Overdue") instead of relying on manual date math.
3. Cut the time to complete a log entry by 50% versus paper (target: under 90 seconds per entry).
4. Make historical entries searchable/filterable by equipment, product, date range, and status in under 5 seconds.
5. Produce an audit-ready, tamper-evident record that satisfies 21 CFR Part 11 for electronic GxP records.

## Non-Goals (v1)

- **Full SAP/MES integration** (auto-pulling batch numbers, material document numbers) — v1 will allow manual entry of the SAP document number field; system-to-system integration is a future phase.
- **Mobile native app** — v1 ships as a responsive web app usable on shop-floor tablets/PCs via browser; a dedicated native app is out of scope.
- **Digitizing other Cipla forms** (batch manufacturing records, deviation forms, etc.) — v1 covers only the Equipment Activity Log family, though the data model is built to extend to other equipment/batch logs (see "General Framework" below).
- **Offline-first / disconnected operation** — v1 assumes reliable plant network connectivity; offline queuing is a future consideration.
- **Running on validated equipment control HMIs** — the app will not be installed on or accessed through the machine's own control-system panel (Siemens/Rockwell/Wonderware, etc.), since that would put the app inside the equipment's validated automation change-control scope. It targets general-purpose shop-floor terminals (panel PCs, tablets, kiosks) positioned near equipment, not the equipment's control interface itself.
- **Automated fumigation/campaign scheduling** — the system will flag campaign length breaches per SOP 1035-A-0072 but will not auto-schedule fumigation or maintenance work orders.

## General Framework Intent

The source form is one of a family of equipment/batch GxP logs. Rather than hard-coding this single form, the system should model:
- **Log Types** as configurable templates (field list, field types, validation rules) so new log types (e.g., a different equipment log, a room activity log) can be added by configuration rather than new code.
- **Equipment Master** shared across log types (equipment code, equipment type, area/stream assignment, fixed vs. movable flag).
- **Equipment Type Master** (e.g. Reactor, ANFD, Multi Mill, Isolator, Sifter, Centrifuge, Jet Mill) as reference data, so equipment can be filtered/grouped by type and future type-specific fields or cleaning rules can be added without a schema change.
- **Equipment Usage Type Master** (e.g. Process, Cleaning, Maintenance, and others such as blank/trial run, preservation, buffing, breakdown, under maintenance — per the source form's Activity* footnote) as a configurable list that the "Activity" field on a log entry is selected from, instead of free text.
- **Area Hierarchy** (Production Block → Area/Stream, e.g. "API-2 (Production Block)" → "Stream-1", "Stream-2") as a configurable tree that equipment is mapped to, so plant layout can change without a code change.
- **Product Master** and **Cleaning Type rules** (A/B/C/G validity periods) as shared reference data, since the same cleaning-type logic likely applies to other forms.

v1 will implement one concrete Log Type (Equipment Activity Log, 1035-A-0008/F1/6) fully, built on this general schema, rather than building a generic form builder UI in v1.

## User Stories

**Operator (fills the log)**
- As an operator, I want to select my equipment by code and see its current status (In Use / To Be Cleaned / Cleaned / Dedicated / Not in Use) so I know what state it's in before I start work.
- As an operator, I want to log the start of an activity (date, time, my signature/login) so the system timestamps it as I begin.
- As an operator, I want to record whether adhered material was removed within 3 days post-process (Yes/No/NA) so the cleaning requirement is tracked.
- As an operator, I want to log the end of an activity and have the system auto-calculate the resulting status and validity date (e.g., "Type A valid until <date>") so I don't have to do the date math myself.
- As an operator, I want the system to warn me if I try to start a new activity on equipment that is past its cleaning validity or campaign length, so I don't use non-compliant equipment.

**QA Reviewer**
- As a QA reviewer, I want to see a dashboard of all equipment and their current status/validity so I can spot overdue cleaning at a glance.
- As a QA reviewer, I want to electronically verify/approve a completed log entry (Part 11 e-signature) so the record has the same review step as the paper "Verified By" line.
- As a QA reviewer, I want to filter/export entries by equipment, product, date range, or status for audits and investigations.
- As a QA reviewer, I want every edit to a submitted record to be captured in an audit trail (who, what, when, before/after value, reason) so nothing can be silently altered.
- As a QA reviewer, I want to configure the Area hierarchy — e.g. add "API-2 (Production Block)" and its Streams ("Stream-1", "Stream-2") — and map equipment into that hierarchy, so plant/area structure stays under QA ownership rather than general system admin.
- As a QA reviewer, I want to rename, add, or retire an Area/Stream (with old records retaining their original area reference) so historical entries stay accurate when plant layout changes.

**Engineer (Maintenance/Engineering)**
- As an engineer, I want to log PM completion against the schedule (Yes/No + reason if No) so PM compliance is visible without a separate system.
- As an engineer, I want to see which equipment is currently under maintenance or breakdown status so I can prioritize my work.
- As an engineer, I want to update equipment status to "Under Maintenance"/"Breakdown" and back, so operators know not to use it in the meantime.

**Production Section Head**
- As a production section head, I want a summary view of all equipment status in my section (clean/to-be-cleaned/overdue/in-use/under maintenance) so I can plan the next batch without walking the floor.
- As a production section head, I want to be notified when equipment in my section is approaching or has exceeded cleaning/campaign validity, so I can intervene before it blocks production.
- As a production section head, I want to review and, where required, sign off on line clearance before a new batch starts in my section, so accountability matches how the paper process works today.
- As a production section head, I want to see overdue PM or recurring breakdowns in my section so I can escalate to engineering.

**Administrator** *(system/technical role, distinct from the four business roles above)*
- As an administrator, I want to manage the Equipment Master, Product Master, and Cleaning Type validity rules so the system reflects current SOPs without a code change.
- As an administrator, I want to configure user roles (Operator, Engineer, QA, Production Section Head, Admin) and permissions so access matches responsibility.

**Edge cases**
- As an operator, I want to be blocked from submitting an entry with missing required fields (e.g., no signature) so incomplete records can't be saved as final.
- As a QA reviewer, I want to see equipment with "Not in Use" or expired-validity status highlighted separately from active equipment, so stale equipment doesn't clutter the active view.
- As a production section head, I want a read-only view by default (no ability to edit entries), so my sign-off role doesn't overlap with QA's verification role or create a conflict of interest.

## Requirements

### Must-Have (P0)

1. **Equipment Activity Log entry form** replicating the source fields: Product, Batch No./Cleaning SOP No./Equipment Maintenance SOP No./#SAP Doc No., Area/Cubicle, PM completed per schedule (Y/N + reason), Activity type (selected from the Equipment Usage Type master), Start of Activity (date/time/sign), Adhered material removed within 3 days (Y/N/NA + date/sign), End of Activity (date/time/sign), Status, Sr. No. of batch after changeover cleaning, Campaign Product Changeover Cleaning due date, Reference ECR No., Line Clearance Bound Book No. + certified date, Remarks.
   - *Acceptance:* All fields from source form 1035-A-0008/F1/6 are present, correctly typed (date/time/text/select/signature), and required fields are enforced before submission.
2. **Equipment Master, Product Master, Equipment Type Master, and Equipment Usage Type Master** CRUD (admin-managed reference data), with Equipment Code, Equipment Type (Reactor, ANFD, Multi Mill, Isolator, Sifter, Centrifuge, Jet Mill, etc.), Usage Type (Process, Cleaning, Maintenance, etc.), Department, fixed/movable flag.
   - *Acceptance:* Admin can add/edit/deactivate equipment, equipment types, usage types, and products; entries reference these masters rather than free text; equipment list/dashboard can be filtered by type and usage type; activity/status logic (e.g. cleaning validity engine) keys off Usage Type rather than a free-text activity description.
3. **Area Hierarchy Master**, QA-managed: a configurable tree of Production Block → Area/Stream (e.g. "API-2 (Production Block)" → "Stream-1", "Stream-2"), with equipment mapped to a specific node in the hierarchy in place of the free-text "Area/Cubicle" field on the paper form.
   - *Acceptance:* A QA user can create/rename/retire a Block or Stream and reassign equipment between Streams; a non-QA user cannot modify the hierarchy (enforced server-side); existing log entries retain the area value as it was at time of entry even if the hierarchy later changes.
4. **Cleaning validity engine**: given cleaning type (A/B/C/G) and completion date, compute and display validity expiry per the rules in the SOP (A: 6 days, B: 6 weeks, C: 6 weeks, G: 6 days; "To be cleaned": 3 days).
   - *Acceptance:* Given a completed activity with a cleaning type, the system correctly computes and displays the expiry date and flags "Expired" once passed.
5. **Status tracking**: equipment status values (Dedicated valid up to X / Cleaned valid up to X / To be cleaned valid up to X / Not in use) visible per equipment.
   - *Acceptance:* Status shown on equipment list/dashboard matches the latest log entry's computed state.
6. **Electronic signature & audit trail (21 CFR Part 11)**: unique login per user, e-signature (re-authentication) on record submission and QA verification, immutable audit log of create/edit/approve actions with timestamp, user, and reason for change.
   - *Acceptance:* Every submitted or edited record has an associated signed event in the audit trail; audit trail is read-only and exportable.
7. **Role-based access control**: Operator, Engineer, QA Reviewer, Production Section Head, and Admin roles with distinct permissions (e.g., Operator: create/edit own entries; Engineer: log PM and equipment maintenance status; QA: verify/approve entries, full audit trail access, manage Area hierarchy; Production Section Head: read-only status view across their section plus line-clearance sign-off; Admin: Equipment/Product master data and user management).
   - *Acceptance:* A user without QA role cannot perform the QA verification action or edit the Area hierarchy; a Production Section Head cannot edit a log entry; enforced server-side, not just hidden in UI.
8. **Search/filter/export** of entries by equipment, product, area/stream, date range, and status.
   - *Acceptance:* Results return in under 5 seconds for a typical query; export to CSV/PDF available.
9. **Campaign length check**: flag when a product's campaign (days or batches, whichever earlier, per SOP 1035-A-0072) is exceeded and cleaning of all process equipment is required before the next batch.
   - *Acceptance:* System blocks/warns when starting a new batch on equipment whose campaign length is exceeded, referencing the applicable rule.

### Nice-to-Have (P1)

1. Kiosk-mode UI tuned for shop-floor panel PCs/touchscreen terminals stationed near equipment (large touch targets, minimal scrolling, auto-login or badge-scan session start) — distinct from, and not installed on, the equipment's own control-system HMI.
2. Equipment status dashboard with visual (color-coded) overview of all equipment by area.
3. Configurable notifications (email/in-app) to QA/operators when validity is nearing expiry.
4. Bulk import of historical paper log data for a cutover period.
5. Printable PDF rendering of an entry that visually matches the original paper form layout, for audits that still expect the familiar format.
6. Reason-code dropdown (rather than free text) for "PM not completed as per schedule."

### Future Considerations (P2)

1. Generic log-type/form builder so new log templates can be configured without engineering work.
2. SAP/MES integration for auto-populated batch and material document numbers.
3. Native mobile app with barcode/QR scanning of equipment codes.
4. Offline entry queuing for areas with unreliable connectivity.
5. Auto-scheduling of fumigation/maintenance work orders triggered by campaign-length breaches.

## Technology & Non-Functional Requirements

**Scale target:** 50+ concurrent users. This is a light load for a conventional 3-tier web app — no microservices, container orchestration, or horizontal auto-scaling needed. A single application server (roughly 4 vCPU / 8GB RAM) plus a database instance is sufficient.

**Thin-client / low-traffic constraint:** shop-floor terminals are expected to be low-spec thin clients on constrained plant network segments, so the architecture favors server-rendered pages over a heavy client-side SPA:
- Backend renders HTML server-side (e.g. ASP.NET Razor Pages, Spring MVC + Thymeleaf, or Django templates) rather than shipping a large JavaScript bundle to the client.
- A lightweight interactivity layer (htmx or Alpine.js) handles partial-page updates so each user action (e.g., submitting a log entry) is a small, targeted request rather than a full SPA re-render or a large JSON round-trip.
- Static assets kept minimal and cached aggressively (long cache lifetimes, gzip/Brotli compression) so repeat visits transfer close to zero data.
- No polling or real-time push where a simple page refresh will do — favors bandwidth savings over UI polish.

**Backend:** Java/Spring Boot or .NET (ASP.NET Core) — mature RBAC/audit-trail support and the ecosystem most GxP computer-system-validation teams are already familiar with. Python/Django is a reasonable alternative if the team's stronger there.

**Database:** PostgreSQL or SQL Server — relational, ACID-compliant, straightforward to model the audit trail and Part 11 record integrity requirements against.

**Hosting:** on-prem or a validated private cloud environment (pending the data-residency open question below); single app server + DB instance is enough at this scale.

**Auth:** plant AD/SSO via SAML or OAuth2/OIDC where available; otherwise local login with badge/PIN for shared kiosk terminals.

## Data Model (draft)

- **Area**: id, name (e.g. "API-2", "Stream-1"), type (Block/Stream), parent_area_id (nullable, self-reference — null for top-level Block), active flag, managed_by_role = QA
- **EquipmentType**: id, name (Reactor, ANFD, Multi Mill, Isolator, Sifter, Centrifuge, Jet Mill, etc.), active flag
- **EquipmentUsageType**: id, name (Process, Cleaning, Maintenance, Blank/Trial Run, Preservation, Buffing, Breakdown, Under Maintenance, etc.), active flag
- **Equipment**: id, code, equipment_type_id (FK → EquipmentType), department, area_id (FK → Area, leaf-level Stream), fixed/movable flag, active flag
- **Product**: id, name, campaign length (days), campaign length (batches)
- **CleaningTypeRule**: type (A/B/C/G/ToBeCleaned), validity period
- **ActivityLogEntry**: id, equipment_id, area_id_snapshot (area path at time of entry, e.g. "API-2 / Stream-1", captured so later hierarchy edits don't rewrite history), product_id, batch_no, cleaning_sop_no, equipment_maintenance_sop_no, sap_doc_no, pm_completed (Y/N), pm_not_completed_reason, usage_type_id (FK → EquipmentUsageType), start_date, start_time, start_sign_user_id, adhered_material_removed (Y/N/NA), adhered_material_date, adhered_material_sign_user_id, end_date, end_time, end_sign_user_id, status, cleaning_type, validity_expiry_date, batch_seq_after_changeover, campaign_changeover_due_date, reference_ecr_no, line_clearance_book_no, line_clearance_certified_date, remarks, created_by, created_at
- **AuditTrailEvent**: id, entity_type, entity_id, action (create/edit/approve), user_id, timestamp, field_changed, old_value, new_value, reason
- **User**: id, name, role (Operator/Engineer/QA/Production Section Head/Admin), department, section, active flag

## Success Metrics

**Leading indicators**
- Entry completion time: target median under 90 seconds (baseline: paper form time, to be measured pre-launch).
- Adoption rate: 90% of eligible equipment logs entered digitally within 30 days of rollout per line.
- Error/validation-block rate: track how often submissions are blocked for missing fields, trending down over first 4 weeks.

**Lagging indicators**
- Reduction in cleaning-validity-related deviations/CAPAs (compare 6 months pre- vs. post-launch).
- Audit finding turnaround time (time to retrieve requested records during an audit).
- QA review cycle time per entry.

Measurement: pulled from application logs/database; evaluated at 30 days (adoption, completion time) and 1 quarter (deviations, audit turnaround) post-launch.

## Open Questions

- What authentication system should this integrate with — plant SSO/AD, or a standalone login? (engineering)
- Is 21 CFR Part 11 validation (IQ/OQ/PQ, computer system validation per GAMP 5) required before go-live, and who owns that validation package? (QA/compliance)
- Should historical paper logs be backfilled into the system, or does digital tracking start fresh at cutover? (stakeholder)
- Which equipment/area should be the pilot line before wider rollout? (stakeholder)
- Hosting: on-premise plant server vs. corporate cloud environment, given GxP data residency requirements? (engineering/IT)
- Who is the system owner for maintaining Equipment/Product master data and cleaning-type rules going forward? (stakeholder)
- What shop-floor terminals are actually available at each equipment location — dedicated panel PCs, shared tablets, or none yet requiring new hardware — and what OS/browser do they run? (engineering/IT)
- Should terminal sessions support quick badge-scan/PIN login for shared devices, or is per-user laptop/tablet login sufficient? (design/engineering)

## Timeline Considerations

- No hard external deadline identified yet — to be set once a pilot line is chosen.
- Dependency: Part 11 / GAMP 5 validation requirements must be scoped with QA/compliance before development starts, since they affect architecture (audit trail, e-signature) from day one rather than being retrofitted.
- Suggested phasing:
  - **Phase 1**: P0 requirements, single pilot equipment/area, core log entry + validity engine + e-signature/audit trail.
  - **Phase 2**: Rollout to remaining equipment/areas, P1 dashboard and notifications.
  - **Phase 3**: P2 items (integration, mobile, generic form builder) based on Phase 1–2 learnings.
