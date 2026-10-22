ResolveAI   Project Description

An agentic consumer resolution workflow that turns scattered information into structured next steps.


Inspiration
A faulty product is often only the beginning of a frustrating experience.
Users may have to collect receipts, organise repair records, explain the same problem repeatedly, figure out what information is missing, prepare follow ups, and keep track of what happens next. These tasks are scattered across documents, conversations, and support interactions.
We wanted to explore a different approach: what if a consumer complaint could be managed as an evolving workflow instead of a series of disconnected conversations?
That idea became ResolveAI.


What It Does?

ResolveAI is an agentic consumer resolution prototype that helps users organise a complaint, examine available evidence, identify missing information, prepare proposed actions, and track a case as new responses arrive.
Rather than stopping at a generated answer, ResolveAI demonstrates a workflow in which recommendations lead to proposed actions, actions require user review, and new information can trigger reassessment.
Key Capabilities
Structured case management: Create and maintain cases with their details, status, and activity history.
Evidence aware processing: Upload supporting documents, organise evidence, and filter irrelevant documents from the factual context used by the analysis workflow.
Recommendations and next steps: Examine the information available in a case, identify potential gaps, and prepare structured next steps using the prototype’s case analysis and policy reference mechanisms.
Human in the loop actions: Prepare actions for review, allow users to approve or reject them, and demonstrate the resulting workflow through simulated execution.
Response driven reassessment: Process simulated external responses, reassess the case, and demonstrate how its state and timeline can evolve.
Alexa+ style experience: Demonstrate the intended assistant interaction through a browser based simulation.


What Makes It Different?

A conventional chatbot can tell someone what they might do next. ResolveAI explores how an assistant can help organise and manage the process that follows.
The central idea is to treat a complaint as a persistent workflow with state, evidence, proposed actions, approval decisions, and follow up events.
This creates a demonstrable sequence:
	1	Create a consumer resolution case.
	2	Examine the available information and supporting evidence.
	3	Identify missing details and potential next steps.
	4	Prepare an action for the user to review.
	5	Approve or reject the proposed action.
	6	Demonstrate execution through a simulated external interaction.
	7	Process a simulated response and reassess the case.
	8	Reflect the updated state in the case timeline.
Human approval remains an explicit step. The prototype demonstrates agentic workflow orchestration without suggesting that every action is executed autonomously.


How We Built It
ResolveAI uses a React 19 and TypeScript frontend built with Vite, backed by a Python FastAPI application and SQLite persistence.
The application combines case management, evidence processing, policy reference retrieval, workflow state, action review, simulated external responses, and response driven reassessment.
AI assisted development tools supported implementation and debugging. The focus was on integrating the components into a coherent application workflow rather than presenting a standalone chatbot.
Technology
	•	React 19 and TypeScript — frontend and user interface.
	•	Vite — frontend development and build tooling.
	•	Python and FastAPI — backend API and application logic.
	•	SQLite — persistent application data.
	•	pytest — backend testing.
	•	AI assisted development tools — implementation and debugging support.


Transparency About the Prototype
ResolveAI is a working prototype, not a fully deployed consumer support platform.
External service centre interactions and action execution are simulated. The current analysis provider includes deterministic demonstration logic rather than verified live LLM inference. The Alexa+ style experience is demonstrated through a browser based simulation, not a claim of direct Alexa+ integration.
The prototype’s policy references and evidence processing safeguards also have limitations. Document relevance does not prove authenticity, and retrieved guidance should be independently verified.
We believe clearly communicating these boundaries is important when demonstrating agentic systems that could eventually influence real world decisions.
Potential Impact
ResolveAI explores a more organised way to handle consumer complaints: one that keeps relevant information together, makes next steps easier to understand, and helps users follow a process rather than repeatedly starting over.
With verified external integrations, stronger privacy protections, and further reliability testing, this approach could be extended to additional consumer support workflows.
For this prototype, the goal is to demonstrate the underlying workflow and explore how an assistant can move beyond answering a question to helping a user manage what happens next.


What’s Next?
Future work could include verified integrations with external support systems, stronger document processing capabilities, improved privacy controls, and a supported production assistant integration.
For now, ResolveAI demonstrates the core concept: a consumer resolution workflow that connects evidence, recommendations, human approved actions, and follow up into one persistent case.
