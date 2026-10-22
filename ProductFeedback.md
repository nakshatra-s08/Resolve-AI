ResolveAI   Product Feedback

Project Overview
ResolveAI is a consumer resolution prototype developed to explore how an assistant can help users manage product complaints through a structured, evidence aware workflow.
The application combines a React and TypeScript frontend, a FastAPI backend, SQLite persistence, case analysis logic, document processing, action management, and simulated external service interactions.
AI assisted development tools were used to support implementation, debugging, and testing.



1. AI Assisted Development Tools

What we used them for
AI assisted development tools helped with:
	•	Exploring implementation approaches and application architecture.
	•	Building and integrating frontend and backend components.
	•	Debugging Python and TypeScript issues.
	•	Reviewing existing code and identifying missing connections.
	•	Generating and refining tests.
	•	Investigating errors reported by automated test runs.
	•	Improving documentation and preparing the project for demonstration.

What worked well
AI assisted development was particularly useful for accelerating implementation and helping connect existing application components.
For example, repository inspection helped identify that ResolveAI already contained an assistant panel, case management APIs, action management components, and simulated response workflows. This allowed development to focus on verifying and integrating existing functionality rather than unnecessarily rebuilding the application.
Automated test execution also provided a useful feedback loop. The backend test suite ultimately reported 102 passing tests, and the frontend production build completed successfully.

What could be improved
Generated code and automated reviews still require independent verification.
A component appearing to be connected does not establish that its workflow works correctly in the browser. Similarly, a successful production build does not prove that all user interactions behave as intended.
A more effective development experience would combine repository aware coding assistance with reliable browser automation, end to end workflow testing, and clearer evidence of which behaviours have actually been verified.

Would we use these tools again?
Yes. AI assisted development was useful for accelerating implementation and debugging. We would continue using these tools alongside conventional testing, code review, and manual verification rather than treating generated code or automated reports as proof of correctness.



2. React, TypeScript, and Vite

What worked well
The frontend stack supported a responsive, component based application. Vite provided a straightforward development and production build workflow, while TypeScript helped identify compile time issues.
The existing component structure also made it possible to integrate the assistant into the case details experience without creating a separate application.

What could be improved
A successful production build does not validate the complete user journey. More accessible browser automation, interaction level tests, and clearer frontend error reporting would make it easier to detect problems that compilation cannot catch.

Would we use it again?
Yes. The stack was suitable for a component based interface that communicates with a separate backend.



3. Python, FastAPI, and SQLite

What worked well
FastAPI provided a clear API layer for case management and workflow operations. SQLite supported persistent application state without requiring a separate database service during local development.
The existing backend also made it possible to test important workflows independently of the frontend.
The final reported backend test run completed with 102 passing tests and zero failures.

What could be improved
The testing process initially encountered syntax and fixture annotation problems in the test configuration. These issues had to be corrected before the suite could be run successfully.
The test suite also reported deprecation warnings involving dependencies and framework interfaces. These did not prevent the reported test run from passing, but they indicate areas that could benefit from maintenance.

Would we use it again?
Yes. This stack was appropriate for a local first prototype with structured APIs, persistent case data, and testable application logic.



4. Automated Testing and Build Tooling

What worked well
The backend test suite and frontend production build provided repeatable checks during development.
The final reported results were:
	•	Backend: 102 passed, zero failures.
	•	Frontend production build: successful.
	•	Frontend lint: zero errors and two warnings.
These checks provided evidence that the backend test suite passed and the frontend compiled successfully.

What could be improved
Automated unit and integration tests do not replace browser level testing.
The available development environment did not provide a browser automation tool for the final verification process. Consequently, the complete assistant workflow still required manual testing in the local application.
Improved support for automated browser interaction, console error collection, and end to end workflow assertions would make the development process more reliable.

Would we use it again?
Yes. Automated tests and production builds were valuable, but we would supplement them with browser automation wherever possible.



5. Amazon and Alexa+ Development Experience

ResolveAI demonstrates an assistant led consumer resolution workflow through a browser based simulation.
The demonstration includes case analysis, evidence context, action drafting, user approval, simulated execution, and response driven reassessment.
We did not implement a direct connection to the Alexa+ service, and we do not claim to have used restricted Alexa+ developer tools.

What worked well
The simulated experience approach allowed us to explore the intended assistant workflow using our existing application architecture and development tools.
It also allowed the project to demonstrate structured actions and persistent workflow state without requiring a live external service integration.

What could be improved
A more accessible development environment for experimenting with supported Alexa+ integrations would make it easier for developers to progress from a simulation to a real platform integration.
Clearer guidance on the boundary between a permitted simulated experience and a production integration would also help teams choose the appropriate implementation path.

Would we use the experience again?
We would continue exploring the simulated experience approach for prototyping assistant led workflows. A real Alexa+ integration would be a separate future step, subject to actual platform access and supported integration requirements.



Overall Feedback
The most valuable lesson from building ResolveAI was that a useful assistant experience requires more than conversational text.
The application needs persistent state, evidence handling, proposed actions, explicit approval, reliable workflow transitions, and a clear distinction between simulated and real world operations.
AI assisted development helped accelerate implementation, while automated testing helped verify parts of the system. More comprehensive browser automation would improve confidence in the complete user experience.
