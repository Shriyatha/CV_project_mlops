# System Architecture Overview

The architecture of this system follows a modular design that efficiently handles audio transcription, compliance analysis, and sentiment detection, while maintaining scalability and robustness. It is built using the following key components:

•⁠  *⁠*FastAPI**: For high-performance backend API interactions.

•⁠  ⁠**Gradio**: To provide a user-friendly interface for interaction.

•⁠  ⁠**Logging Server**: To capture and monitor system events for debugging and analysis.

---
# Project Architecture

```mermaid
graph LR;
    A[User] -->|Requests| B[FastAPI Backend];
    B -->|Processes| C[Semantic Search Engine];
    C --> D[OpenCV for Image/Video Processing];
    C --> E[BLIP Model for Captioning];
    C --> F[Whoosh for Indexing and Search];
    A --> G[BentoML for Deployment];
    G --> |Processes| C[Semantic Search Engine];
```
---