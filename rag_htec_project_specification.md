## Assignment Introduction 

Companies today gain significant value from AI tools that accelerate work, automate tedious tasks, and improve quality. However, these tools differ widely in maturity and business models, creating risks such as data leakage, weak security, and compliance failures. 

HTEC’s verification team must carefully assess these risks before approving any tool for company-wide use. Currently, verifying a single tool can take several days. The process involves checking several important typical risks across a set of legal and compliance documents. Because these documents are not standardized in naming or structure, reviewers must search through long texts to find answers to questions like: “Is the AI model used in this tool trained on our company data?” or “If yes, which type of license allows turning that off, ideally in the admin console so users cannot enable it accidentally?” 

An advanced semantic search AI chatbot can help solve this challenge and greatly accelerate the verification process. 

The goal of this assignment is to create and implement a full end-to-end solution for: 

*   Generating synthetic datasets simulating real-world software legal and compliance documentation.
*   Ingesting and indexing this data to enable semantic retrieval.
*   Building a chatbot that uses RAG to answer user questions about the data, such as those typically asked during the verification process.
*   Evaluating the system using standard metrics and comparing performance across configurations.

Imagine this solution as an assistance tool for software whitelisting teams in their approval decisions. 

The assignment is structured into multiple phases. This means you will be able to incrementally build the solution.

---

## Phase 1: Data Generation 

In this phase, you will focus on creating synthetic data that simulates real-world software terms and privacy policies. This data will serve as the foundation for testing and validating your parsing algorithms and supporting later phases including RAG implementation and report generation. 

### Technical Requirements 

**Data Scope**
*   Generate 20 documents total across 5 software tools (4 documents per tool). 
*   Document types to choose from: 
    *   Privacy Policy 
    *   Terms of Service 
    *   Data Processing Agreement 
    *   Service Level Agreement 
    *   Security Whitepaper 
    *   Compliance & Certifications 

**Output Structure**
Each tool has its own folder containing all generated documents.

```text
/data/
├── tool1/
│   ├── toc_privacy_policy.json
│   ├── privacy_policy.html
│   ├── toc_terms_of_service.json
│   ├── terms_of_service.html
│   ├── ...
├── tool2/
│   ├── ...
└── ...
```

*   **TOC files:** Must contain the table of contents in JSON format. 
*   **Validation:** Implement programmatic HTML parsing/validation to ensure all files are well-formed. 

**Multi-Step Generation Process**
1.  **Tool Ideation Step** 
    *   Automatically generate a short description of each tool (name, purpose, category, and typical user base).
    *   Randomly decide which document types to generate for each tool.
    *   Use these as persistent contexts for all its document generations.
2.  **Step 1 - Table of Contents Generation** 
    *   Use a reasoning-capable LLM to create a structured TOC for each document type.
    *   Enforce the use of the LLM JSON output feature.
    *   Store the resulting JSON formatted TOC inside a standalone JSON file (`toc_*.json`).
3.  **Step 2 - Section Generation** 
    *   Use a cost-effective model to generate document content section by section.
    *   Provide prior context (tool description + generated sections so far) to maintain coherence and logical flow.

**Model Configuration**
*   Use at least two different models: one for TOC generation, one for section generation.
*   Choose models based on price/performance trade-off.
*   Adjust temperature and/or `top_p` to ensure variety across tools and document types.

**Data Quality Issues**
Each document must intentionally include 2-3 issues such as: 
*   Contradictory or conflicting clauses.
*   Ambiguous or vague language.
*   Minor typos or formatting errors.
*   Inconsistent terminology or cross-references.

### Deliverables 
*   20 validated HTML documents organized by tool folder.
*   20 corresponding TOC JSON files.
*   Generation script/console application with reproducible outputs (must be configurable for all the parameters - models, temperature, number of tools, document types etc.).
*   Basic validation logic for HTML and JSON integrity.

### Additional Notes: Common Pitfalls to Avoid

