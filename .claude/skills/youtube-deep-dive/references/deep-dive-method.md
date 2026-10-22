# Deep-dive method

## The contract

After one read, the reader should be able to explain the idea to someone else. That is the test. Not "the video was covered." Not "it sounds authoritative." Transfer.

The video is a source of evidence and a point of view. The essay is your explanation of the idea underneath it. If the video disappeared, the essay should still stand.

## 1. The first-principles ladder

Answer these six questions before drafting. In order.

1. **What is the smallest observable fact?** A latency number, a failed request, a bill, a user action, a physical limit. Start where the reader can see something.
2. **What are the primitives?** The nouns and verbs that cannot be reduced further in this domain: a request, a key, a queue, a token, a weight, a constraint, a cost.
3. **What constraints and invariants hold?** Memory is finite. Requests arrive concurrently. Data changes. Time only moves forward. Money is conserved. Name the rules the system cannot escape.
4. **What is the causal chain?** Because A, B happens; therefore C; which means D. Write it as a chain, not a list. If two steps are really one, merge them.
5. **What would break it?** Find the edge case, the cost, the failure mode, the regime where the idea stops working. This is where understanding is tested.
6. **What follows?** The portable mental model, the design rule, or the question the reader should ask next.

If you cannot answer 2-4 without jargon, you are not ready to draft.

### Worked example: caching

- Observable: the same expensive request happens again and again.
- Primitives: a request, a key, a stored result, a freshness rule, a cost.
- Constraints: storage is finite; the underlying data changes; concurrent readers arrive.
- Chain: a hit skips the work; a miss pays for the work plus the lookup; invalidation decides whether the saved result is still true.
- Breaks: hot keys, stale reads, thundering herds on expiry, and caches that hide a broken source of truth.
- Follows: cache the expensive, pure part of the work, not the whole request; make freshness a product decision.

That chain is the essay. The video only supplies the specific system, numbers, and war stories.

## 2. The layman translation protocol

Use this sequence for every hard concept:

1. Name the abstraction in plain words.
2. Ground it in a physical analogy the reader already knows.
3. Map the parts explicitly: "the shelf is the index, the book is the row."
4. Say where the analogy stops. Every analogy leaks.
5. Introduce the technical term only after the reader has the shape.
6. Use the term consistently from then on.
7. Test it with one concrete number or case.

Weak: "The scheduler uses a work-stealing deque."

Better: "Imagine a shared to-do pile. Each worker also keeps a small private stack. When a worker runs out, it steals from the bottom of someone else's stack. That is a work-stealing deque: private on one end, shared on the other. The analogy stops at contention, because real deques use atomics, not politeness."

Then use "work-stealing deque" for the rest of the piece.

### Language rules

- Define before use. Expand every acronym on first use unless it is universal in the intended audience.
- Prefer verbs to nominalizations: "the scheduler decides" not "decision-making is performed."
- One new concept per paragraph. Two is a stall.
- Prefer concrete nouns and real numbers to adjectives.
- Average sentence length under 30 words. Vary the rhythm; a short sentence after a long one is a tool.
- If you cannot draw it, you do not understand it yet.
- An analogy must be load-bearing. If removing it changes nothing, remove it.
- Say "I" when the judgment is yours. Say "the speaker argues" when it is theirs.

## 3. Structure and word budget

| Movement | Job | Words |
| --- | --- | --- |
| Cold open | A scene, number, failure, or question. No preamble. | 150-250 |
| The question | Why this is hard, and why the obvious answer fails. | 200-300 |
| Primitives | Strip the idea to its parts and constraints. | 400-600 |
| Mechanism | The causal chain, step by step, with a figure or example. | 600-900 |
| Evidence | The number, demo, or case that makes it credible. | 300-500 |
| Limits | Where it breaks, what it costs, when not to use it. | 300-400 |
| Carry away | A portable model, not a recap. | 150-250 |

Total: 2,000-3,000 words. Five to seven H2 sections. Use H3 only when a mechanism has genuinely separate stages.

### Openings that work

- A concrete failure: "At 3 a.m. the queue was empty and the database was not."
- A number that does not add up: "The service used 4% of the CPU and 90% of the budget."
- A question a smart beginner would ask: "Why does adding a cache sometimes make the system slower?"
- A before/after contrast: "The old job took six hours. The new one takes six minutes, and the difference is not the language."
- A small experiment the reader can picture.

Never open with "In this video," "Today we're going to," or "X is a fascinating topic."

## 4. Paragraph moves

Use these to keep the explanation moving:

- **Claim → mechanism → consequence → example.** The workhorse.
- **Naive model → failure → better model.** Good for correcting intuition.
- **Concrete → abstraction → term → back to concrete.** Good for definitions.
- **"The tempting explanation is X. It fails when Y. The better explanation is Z."**
- **"That sounds like a detail. It decides whether the system survives Tuesday."**

A paragraph should end on a consequence or a question, not a restatement. If a paragraph only says "this is important," cut it.

## 5. Figures

- Place a figure after the paragraph that creates the question it answers.
- One idea per figure. If it needs three sentences to explain, it is two figures or none.
- The caption says what to notice: "Fig. 2 — the second write lands before the first ack. [08:14]"
- Do not use a figure as decoration or as proof of effort.

## 6. Accuracy and attribution

- Distinguish what the speaker argues from what the evidence shows.
- Verify names, numbers, units, and product versions. ASR mangles all four.
- Quote sparingly and verbatim. Never invent a quote.
- If a claim is load-bearing and unverifiable, hedge or leave it out.
- End with a source line: title, channel, URL, and the date you watched it.
- Timestamp every video still in its caption.

## 7. Edit pass

Do this after the draft cools, not while writing.

- Cut 15%. Start with the first sentence of each section.
- Every pronoun has an antecedent. Every "this" points at one thing.
- Every claim has a mechanism or evidence.
- Every term is defined before use.
- Every analogy is mapped and bounded.
- Read aloud; fix the places where you run out of breath.
- Headings are claims, not labels. "Why the cache lies" beats "Caching."
- The last paragraph gives the reader something to carry, not a summary of the video.
- Check the piece against the video: no invented detail, no reversed causality.

## 8. Banned phrases

Do not use: delve, tapestry, testament to, game-changer, in today's fast-paced world, it's not just X it's Y, more than just, at the end of the day, in conclusion, in summary, buckle up, let's unpack, let's dive in, this changes everything, the future of work.

Also avoid: three-item lists in every paragraph, em-dash pileups, "not only ... but also," and rhetorical questions stacked three deep.

## 9. Before and after

Transcript: "So the scheduler basically batches requests to improve throughput."

Weak: "The scheduler batches requests to improve throughput."

Strong: "A scheduler has one lever: it can trade latency for utilization. Batching is that trade made explicit. Hold a request for 5 ms and you can fill a batch of 64; the CPU stops idling between tiny jobs, and every caller pays the 5 ms. The gain is real only while the queue is deep enough to fill the batch. At low traffic, the same policy adds latency and buys nothing."

The strong version defines the lever, gives the mechanism, quantifies it, and names the regime where it fails. That is the standard.
