# Synthetic Repair Case Fixture

This isolated fixture contains fictional test evidence for ResolveAI. No documents were uploaded and no application case was created. All PDFs prominently carry the exact required disclaimer. All names, addresses, events, amounts and references are invented; the `.invalid` email domains are reserved placeholders. These files are not official records, manufacturer policies, or legal claims.

## Case summary

- Product: Sony WHM1000X wireless headphones (model reference WHM1000X)
- Customer: Mira Sen (fictional); fictional Chennai address
- Purchase: 14 January 2025; INR 18,999.00; invoice SIM-INV-250114-017
- Illustrative coverage: 14 January 2025 through 13 January 2026
- Repair visits: 3 February 2025 (SIM-JOB-250203-A) and 18 March 2025 (SIM-JOB-250318-B)
- Reported fault: unexpected power-off after approximately two minutes of playback; recurrence reported 22 March 2025 after second visit
- Simulated provider responses: evidence request 24 March 2025; conditional replacement proposal 27 March 2025
- Fictional case reference: SIM-CASE-2601

## Documents and intended ResolveAI categories

| Filename | Intended upload category | Expected workflow test |
|---|---|---|
| `01_synthetic_purchase_invoice.pdf` | Purchase invoice / proof of purchase | Extract purchase date, INR amount, retailer, customer and model. |
| `02_synthetic_warranty_certificate.pdf` | Warranty / coverage document | Extract coverage dates and recognize terms as illustrative only. |
| `03_first_repair_job_sheet.pdf` | Repair record | Extract first reported fault, inspection, repair, outcome and reference. |
| `04_second_repair_job_sheet.pdf` | Repair record | Link the same fault to a later, different repair and note reported recurrence. |
| `05_customer_service_email_thread.pdf` | Customer correspondence | Order timestamps, identify recurrence acknowledgement, and connect references. |
| `06_simulated_provider_evidence_request.pdf` | Provider response | Detect the request for the second job sheet and identify it as simulated. |
| `07_simulated_provider_resolution_offer.pdf` | Provider response | Extract conditional replacement proposal, unresolved conditions and avoid asserting legal entitlement. |

## Expected end-to-end workflow

ResolveAI should extract consistent customer, product/model, purchase and repair facts; connect both repair visits to the reported recurring fault; distinguish the customer's recurrence report from verified findings; recognize that the warranty wording and provider messages are simulated; identify the requested second job sheet; process the later conditional replacement proposal; surface unresolved details; and recommend seeking a clear written resolution proposal without asserting a legal entitlement.

The files are kept in this fixture directory only. They are not uploaded into ResolveAI and no production database, user evidence, or application code is modified.
