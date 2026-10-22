+++
title = 'You did not remove the coupling; you moved it out of sight'
date = 2026-10-22
description = 'Decoupling does not delete dependencies; it moves them into agreements that are invisible at design time and billable at runtime. In serverless cloud systems, automation code holds the application together — treat it as application code.'
tags = ['Architecture', 'Event-driven', 'Distributed systems']
source_url = 'https://www.youtube.com/watch?v=w9a7eI6BlVc'
source_title = 'I Made Everything Loosely Coupled. Does My App Fall Apart?'
source_channel = 'GOTO Conferences'
source_kind = 'video'
+++

Picture a system with every direct call between its services cut. No service imports another's client, no interface is shared, and no request waits synchronously on a reply. An order still turns into a payment, and a payment still moves a balance, so something invisible is doing the connecting. That something is a set of agreements: the name of the channel an order is dropped into, the meaning of the message that carries it, the order in which two systems are allowed to hear about the world. Cut every line and the dependency does not disappear; it changes shape, and it changes address. That relocation — out of the call graph and into names, messages, and timing — is what this essay follows.

## Five buzzwords, one decision

Loosely coupled, event-driven, microservices, cloud, serverless: five buzzwords that sound like five technologies and hide one decision. That is where Gregor Hohpe starts. He has spent a career wiring large enterprises together — he co-wrote *Enterprise Integration Patterns*, the reference integration teams keep within arm's reach — and his keynote asks what buyers are actually purchasing with those words. Not a product, he argues: a placement. Each buzzword is a claim about where the dependencies will sit, who must know about whom, and whose change forces whose.

He makes the point by borrowing a line that he credits on a slide to David Orchard, formerly of BEA (a middleware vendor later absorbed by Oracle):

> “How do you make two systems loosely coupled? Don’t connect them.”

The line is funny because it is honest. Two systems that never connect are, trivially, loosely coupled; they are also useless to each other. The moment the two must cooperate, coupling exists, and the only remaining decision is where it sits. Everything else in the five buzzwords follows from there. A message queue does not delete the dependency between an order service and a payment service; it gives the dependency a new name, a new place to live, and a new set of things that can go wrong with it. Hohpe's title is the fear that follows the migration — everyone made the app loosely coupled, so does it fall apart? His answer, as I read the talk, is that it was always held together by something, and loose coupling only changed what the something is.

## Coupling is a dial, not a switch

A slide early in the talk offers the definition worth keeping: “Coupling is a measure of independent variability between connected systems.” Two systems are coupled to the degree that one cannot change without forcing a change in the other. That is a matter of degree, not of kind — hence the dial. A model Hohpe borrows on a slide — Vladik Khononov's, from *Balancing Coupling in Software Design* — breaks the measure into three axes. **Strength** is how hard one side's change forces change on the other. **Distance** is how far a change must travel through the system before it stops forcing more changes. **Volatility** is how often the coupled thing changes at all. Strength is cheap across stable boundaries and ruinous across volatile ones, which is why the same design decision can be wise in a billing core and reckless in a pricing experiment.

Then he cuts across the axes with a second distinction: design time versus runtime. A compile-time reference is the loud kind of coupling — touch the interface and the build breaks, and the build tells you where. An agreement living in a channel name, a message schema, or an ordering rule is the quiet kind: nothing validates it at design time, so the first proof of a disagreement is production traffic. His heuristic says which you can afford at each end of the wire: “The appropriate level of (design-time) coupling depends on the level of control you have over the endpoints.” Own both ends and you can draw the joint tight, because change on one side can be scheduled with change on the other. Couple to a system whose roadmap you do not control and tightness becomes a negotiation scheduled by someone else's release calendar. Either way the coupling is paid; loosening the joint only moves the payment to a different ledger.

## The wiring is the architecture, not the boxes

None of this is visible in the artifact most people hand over as architecture: the boxes. Hohpe draws the same four components twice. On the left they sit in a chain, each talking only to its neighbour. On the right the same four form a mesh, every component reaching every other directly. The boxes did not change between the two drawings; everything about the systems did. The chain has replaceability and single points of failure: swap one box in the middle and you renegotiate with everything behind it. The mesh has short paths and resilience: kill a node and traffic walks around it, but every component must now know about more of the others. Same boxes, opposite machines. The only variable is the wiring, which is exactly the part the boxes hide.

