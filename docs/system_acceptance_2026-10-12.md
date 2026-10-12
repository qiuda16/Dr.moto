# System acceptance: 2026-10-12

The system has not passed full acceptance and is not verified for production delivery.

Latest full backend run: 47 passed, 1 failed (AI shop context). The staff build passes.
The empty-shop context defect was subsequently fixed: keyword browsing works without
a vehicle model and does not label results as compatible recommendations. The remaining
failure now occurs in AI chat because the external AI service returns HTTP 502; the
Odoo integration harness does not provide that AI service. AI answers remain unverified.
The trial_core_build CI intentionally covers core contracts and staff compilation only;
it does not run real Odoo integration or the complete backend suite. A green result
must not be described as full system acceptance.

## Current evidence

- Cross-frontend browser write acceptance passed: submitted BrowserTrial1012 through the production website contact form, observed success and cleared inputs, logged into staff inbox, found the same new lead, clicked contacted and observed its persisted contacted state after reload. Both clients proxied real isolated BFF/PostgreSQL through SSH. Lead-to-order conversion and completing an order entirely through the UI remain outstanding.
- Removed outdated contact-page development copy claiming the form is frontend-only. Website production build passed after this edit.

- Dashboard summary/overview now include paid offline receipts in cumulative totals, today's receipts, recent payments and receipt-average calculation. A regression verifies store isolation, exclusion of void receipts and received-date filtering (3 trial tests passed). The existing day boundary remains UTC; receipt average is per receipt, not per completed order.
- Expanded real HTTP run passed for order c942ab82-0630-4014-9bad-08794c39c86c, including dashboard assertions: one 199.00 offline receipt increased total paid by exactly 199.00 despite a repeated request, summary and overview agree, and the recent receipt appears. Browser dashboard after this backend change has not been rechecked.

- Staff production-build browser run now connects to isolated BFF through scripts/serve_staff_acceptance.py. Playwright successfully logged in, displayed dashboard counts (9 orders, 7 completed), opened the trial inbox, loaded the real order list, and opened a completed order detail. Console error checks returned zero messages. This verifies authentication/navigation/read paths; creating and completing an order entirely through UI is still outstanding.
- Dashboard showed today's revenue as zero despite recorded offline payments. The cause and expected accounting scope remain unverified; offline-payment aggregation in business metrics needs investigation before claiming operational reporting accuracy.

- Staff routes now load views on demand rather than eagerly importing all eight pages. Production build passed (2.92 seconds), with entry JavaScript 12.57 kB and separate page chunks. A Playwright run against the production static build displayed the login page, reported zero console errors, and verified empty username/password validation. This static test did not proxy the BFF; actual browser authentication and staff operations remain unverified. The earlier Vite development-navigation timeout has not been retested in the same environment.

- Staff browser acceptance is not passed. Vite served the entry and /src/main.js with HTTP 200; /api/health through an SSH tunnel to isolated BFF also returned 200. Playwright navigation exceeded 60 seconds and snapshot exceeded 30 seconds. No login or staff workflow was verified in this attempt. Root cause remains undetermined (page loading versus browser runtime); API success does not prove frontend usability.

- Financial-detail acceptance passed for order 078070e7-c2cb-4e58-ad11-12dd551248de: customer history and detail both report the confirmed 199.00 quote; detail lines sum to 199.00 and payment summary reports paid 199.00. Previously history used Odoo's computed total although quote versions reside in BFF. Customer aggregation now uses the current active published/confirmed BFF quote when present, otherwise retains the Odoo amount. This does not synchronize accounting or order lines back into Odoo.
- Customer order detail previously queried drmoto.work.order.line.work_order_id, which does not exist in the actual module. The domain now uses order_id. The complete real HTTP run including customer detail passes; customer/trial regression suite also passes (9 tests).

- Complete expanded HTTP run passed for order 6553eef8-62b8-49d0-93f3-f5dff428ccc7: customer/vehicle, lead/inbox, diagnosis, selected service, published/confirmed quote, in_progress, completion health check, ready, offline payment, delivery checklist, done, customer binding, customer vehicle list and completed paid history (199.00). Real PostgreSQL and Odoo were used. WeChat identity used the development fallback; SMS ownership verification and WeChat device/UI behavior were not verified.
- This run exposed and fixed Odoo empty-string-field compatibility: empty VIN and engine_code arrive as false, which previously caused response validation errors and HTTP 500. Customer vehicle adapters now map these absent values to null. The expanded HTTP script passed after updating the isolated BFF.