**General**
*   Don’t embed prompts as long inline strings, move them into separate YAML or other configuration files.
*   Avoid overly basic system and user prompts, they should be detailed enough to drive high-quality, nuanced generation.
*   Generate the tool ideas as part of the script, or at least use tools which do not exist so the LLM has no prior knowledge.
*   Don’t ignore the temperature parameter, it must be used and configurable.
*   If LLM calls fail, do not use hard-coded fallbacks, hard-coded values are not allowed.
*   Avoid code that looks entirely generated by a copilot, the final submission should reflect your own engineering decisions, coding style, and deep understanding of the problem.
*   Enforce the generated JSON schema using the chat completions API’s structured model outputs feature.

**ToC Generation**
*   Don’t hard-code and restrict the ToC for 2 levels, it should represent realistic, deeper structures for some cases.
*   Don’t store the JSON ToC output as a raw string, it must be a valid JSON object so the files are valid JSON.

**Section Generation**
*   Avoid generating very short documents, use real-life SLAs (e.g., https://openai.com/policies/services-agreement/) as a reference for length and depth.
*   During section generation, the model must always generate HTML, fallbacks to non-HTML are not acceptable. Individual sections can be partial structures (e.g., a `<div>`), but the assembled document must be valid HTML.
*   For each section generation, always provide the generated sections so far for the current document. You can add it in the system prompt so the model receives complete context and can continue the document naturally.
*   Ensure the required data quality issues (contradictions, ambiguity, minor typos, etc.) are actually present. One technique is to ask the LLM for a JSON output with one property for the generated section and another listing the issues applied.
*   Don’t generate entire documents in one go per document type, generate documents by sections within each document type to achieve realistic length and structure.

---

## Phase 2: Chatbot Interface 

In this phase, you will design and implement an interactive conversational interface powered by an LLM. The objective is learning message handling, context preservation, and the stateless nature of the LLM API. 

This phase is independent of Phase 1. The chatbot you built here is a new and separate application, not an extension of the data generator from the previous phase. 

The chatbot will act as a lightweight assistant capable of maintaining a defined conversational tone, handling natural language queries, and executing simple tool calls. 

Later on in the assignment, this will be the assistant that helps users interact with the generated data. 

The chatbot is expected to be implemented as a console application to avoid unnecessary effort on building additional user interfaces. This approach keeps the focus on core LLM interaction and functionality. Each run of the program represents a single conversation - there is no need to store sessions or support multiple concurrent sessions within the same application. You may choose to create a more advanced interface if you wish, but that is not the primary goal. 

### Technical Requirements 

**Core Functionality**
*   Build a console application chatbot that enables interactive conversations with the LLM.
*   The chatbot should: 
    *   Maintain a consistent personality and tone throughout all responses.
    *   Handle system, user, and assistant message roles correctly.
    *   Support context persistence within a conversation (maintain in-memory message history).
    *   Demonstrate how an otherwise stateless API can simulate stateful conversation behavior.

**Tool Calls**
Implement at least two simple "tool" functions to demonstrate how the LLM can interact with external logic: 
*   **Get Current Date** - returns the current system date. 
*   **Add Days to Date** - accepts a date and a number of days (positive or negative), returning the resulting date. 

*Example Interaction (doesn't have to be word-by-word like this, don't use this as an example in the prompts):*
```text
$ user> Hey, what's the date today?
assistant> Today is October 17, 2025.

$ user> What will be the date after 2335 days?
assistant> March 9, 2032.

$ user> Sorry, I meant 2935.
assistant> October 30, 2033.
```

**Tone and Personality**
*   The assistant should exhibit a consistent conversational tone throughout the session.
*   You may freely choose the personality (e.g., professional, friendly mentor, giggle master etc.), but it must remain stable across all responses.

**Conversation Management**
*   Store the message history in an in-memory data structure.
*   This should allow users to request a summary of the conversation at any point by asking for it.

### Deliverables 
*   Functional command line application chat interface with: 
    *   Configurable for all the parameters (e.g.: model, temperature, tools enabled, prompts).
    *   Correct use of message roles and simulated state handling.
    *   Consistent tone and style across all responses.
    *   Support for tool calling and natural dialogue continuity.
    *   Proper summarization of conversation history.

---

## Phase 3: Data Ingestion & Semantic Search 

Goal is to persist the Phase 1 HTML documents into a vector store and provide a command line application for semantic retrieval over structure-aware chunks. With this, you will implement the Retrieval part of the RAG pattern. 

This phase is expected to be implemented as a console application. It doesn’t need to include any conversational features. Instead, it should provide a simple interface for testing retrieval functionality - allowing the user to enter a query and receive a structured output containing the most relevant results and metadata. The focus of this phase is on retrieval logic and data handling, not on user interface design. 

### Technical Requirements 

**Ingestion (Indexing)**
*   **Input:** The HTML documents produced in Phase 1.
*   **Parsing & Chunking:** 
    *   Parse HTML and extract sectioned text while preserving document structure (headings, paragraphs, etc.).
    *   Chunk content with a structure-aware approach (keep sections together where possible).
*   **Embeddings:** 
    *   Use the provided embedding model (configurable) to create vectors for each chunk.
*   **Persistence:** 
    *   Store vectors and enough metadata to reconstruct results (e.g., tool name, document type, source doc and section label, chunk order).
    *   Must persist to disk so the index can be loaded on startup without re-indexing.

**Retrieval (Search)**
*   **Query Flow:** 
    *   Accepts a free-text query.
    *   Create a query embedding with the same model used for ingestion.
    *   Perform vector similarity search and return top-K matches (configurable).
*   **Context Expansion:** 
    *   Parameter to include neighbor chunks for additional context around each hit.
*   **Output:** 
    *   For each result, display: a relevance score, the chunk (and neighbors if configured), and basic source info (tool name, document type, document URL and section heading).

### Deliverables 
*   Ingestion that parses HTML, chunks with structure awareness, embeds, and persists the index (with configurable embedding model and chunking parameters).
*   Search command line application that embeds a query, returns top-K results, and supports neighbour expansion (with configurable embedding model, top-K, and neighbour behaviour).

---

## Phase 4: Agentic RAG Assistant 

In this phase, you will extend the chatbot developed in Phase 2 by integrating the retrieval functionality from Phase 3 as a callable tool. The assistant should be able to decide when to use retrieval based on user intent and combine the retrieved information with its conversational reasoning to provide grounded, evidence-based responses. This phase brings together the previous components into a complete retrieval-augmented generation (RAG) system. 

### Technical Requirements 
*   Extend the Phase 2 chatbot to include the retrieval functionality from Phase 3 as a callable tool.
*   The assistant should autonomously decide whether to use retrieval based on user intent.
*   When needed, it should: 
    *   Call the retrieval tool with appropriate arguments (e.g., tool name, query).
    *   Integrate the retrieved information into its reasoning.
    *   Produce grounded responses supported by retrieved evidence.
    *   Always cite sources when referencing retrieved content.
    *   Citations must include direct quotes from the retrieved document(s) and clear source details (such as file name or link and section title). Summaries without concrete quotes and source references are not sufficient.
*   When retrieval is not needed, it should respond naturally without querying the index.

**Tool Integration**
*   Add a Retrieval Tool to the chatbot: 
    *   Exposes an interface for searching over the Phase 3 index.
    *   Accepts input parameters such as query, top-K results, and optional filters.
    *   Returns text chunks and metadata about their source (e.g., tool name, document type, section).
*   The retrieval call should be invoked only when it's necessary, not automatically for every message.

**Conversation Orchestration**
*   The chatbot should: 
    *   Maintain conversation history and context from previous turns.
    *   Use the retrieved information together with the conversation context when generating responses.
    *   Allow for follow-up questions that build on prior answers and retrieved info, possibly triggering new retrievals.
    *   Clearly communicate when it references external knowledge.
*   To handle context length limitations of the LLM, implement a summarization strategy: 
    *   When the conversation grows too long (approaching 60-70% of the maximum input tokens), summarize earlier exchanges using a separate, lightweight LLM call.
    *   Store this condensed summary in the system message.
    *   Retain only the last 2-3 user/assistant messages in full in the context, alongside the running summary.
    *   This ensures the model remains aware of prior context without exceeding its token limits.

### Deliverables 
*   Updated chatbot implementation with: 
    *   Integrated retrieval as a tool callable by the assistant.
    *   Configurable model and retrieval parameters.
    *   Support for grounded answers combining conversation and retrieved context (proper source citation for all referenced content).
    *   Context management with summarization to handle long conversations.

---

## Phase 5: Evaluation & Quality Metrics 

In this final phase, you will evaluate the performance and quality of the RAG assistant built in Phase 4. The goal is to implement proper evaluation logic, apply standard evaluation frameworks, and perform experiments to compare configurations and understand trade-offs in your design choices. 

### Technical Requirements 

**Evaluation Objectives**
Evaluate your RAG assistant using both retrieval metrics and answer quality metrics. 

*Retrieval Metrics:*
*   Contextual Precision 
*   Contextual Recall 
*   Context Utilization 

*Answer Quality Metrics:*
*   Answer Relevancy 
*   Faithfulness 
*   Answer Correctness 

**Implementation Requirement for Evaluation**
You must expose your RAG assistant so that it is callable from your evaluation script. This can be a function, command line application with arguments, an HTTP endpoint, or any other programmatic interface. The evaluation script must be able to: 
*   Pass in configuration parameters such as model, temperature, or top-K.
*   Receive all required evaluation data in a structured format, including: 
    *   Retrieved chunks with metadata.
    *   The generated answer.

**Evaluation Workflow**
1.  **Choose an Evaluation Framework** 
    *   You don't need to re-implement the metrics, you can integrate a chosen framework into your workflow (e.g., DeepEval or TruLens).
2.  **Create a Validated Golden Dataset** 
    *   Build a reference (golden) dataset containing user queries and their corresponding manually created and validated reference answers.
    *   You may use generator tools from your chosen framework, but the final references must be validated before use.
    *   The dataset should be stored in the structure required by the framework.
3.  **Run Experiments Across Configurations** 
    *   Evaluate your assistant under multiple configurations to explore how different configurations affect performance.
    *   Experiment with: 
        *   Different LLM models and parameters (e.g., smaller cost-efficient vs. larger reasoning-capable models, temperature, etc.).
        *   Retrieval parameters (e.g., top-K, neighbor expansion).
        *   Optionally: chunking strategies.
    *   Compare results using the chosen metrics to analyze trade-offs between accuracy, grounding quality, and efficiency.
    *   You don't need to achieve perfect scores; the goal is to demonstrate experimentation, measurement, and insight through empirical results.
4.  **Error Analysis and Impact Report** 
    *   Write a short summary (a few paragraphs) where you: 
        *   Compare the different configurations you tested and provide metric summaries for each one.
        *   Explain the main insights and trade-offs you observed across configurations, such as differences in accuracy, grounding quality, or efficiency.
        *   Identify where your system produced false positives (irrelevant chunks retrieved) and false negatives (important chunks missed).
        *   Describe how this retrieval issues influenced both your metrics and the final answer quality.
        *   Reflect on the potential real-world impact of these errors and trade-offs if the system were used in practice.
    *   *Note: Your write-up should reflect your own evaluation and analysis; don’t generate it with an LLM.*

### Deliverables 
*   RAG assistant exposed through a programmatic interface that your evaluation script can call and that returns structured evaluation data.
*   Validated golden dataset in the framework’s required structure.
*   Evaluation scripts or notebooks showing metric computation using a selected framework.
*   Evaluation summary that includes configuration comparisons, metric summaries, insights, and analysis of retrieval errors.

---

## Task Delivery
When you finish this final phase, please reach out to your Direct Manager, Project Tech Authority, or Delivery Authority to present your solution and receive validation.