The figure below keeps the components identical and rewrites only their connections.

{{< figure src="fig-01.jpg" alt="Architecture slide showing the same four components wired in a chain on the left and in a mesh on the right." caption="Fig. 1 — Boxes identical, characteristics opposite: replaceability and single points of failure on the left, short paths and resilience on the right. [10:24]" >}}

One drawn line hides more than it shows. The frame below is a slide that isolates a single arrow between two systems and rings it with the questions the arrow leaves unanswered.

{{< figure src="fig-02.jpg" alt="Slide titled Connecting two systems: a single arrow from A to B surrounded by a ring of practical questions." caption="Fig. 2 — A single line implies a contract: sync or async, data or control flow, partial failure, retries, idempotency, back-off. [15:20]" >}}

Does the message travel synchronously or asynchronously? Is what crosses the line data, or a request that someone act? Which side waits when the other is down? Who retries, and is the retry harmless when it arrives twice? What happens to the payment in flight when the processor reboots mid-transaction? Not one of those questions can be answered by looking at the line, and every one of them is answered somewhere — in code the diagram does not contain. As he tells it, a team he met some two weeks before the keynote had documentation showing a clean, direct line between two services; the dependency that mattered lived elsewhere, in code nobody had drawn, and rerouting it cost the team sizable rework. The boxes were true. The wiring was not. The wiring is what changes when the requirements change.

## Decoupling moves the agreement, it does not delete it

The first place the relocated coupling shows up is in the names of the channels. Hohpe's slide walks through an order-entry system reaching a payment processor across four different channel names. Name the channel after the destination and the sender must know exactly who will fulfil the request; learning the receiver's identity means learning the receiver's interface, and replacing the receiver changes the sender. Name it after the command and the sender couples only to its own intent, while some other part decides who acts. Name it after the entity and the message is about a subject rather than a verb, which outlives process changes better than either. Name it after the event and the sender announces only that something happened, leaving everyone downstream to work out whether the announcement matters to them. The naming ladder — destination, command, entity, event — loosens the sender and tightens the receiver at every rung: the burden of knowing does not disappear, it crosses the wire. And the diagram still shows one arrow.

The diagram below is that ladder.

{{< figure src="fig-03.jpg" alt="Slide titled Message Channel Semantics: an order entry component reaching a payment processor through four differently named channels." caption="Fig. 3 — The naming ladder — destination, command, entity, event — shifts the burden of knowing from sender to receiver. [32:00]" >}}

The rungs are choices, not virtues. Destination naming reads naturally and dies in reorganizations. Event naming survives them and hides its cost in debugging, because relevance is no longer visible at the call site. Picking the rung is picking which kind of foreknowledge the system stores, and where a future engineer will go looking for it.

The second place the relocation shows up is in what people mean by event-driven. The figure below separates event-based, event-driven, and event-sourced systems, using an address change as the running example.

{{< figure src="fig-04.jpg" alt="Slide titled Event-based, Event-driven or Event-sourced, contrasting event notification with event-carried state transfer on an address-change example." caption="Fig. 4 — Notification couples the consumer to the producer's API; state transfer duplicates the data and accepts drift. [36:24]" >}}

In the notification style — **event notification** — the event says only that the address changed. A consumer that needs the new address must turn around and fetch it, which is why the style that Martin Fowler later named — **passive-aggressive events**, in the article this slide cites — earns its adjective: the announcement is polite, and the follow-up call is not optional. In **event-carried state transfer** the event carries the whole record, so consumers keep their own copy, stop calling back, and trade the round trip for a database that will drift. Hohpe's contrast is precise: notification couples the consumer to the producer's interface and bills a lookup at runtime; state transfer removes the lookup and couples the consumer to the producer's schema, then accepts the copy going stale. Neither style removes the coupling between the address system and everyone who cares about addresses. One moves it into an interface, the other into a schema.

## The bill is paid at runtime, when something fails

Whatever agreements the diagram does not show, production will exercise first. Hohpe spends the talk's later chapters on what happens when a quiet agreement is wrong, and the pictures turn from whiteboard to console. AWS (Amazon Web Services) EventBridge is a rule engine: a rule watches an event bus for a pattern and routes matches to targets, and one perfectly legal pattern is the class of events the rule itself emits. The screenshot below is the platform vendor's own documentation, warning about the loop that creates.

