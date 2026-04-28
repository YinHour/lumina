# Notebooks, Sources, and Notes - The Container Model

Open Notebook organizes research in three connected layers. Understanding this hierarchy is key to using the system effectively.

## The Three-Layer Structure

```
┌─────────────────────────────────────┐
│         NOTEBOOK (The Container)    │
│     "My AI Safety Research 2026"   │
├─────────────────────────────────────┤
│                                     │
│  SOURCES (The Raw Materials)        │
│  ├─ safety_paper.pdf                │
│  ├─ alignment_video.mp4             │
│  └─ prompt_injection_article.html   │
│                                     │
│  NOTES (The Processed Insights)     │
│  ├─ AI Summary (auto-generated)     │
│  ├─ Key Concepts (transformation)   │
│  ├─ My Research Notes (manual)      │
│  └─ Chat Insights (from conversation)
│                                     │
└─────────────────────────────────────┘
```

---

## 1. NOTEBOOKS - The Research Container

### What Is a Notebook?

A **notebook** is a *scoped container* for a research project or topic. It's your research workspace.

Think of it like a physical notebook: everything inside is about the same topic, shares the same context, and builds toward the same goals.

### What Goes In?

- **A description** — "This notebook collects research on X topic"
- **Sources** — The raw materials you add
- **Notes** — Your insights and outputs
- **Conversation history** — Your chats and questions

### Why This Matters

**Isolation**: Each notebook is completely separate. Sources in Notebook A never appear in Notebook B. This lets you:
- Keep different research topics completely isolated
- Reuse source names across notebooks without conflicts
- Control which AI context applies to which research

**Shared Context**: All sources and notes in a notebook inherit the notebook's context. If your notebook is titled "AI Safety 2026" with description "Focusing on alignment and interpretability," that context applies to all AI interactions within that notebook.

**Parallel Projects**: You can have 10 notebooks running simultaneously. Each one is its own isolated research environment.

### Example

```
Notebook: "Customer Research - Product Launch"
Description: "User interviews and feedback for Q1 2026 launch"

→ All sources added to this notebook are about customer feedback
→ All notes generated are in that context
→ When you chat, the AI knows you're analyzing product launch feedback
→ Different from your "Market Analysis - Competitors" notebook
```

---

## 2. SOURCES - The Raw Materials

### What Is a Source?

A **source** is a *single piece of input material* — the raw content you bring in. Sources never change; they're just processed and indexed.

### What Can Be a Source?

- **PDFs** — Research papers, reports, documents
- **Web links** — Articles, blog posts, web pages
- **Audio files** — Podcasts, interviews, lectures
- **Video files** — Tutorials, presentations, recordings
- **Plain text** — Notes, transcripts, passages
- **Uploaded text** — Paste content directly

### What Happens When You Add a Source?

```
1. EXTRACTION
   File/URL → Extract text and metadata
   (OCR for PDFs, web scraping for URLs, speech-to-text for audio)

2. CHUNKING
   Long text → Break into searchable chunks
   (Prevents "too much context" in single query)

3. EMBEDDING
   Each chunk → Generate semantic vector
   (Allows AI to find conceptually similar content)

4. STORAGE
   Chunks + vectors → Store in database
   (Ready for search and retrieval)
```

### Key Properties

**Immutable**: Once added, the source doesn't change. If you need a new version, add it as a new source.

**Indexed**: Sources are automatically indexed for search (both text and semantic).

**Scoped**: A source belongs to exactly one notebook.

**Referenceable**: Other sources and notes can reference this source by citation.

### Example

```
Source: "openai_charter.pdf"
Type: PDF document

What happens:
→ PDF is uploaded
→ Text is extracted (including images)
→ Text is split into 50 chunks (paragraphs, sections)
→ Each chunk gets an embedding vector
→ Now searchable by: "OpenAI's approach to safety"
```

---

## 3. NOTES - The Processed Insights

### What Is a Note?

A **note** is a *processed output* — something you created or AI created based on your sources. Notes are the "results" of your research work.

### Types of Notes

#### Manual Notes
You write them yourself. They're your original thinking, capturing:
- What you learned from sources
- Your analysis and interpretations
- Your next steps and questions

#### AI-Generated Notes
Created by applying AI processing to sources:
- **Transformations** — Structured extraction (main points, key concepts, methodology)
- **Chat Responses** — Answers you saved from conversations
- **Ask Results** — Comprehensive answers saved to your notebook

#### Captured Insights
Notes you explicitly saved from interactions:
- "Save this response as a note"
- "Save this transformation result"
- Convert any AI output into a permanent note

### What Can Notes Contain?

- **Text** — Your writing or AI-generated content
- **Citations** — References to specific sources
- **Metadata** — When created, how created (manual/AI), which sources influenced it
- **Tags** — Your categorization (optional but useful)

### Why Notes Matter

**Knowledge Accumulation**: Notes become your actual knowledge base. They're what you take away from the research.

**Searchable**: Notes are searchable along with sources. "Find everything about X" includes your notes, not just sources.

