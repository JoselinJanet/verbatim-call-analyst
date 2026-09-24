# Demo Questions — Verbatim Call Analyst
## Covering All System Behaviours

> Use this during your live demo to systematically demonstrate every feature and edge case.
> Type these into the **Ask Chat** tab unless noted otherwise.

---

## 🗂️ PRE-DEMO: Guide Answers Matrix (No typing needed)

**What to show:** Load the Matrix tab and say:

> *"Before I type anything, notice the matrix is already populated from the pipeline run.
> Every cell shows a status — Answered, Partial, or Not Discussed.
> Let me click one cell to show a quote."*

**Suggested cell to click:** Q2 (Barriers) × France
- Quote will show: *"The biggest issue is still capital budget approval..."*

**Then click Citation Drilldown** → show the surrounding context (interviewer question visible before the quote).

> *"The question asked is visible above the answer — so you can see this quote was not taken out of context."*

---

## ✅ CASE 1 — Well-covered research question (expect: cited quotes from multiple experts)

**Type in Ask Chat:**
```
What are the main barriers to robotic surgery adoption in Europe?
```

**What happens:**
- BM25 retrieves relevant sentences from all 3 transcripts
- LLM selects sentence IDs referencing capital cost, training, utilisation
- Returns cited quotes from France (Dr. Martin), Germany (Anna Keller), UK (Dr. Carter)

**What to say:**
> *"Notice: the system doesn't just answer — it cites the exact sentence, the expert name, turn ID, and timestamp. These are verbatim from the transcript files. The model never wrote these words."*

---

## ✅ CASE 2 — Single-expert specific question (expect: quote from one expert only)

**Type in Ask Chat:**
```
What did the German expert say about procurement criteria?
```

**What happens:**
- BM25 retrieves Germany-relevant sentences
- Returns Anna Keller's quote: *"We look at total cost of ownership, expected procedure volume, maintenance, service contracts and training requirements..."*

**What to say:**
> *"Even a single-expert question is answered with a direct citation — not a paraphrase, not a summary. The exact sentence from the file."*

---

## ✅ CASE 3 — Cross-market comparison question (expect: multiple experts compared)

**Type in Ask Chat:**
```
How do France and the UK differ in how they weigh economics versus clinical outcomes?
```

**What happens:**
- France: Dr. Martin — *"Clinical outcomes are necessary, but they are not enough on their own. If two systems offer similar outcomes, the hospital will look hard at economics and utilisation."*
- UK: Dr. Carter — *"I would not say finance alone decides the purchase."* / economics and clinical strategy are balanced

**What to say:**
> *"This is a cross-market question. The system pulls verified quotes from both experts so you can compare their actual words — not a paraphrased interpretation."*

---

## ✅ CASE 4 — Future outlook question (expect: all three experts, disagreement visible)

**Type in Ask Chat:**
```
What growth do experts expect in robotic surgery procedures over the next 3 to 5 years?
```

**What happens:**
- France: *"15 to 20 percent more procedures annually in some of the stronger centres"*
- Germany: *"closer to high single digits or low double digits... rather than something like 20 percent"*
- UK: *"procedure growth above 15 percent annually in some areas"*

**What to say:**
> *"Now look at this — France and UK are more optimistic, Germany is more conservative. This difference also appears in the Disagreements tab as a typed disagreement. Let me switch there now."*

**→ Switch to Disagreements tab** to show the system already caught this as an "Emphasis" disagreement.

---

## ❌ CASE 5 — Question with NO coverage (expect: refusal, not fabrication)

**Type in Ask Chat:**
```
What do experts think about robotic surgery adoption in the United States?
```

**What happens:**
- BM25 scores are all below threshold (transcripts only cover FR, DE, UK)
- System returns: *"Not covered in these calls"* — does NOT fabricate

**What to say:**
> *"This is the most important behaviour to demonstrate. The question is reasonable — but the transcripts don't cover the US market. The system refuses to answer rather than making something up. That refusal is the hallucination firewall working."*

---

## ❌ CASE 6 — Off-topic question (expect: refusal)

**Type in Ask Chat:**
```
What is the market size of the global AI industry?
```

**What happens:**
- BM25 retrieves nothing relevant
- Returns: *"Not covered in these calls"*

**What to say:**
> *"Completely outside the transcript content — and the system knows it. No hallucination, no confident wrong answer."*

---

## 💬 CASE 7 — General chat / small talk (expect: conversational reply, no citations)

**Type in Ask Chat:**
```
Hello, can you briefly explain what this tool does?
```

**What happens:**
- System detects it as a general/conversational message
- Responds naturally without forcing transcript citations

**What to say:**
> *"The system has two modes: research mode — which cites everything — and general conversation mode, which handles greetings and meta questions naturally. The routing is automatic."*

---

## 💬 CASE 8 — Context-aware follow-up (expect: resolves "he/she" from prior context)

**After Case 1 or Case 2, type:**
```
What else did she say about training?
```

**What happens:**
- System resolves "she" from prior message context (Dr. Carter or Anna Keller depending on prior question)
- Returns training-related quotes from that expert

**What to say:**
> *"The chat remembers the last few messages. 'She' is resolved from context — the system knows which expert was just discussed."*

---

## 🗂️ BONUS: Themes Tab

**What to show:**
- Click the Themes tab
- Point to one theme (e.g., "Economics as the primary decision driver")
- Show the verified quotes supporting it from multiple experts

**What to say:**
> *"These themes were identified by the LLM — but every theme is backed only by quotes that were already verified in the answer grid. The model cannot invent a theme from raw transcript text."*

---

## 🗂️ BONUS: Disagreements Tab

**What to show:**
- Click Disagreements tab
- Find the Growth Outlook disagreement (France/UK vs Germany on procedure growth %)
- Show it is typed as "Emphasis" — both sides agree growth will happen, but disagree on magnitude

**What to say:**
> *"The disagreement type matters. This isn't a contradiction — both experts agree growth will happen. The system correctly types it as an Emphasis difference, not a Contradiction."*

---

## 🎯 Demo Flow Summary

| Order | What to Show | Case Covered |
|---|---|---|
| 1 | Matrix tab + click a cell | Pre-built analysis |
| 2 | Citation Drilldown | Context preservation |
| 3 | Ask: barriers question | Multi-expert citation |
| 4 | Ask: Germany procurement | Single-expert citation |
| 5 | Ask: France vs UK economics | Cross-market comparison |
| 6 | Ask: growth outlook | Disagreement visible |
| 7 | Switch to Disagreements tab | Typed disagreement |
| 8 | Ask: US market question | Refusal (no hallucination) |
| 9 | Ask: off-topic question | Refusal (no hallucination) |
| 10 | Ask: "Hello, what does this do?" | General chat mode |
| 11 | Ask: "What else did she say?" | Context-aware follow-up |
| 12 | Themes tab | Synthesis from verified data |
