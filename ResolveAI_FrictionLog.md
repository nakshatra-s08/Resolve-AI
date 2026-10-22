ResolveAI — Development Friction Log

Purpose

This log documents friction encountered while implementing and verifying ResolveAI, a consumer resolution prototype developed for the Amazon Developer Hackathon.
Each entry describes the observed issue, its impact, the workaround or resolution, and a concrete improvement that could help future developers.
The log distinguishes confirmed development issues from limitations that still require additional investigation.



FR 01 — Repository Context and Project Discovery

Category: AI assisted development and repository navigation  Severity: Medium  Status: Resolved through repository discovery

Task attempted
Continue development of the existing ResolveAI application and integrate its conversational assistant with the existing backend.

Expected behaviour
The development assistant should identify the correct project directory, inspect the relevant source files, and reuse the existing application architecture.

Actual behaviour
The initial workspace search did not locate the ResolveAI source code. It found a document describing the project while other unrelated projects were present in the workspace.
A subsequent inspection located the actual application under:
Desktop/Projects/Amazon Handling Agentic Workflow
The repository contained the existing FastAPI backend, React frontend, SQLite database, assistant panel, and action management components.

Impact
The initial search created uncertainty about whether the application source was available and introduced the risk of unnecessarily scaffolding a second application.

Workaround
The project directory was located explicitly, and subsequent work was redirected to the existing repository.

Suggested improvement
Repository aware coding assistants should prioritise identifying the active project root, inspecting version control metadata, and checking common source directories before concluding that an application is missing.
They should also distinguish between a genuinely absent codebase and a workspace search that has not yet found the relevant directory.



FR 02 — Test Configuration Errors

Category: Python testing and development tooling  Severity: Medium  Status: Resolved

Task attempted
Run the ResolveAI backend test suite to verify application behaviour.

Expected behaviour
The test runner should load the project’s test configuration and execute the tests.

Actual behaviour
The test configuration contained a syntax error in a sys.path.append statement and an incorrect return type annotation for the db_session fixture.
These issues were identified and corrected before the successful test run.

Impact
The test configuration needed repair before the test suite could provide useful verification results.

Workaround
The affected lines in backend/tests/conftest.py were corrected, and the test suite was run again.
Verification result
The subsequent reported backend test run completed with:
	•	102 tests passed.
	•	Zero failures.
	•	16 warnings.

Suggested improvement
Coding assistants could improve the development experience by running a lightweight syntax and test collection check immediately after editing test configuration files.
They should also validate generated fixture definitions and import paths before reporting implementation work as complete.



FR 03 — Distinguishing Code Integration from End to End Verification

Category: Testing and AI assisted development  Severity: Medium  Status: Partially addressed

Task attempted
Verify that the existing assistant panel was connected to the case management, action management, and simulated response workflows.

Expected behaviour
A development review should establish not only that components and callbacks exist, but also that the complete workflow functions correctly in the running application.

Actual behaviour
Repository inspection identified the assistant panel, API client functions, action management components, and relevant backend endpoints.
The backend test suite passed, and the frontend production build succeeded. However, the final verification environment did not provide a browser automation tool, so the complete workflow could not be independently verified through automated browser interaction.

Impact
Compilation and backend tests provided useful evidence, but they did not establish that every assistant interaction behaved correctly in the browser.

Workaround
A manual browser testing checklist was prepared to cover analysis, messaging, action drafting, approval or rejection, simulated response processing, reassessment, and persistence after refresh.

Suggested improvement
Development environments should make browser automation easier to configure and provide a reliable way to interact with the locally running application.
Coding assistants should explicitly distinguish between source code inspection, automated tests, successful builds, and actual browser level verification.



FR 04 — Frontend Build Success Does Not Guarantee Correct User Interactions

Category: Frontend testing  Severity: Low to Medium  Status: Documented

Task attempted
Verify the frontend after integrating the existing assistant functionality.

Expected behaviour
The build process should establish that the frontend compiles, while interaction tests should establish that user actions work correctly.

Actual behaviour
The production build completed successfully, and the lint command reported zero errors and two warnings.
However, a successful build alone cannot establish that the assistant handles every interaction correctly or that backend state updates are consistently reflected in the UI.