**Citable**: Notes can cite sources, creating an audit trail of where insights came from.

**Shareable**: Notes are your outputs. You can share them, publish them, or build on them in other projects.

---

## How They Connect: The Data Flow

```
YOU
 │
 ├─→ Create Notebook ("AI Research")
 │
 ├─→ Add Sources (papers, articles, videos)
 │    └─→ System: Extract, embed, index
 │
 ├─→ Search Sources (text or semantic)
 │    └─→ System: Find relevant chunks
 │
 ├─→ Apply Transformations (extract insights)
 │    └─→ Creates Notes
 │
 ├─→ Chat with Sources (explore with context control)
 │    ├─→ Can save responses as Notes
 │    └─→ Notes include citations
 │
 ├─→ Ask Questions (automated comprehensive search)
 │    ├─→ Can save results as Notes
 │    └─→ Notes include citations
 │
 └─→ Generate Podcast (transform notebook into audio)
     └─→ Uses all sources + notes for content
```

---

## Key Design Decisions

### 1. One Notebook Per Source (Ownership)

Each source has exactly one **owner** (the user who uploaded it) and an **owning notebook** (the notebook it was originally added to). However, sources can now be **shared** across notebooks via references:
- A source can be added to multiple notebooks (it appears in each notebook's context)
- The original owns it, but other notebooks can reference and use it
- Deleting a source from a notebook only removes the reference — the source still exists in its owning notebook

### 2. Public / Private Visibility

Notebooks and sources have a **visibility** setting: `private` (default) or `public`.

**One-way toggle:** Visibility can only change from `private` → `public`. Once public, it cannot be made private again. This prevents accidental exposure and ensures public content stays public.

**Summary:**

| Visibility | Who Can See It |
|-----------|----------------|
| `private` | Only the owner |
| `public`  | Everyone (with or without login) |

**Public content** is browsable on a dedicated public page. Unauthenticated users can view public notebooks, sources, and their associated content.

**Deletion constraint:** A public source that is referenced by notebooks **cannot** be deleted until all notebooks unlink it. This prevents breaking public-facing content that others may rely on. Attempting to delete a referenced public source returns a 409 Conflict.

### 3. Immutable Sources, Mutable Notes

Sources never change (once added, always the same). But notes can be edited or deleted. Why?
- Sources are evidence → evidence shouldn't be altered
- Notes are your thinking → thinking evolves as you learn

### 4. Explicit Context Control

Sources don't automatically go to AI. You decide which sources are "in context" for each interaction:
- Chat: You manually select which sources to include
- Ask: System automatically figures out which sources to search
- Transformations: You choose which sources to transform

This is different from systems that always send everything to AI.

---

## Mental Models Explained

### Notebook as Boundaries
Think of a notebook like a Git repository:
- Everything in it is about the same topic
- You can clone/fork it (copy to new project)
- It has clear entry/exit points
- You know exactly what's included

### Sources as Evidence
Think of sources like exhibits in a legal case:
- Once filed, they don't change
- They can be cited and referenced
- They're the ground truth for what you're basing claims on
- Multiple sources can be cross-referenced

### Notes as Synthesis
Think of notes like your case brief:
- You write them based on evidence
- They're your interpretation
- You can cite which evidence supports each claim
- They're what you actually share or act on

---

## Common Questions

### Can I move a source to a different notebook?
You can **add** a source to multiple notebooks via references. The source keeps its owning notebook, but all notebooks it's added to can use it. To stop using it in a notebook, simply remove the reference.

### Can a note reference sources from a different notebook?
Yes, if the source is shared into the notebook. Notes can reference any source that is linked (via reference) to their notebook.

### What if I want to group sources within a notebook?
Use tags. You can tag sources ("primary research," "background," "methodology") and filter by tags.

### Can I merge two notebooks?
Not built-in, but you can manually copy sources from one notebook to another by re-uploading them.

### Can anyone see my content?
Only if you explicitly make it public. By default, all notebooks and sources are **private** — only you can see them. Making content public is a deliberate, one-way action.

### Can I delete a public source?
Only if it's not referenced by any notebook. If notebooks are still using the source, you must first remove it from those notebooks (or ask the notebook owners to do so). This protects content that others may depend on.

---

## Summary

| Concept | Purpose | Lifecycle | Scope | Visibility |
|---------|---------|-----------|-------|------------|
| **Notebook** | Container + context | Create once, configure | All its sources + notes | private (default) or public |
| **Source** | Raw material | Add → Process → Store → Share | Owning notebook + referenced notebooks | private (default) or public |
| **Note** | Processed output | Create/capture → Edit → Share | One notebook | Inherits notebook visibility |

This three-layer model gives you:
- **Clear organization** (everything scoped to projects)
- **Privacy control** (private by default, explicit public sharing)
- **Audit trails** (notes cite sources)
- **Flexibility** (notes can be manual or AI-generated)
- **Safe sharing** (public content is protected from accidental deletion)