- Expanded real HTTP acceptance passed: order c1560ec9-8ec7-4d75-a3ac-cf5d269db244 advanced through confirmed and diagnosing, saved the verified complaint, created/published/confirmed a 199.00 quote, rejected advancement to quoted without selected service items, then verified offline payment and retries. This proves quote and gate behavior, not successful construction or delivery; the test intentionally stops at the missing-service gate.

- Current BFF source is running in the isolated server stack, with real PostgreSQL and Odoo. Startup logs confirm migrations 0001 through 0016 applied successfully; /health returns db=ok and odoo=ok, env=dev. It uses the server's cached infra-bff image for dependencies and a read-only source mount, so a fresh reproducible image build is still outstanding.
- scripts/test_trial_http.py passed against localhost:28080 on the server. It verified customer/vehicle creation, website lead submission, staff inbox, conversion to an Odoo-backed work order, duplicate conversion rejection, offline payment recording, repeated payment idempotency and payment list amount. Test order: b6c29888-6195-4dc4-ac0c-06f7c8f7c422. Quote confirmation, construction, completion and customer mini-program history were not covered by this run.

- A real isolated stack now runs on the existing server under /home/ubuntu/drmoto_integration_20261012, Compose project drmoto-integration. PostgreSQL has its own integration_db volume; Odoo has its own integration_odoo volume and localhost port 18069. Existing production containers were not replaced.
- Server SSH credentials and noninteractive sudo Docker access were verified. Odoo initialization completed, /web/login returned HTTP 200, and a database query confirmed drmoto_mro is installed.
- Subsequent real Odoo run: all four previously failing customer/payment configuration checks passed (4 passed, 21 deselected). The BFF runs locally with a fresh SQLite database, connected through SSH to isolated Odoo; this does not verify BFF PostgreSQL migrations or production HTTP deployment. Runner: scripts/run_odoo_integration.py. It creates test customers and orders only in the designated isolated Odoo. Never point it at production.
- Full suite using this tunnel and a fresh BFF SQLite database: 46 passed, 1 failed, in 8.70 seconds. Remaining failure: test_ai_ops_context_returns_shop_items_and_ai_answers_them. Some tests mock their dependencies even in this run; this count is not proof that all workflows used real Odoo.

- Full BFF suite before the appointment conversion fix: 41 passed, 5 failed.
- Four failures affect customer creation, customer summary and customer search. The test runtime cannot connect to Odoo at localhost:8069. These tests remain failed; they must be rerun with a working integration environment.
- One failure affects AI shop context: shop_items is empty despite inserted fixtures. Root cause remains unverified.
- Appointment conversion now rejects repeated conversion with HTTP 409. Focused trial and account safety suite: 5 passed. This covers sequential retries, not simultaneous requests or Odoo/BFF partial failures.
- Appointment conversion preserves requested time in Odoo date_planned and keeps source and complaint in the order description. Updated trial, customer, account and startup checks: 14 passed. Odoo calls in these tests are mocked; actual persistence still requires integration acceptance.
- Customer mini program builds with Node 20 after clean dependency installation. This proves compilation, not device behavior or production API connectivity.
- Website and staff builds previously passed. Browser workflow acceptance remains outstanding.

## Required mainline acceptance

1. Use a working isolated Odoo and BFF environment with the candidate migrations.
2. Create a customer and vehicle; log in and bind the customer mini program.
3. Submit a website lead and a customer appointment; verify both in the staff inbox.
4. Convert to a work order; verify customer, vehicle, complaint and requested time.
5. Publish and confirm a quote, record work, record offline payment and complete delivery.
6. Verify the same order status, amount, payment and history through the customer API and mini program.
7. Verify backups and recovery, then deploy the same version and repeat runtime acceptance.

No production acceptance is implied by mocked Odoo tests, successful compilation or a healthy old server.