Impact
Additional manual verification was necessary before the application could be considered ready for a live demonstration.

Workaround
The project was given a manual end to end test plan covering the main assistant workflow.

Suggested improvement
Frontend tooling could provide clearer, integrated support for interaction tests, browser console monitoring, API failure simulation, and assertions about persisted application state.



FR 05 — Framework and Dependency Deprecation Warnings

Category: Dependency maintenance  Severity: Low  Status: Outstanding maintenance item

Task attempted
Run the complete backend test suite.

Expected behaviour
The test run should complete without failures and ideally without warnings caused by obsolete interfaces.

Actual behaviour
The successful backend run reported 16 warnings. The visible warning summary included deprecations involving Starlette’s TestClient dependency setup, an asyncio event loop policy, and an HTTP 422 status code constant.

Impact
The warnings did not prevent the tests from passing, but they indicate that some interfaces may require updates as dependencies evolve.

Workaround
The warnings were documented rather than addressed through potentially unnecessary dependency changes immediately before the submission deadline.

Suggested improvement
Framework and testing documentation could provide clearer migration guidance and recommended compatible dependency combinations.
Projects would also benefit from a straightforward way to distinguish actionable deprecations from warnings that can safely be addressed in later maintenance.



FR 06 — Repeated Action Generation During Manual Testing

Category: User interaction and workflow verification  Severity: Low  Status: Context identified; no confirmed defect

Task attempted
Exercise the action generation workflow while reviewing the case timeline.

Expected behaviour
The interface should make it clear when an action is being prepared and should help users distinguish between drafting, approval, and execution.

Actual behaviour
During manual exploration, the action generation control was clicked multiple times, and the timeline displayed repeated execution related entries.
The repeated clicks provide a possible explanation, but they do not by themselves establish whether the entries were correct or whether the backend handled repeated requests safely.

Impact
Repeated entries made the timeline harder to interpret and created uncertainty about whether the same action had been processed more than once.

Workaround
A clean demonstration should use a fresh synthetic case and deliberate, single step interactions. If the behaviour recurs, the persisted records and execution logic should be inspected.

Suggested improvement
Interfaces could disable action controls while requests are processing, communicate action state more clearly, and prevent accidental duplicate submissions where appropriate.
Backend operations should also handle repeated requests safely.
This entry records an observation, not a confirmed backend defect.



FR 07 — Access to Restricted Alexa+ Developer Tools

Category: Platform access and developer onboarding  Severity: Medium  Status: Worked around through the permitted simulated experience route

Task attempted
Determine whether ResolveAI could connect directly to Alexa+ through an API key or developer integration.

Expected behaviour
Developers would benefit from clear, accessible instructions explaining how to determine which integration mechanisms are available and what credentials or permissions they require.

Actual behaviour
The hackathon organisers’ guidance indicated that the restricted Alexa+ developer tools were not available to participants and that a simulated experience approach was permitted.
As a result, a direct Alexa+ integration was not implemented.

Impact
The project needed to distinguish between building an assistant experience and establishing a real connection to the Alexa+ platform.

Workaround
ResolveAI uses a browser based assistant experience that demonstrates case analysis, proposed actions, user approval, simulated external interactions, and workflow reassessment.
The simulation is clearly distinguished from a direct Alexa+ integration.

Suggested improvement
Developer onboarding would benefit from an easily discoverable capability matrix explaining:
	•	Which platform APIs and SDKs are publicly available.
	•	Which capabilities require restricted access.
	•	Which simulation approaches are permitted.
	•	How a prototype could progress to a supported production integration.



Summary
The main friction encountered while developing ResolveAI involved locating the correct repository, correcting test configuration, distinguishing automated verification from browser level testing, and determining the appropriate approach for demonstrating an Alexa+ style experience.
The project ultimately reported 102 passing backend tests, a successful frontend production build, and zero frontend lint errors.
Browser level verification remained a manual task because the available development environment did not provide a browser automation tool.
These experiences highlight the value of repository aware development assistance, reliable automated testing, accessible browser automation, clear platform access documentation, and explicit communication about what has actually been verified.