{{< figure src="fig-05.jpg" alt="Amazon Web Services EventBridge documentation warning that a rule responding to events it generates can loop indefinitely." caption="Fig. 5 — A rule reacting to the change it causes re-fires itself until a budget alert stops the bleeding. [40:08]" >}}

The rule fires, and its work writes back an event of the kind it watches, so it fires again, and again, forever. No component forbids the loop; every part does exactly what it was configured to do. The check that finally stops it is the bill — the account's budget alert is the only circuit breaker in the picture. That is the shape of runtime coupling: design-time mistakes surface in tools and cost a diff; runtime mistakes cost per message, per retry, per replay, and are found the expensive way. The mistakes also multiply rather than add. A rule that re-fires on its own output, joined to a consumer that retries on failure, turns a one-percent error rate into a standing invoice with no deadline. Loose runtime coupling is not the absence of structure. It is structure whose violations are enforced by the general ledger instead of the compiler.

## In the cloud, the wiring is code

If runtime coupling bills by the message, then the software that wires the messages becomes the most consequential code in the system. That is the keynote's closing move. In a serverless composition — his example uses CDK (Cloud Development Kit), an infrastructure-as-code tool for AWS — the code itself creates a channel named `mortgageQuotesBus`, stands up a bank service configured with `BANK_ID: 'PawnShop'`, `BASE_RATE: '5'`, `MIN_CREDIT_SCORE: '400'`, and binds the bank to that channel, so the two find each other by agreement rather than by address.

The code in the next figure is that composition, one screenful of it.

{{< figure src="fig-06.jpg" alt="Slide of Cloud Development Kit code that creates a queue named mortgageQuotesBus, configures a bank with base rate and credit score settings, and binds it to the queue." caption="Fig. 6 — Configuration and composition are both executable; the coupling is written down where readers can see it. [45:09]" >}}

Two kinds of decision sit in that screenful. The configuration — a bank identifier, a base rate, a floor on credit scores — is business policy expressed as code. The composition — which channel exists, who publishes to it, who consumes — is the architecture expressed as code. For the first time in the talk, both are written down in a form a reader can open, review, diff, and test, instead of living in the tribal memory of whoever set the system up. This is the quiet good news inside the keynote: composition in the cloud did not get looser, it got legible.

His slide's verdict is blunter than mine:

> Automation code holds your app together.

That sentence deserves to be read optimistically. If automation holds the application together, then the agreements no longer have to be invisible. They live in a repository, where they can carry review comments the way application code does. The coupling did not get deleted when the wiring moved to composition code; it acquired an address you can put in version control.

## What actually holds it together

Take the talk apart and three agreements remain, none of them drawn as boxes. Names: which channels exist and who listens on what. Meanings: which fields mean what in a message, and what a consumer owes a producer when they disagree. Sequencing: which statement of fact may follow which, and what a system does when reality refuses to arrive in the planned order. Loose coupling removes none of these agreements. What it removes is the compiler's help in checking them — and that removal is precisely the trade being sold.

So the practical conclusions are narrow and cheap. Read the wiring before the boxes; every channel name is a contract, and contract review at design time is the cheapest hour you will spend. Match the tightness of each joint to the control you have over its two ends, and loosen exactly there, not everywhere. Watch the runtime ledger the way you watch the build, because loops, retries, and replays are the failures a box diagram cannot show. And treat the code that wires services as what it is — automation code that holds the application together — because it will be read: by whoever pays the next bill, if not by you.

Decoupling, done honestly, is not the removal of dependency. It is the authorship of it. You drew fewer lines on the diagram and signed the same number of agreements; that is the work. The dependencies did not go away. They went out of sight — so go and look at them where they live.

---

Source: [“I Made Everything Loosely Coupled. Does My App Fall Apart?”](https://www.youtube.com/watch?v=w9a7eI6BlVc) by Gregor Hohpe, keynote at GOTO (the conference organiser) EDA (event-driven architecture) Day 2022 in London, 48 min. Watched 22 October 2026. Figures are stills from the video at the timestamps in their captions.
