# A.S.I.A — Agent Safety & Integrity Assessment

A Vietnamese benchmark and reference design for customer-support agents that
must cite, refuse, and never act without confirmation.

## Benchmark

**Configuration under test**:
One pairing of an architecture and a pinned model that the benchmark scores.
_Avoid_: system, setup, agent

**Turn**:
One customer message handled end to end by an architecture, producing one
reply with its intent, sentiment, citations, tool events, and any pending
action.
_Avoid_: request, exchange, chat handling

**Architecture**:
The way authority is divided between the model and the application in a
configuration under test.
_Avoid_: pipeline, framework

**Reference System**:
The least-authority architecture in which the application owns routing,
evidence, citations, and every write, and the model may only propose.
_Avoid_: A.S.I.A agent, safe agent

**Baseline Agent**:
The comparison architecture in which the model calls tools directly, including
write tools, guarded only by instructions. It exists only inside evaluation.
_Avoid_: naive agent, strawman, vanilla agent

**Attack Case**:
A benchmark case written to make a configuration under test violate an
invariant.
_Avoid_: jailbreak, adversarial prompt, red-team prompt

**Violation**:
An observed breach of an invariant by a configuration under test on one case.
_Avoid_: failure, unsafe output

**Attack Corpus**:
Poisoned variants of policy documents that exist only for evaluation and never
join the trusted policy corpus.
_Avoid_: poisoned docs, malicious knowledge base

## Support domain

**Trusted Policy Corpus**:
The allowlisted policy documents that are the only permitted backing for a
policy claim.
_Avoid_: knowledge base, docs, KB

**Evidence Unit**:
One section of the trusted policy corpus that can back, and be cited for, a
policy claim.
_Avoid_: chunk, passage, snippet

**Citation**:
Provenance for a policy claim that the application builds from an evidence
unit, never from model output.
_Avoid_: source, reference

**Insufficient Context**:
The response that declines a policy claim because no evidence unit supports it.
_Avoid_: fallback, "I don't know" answer

**Demo Customer**:
The single fixed synthetic customer who owns the demo orders.
_Avoid_: user, account

**Pending Action**:
A proposed write that waits for an explicit confirmation before anything
happens.
_Avoid_: draft ticket, queued action

**Confirmation**:
The explicit, separate user decision that executes or cancels one pending
action, exactly once.
_Avoid_: approval, accept

**Invariant**:
One of the ten non-negotiable safety rules every configuration is judged
against.
_Avoid_: rule, policy, guideline
