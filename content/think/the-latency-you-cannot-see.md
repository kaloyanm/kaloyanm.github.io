+++
title = 'The requests your latency graph deleted'
date = 2026-10-22
description = 'A service can report a perfect p99.9 while users wait seconds. Closed-loop measurement deletes the requests that would have arrived during a stall, and the fix starts with asking who was supposed to be in line.'
tags = ['Performance', 'Observability', 'Distributed systems']
source_url = 'https://www.youtube.com/watch?v=lJ8ydIuPFeU'
source_title = 'How NOT to Measure Latency'
source_channel = 'Strange Loop Conference'
source_kind = 'video'
+++

The benchmark reported ten thousand requests at one millisecond and one at a hundred seconds. Its four-nines line (99.99%) was perfect: every request but one had finished in about a millisecond. The system had, in fact, been frozen for a full hundred seconds.

The contradiction is not a rounding error. It is what a measurement looks like when it deletes its own worst evidence. While the system was frozen, the load generator was waiting for a response, so it never issued the requests that would have arrived. The requests that would have been slow were never born. The graph recorded the one request that was in flight, then went back to reporting a healthy service.

Latency is not a property of a program. It is a property of a population of requests, and the number you report depends on which requests you let into the population. Most tools sample the requests the system was healthy enough to accept. That is a biased sample, and the bias has a name: **coordinated omission**. The cost is simple: the dashboard stays green while the queue grows, and the fix gets aimed at the work instead of the wait.

## A latency number describes a crowd

One request has a duration. A running system has a distribution. Serve a million requests in an hour and you do not have one latency; you have a million. The job of measurement is to describe how that million behaved. The mean, the median, the 99th percentile, and the maximum are four different summaries of the same crowd, and they answer different questions.

Three terms keep getting mixed together. **Service time** is the interval between a worker starting the work and finishing it. **Response time** is the interval between the caller wanting the answer and receiving it, including every wait in between. **Latency** is a general word for elapsed time, useful only after you say which clock is running.

The coffee shop makes the difference physical. The barista takes thirty seconds to make a drink: that is service time. The customer at the back of the line waits twelve minutes: that is response time. The barista did not get slower. The line did.

Every queue in a computer is that line. A run queue, a lock, a database connection pool, a socket buffer, a scheduler waiting for a CPU: each one can hold a request without doing any work on it. The timer that starts when the work starts cannot see any of them.

A constraint sits underneath all of this: a queue forms when arrivals outpace service, and the amount of work in the system is the arrival rate multiplied by the time each request spends there. At 100,000 requests per second and 10 milliseconds per request, 1,000 requests are in flight at any instant. If the service rate is lower than the arrival rate, the difference does not evaporate. It joins the line, and the line grows. The arithmetic is simple; the visibility is not.

## The dashboard shows only the good side

Sort a million samples from fastest to slowest. The 99th percentile, often written p99, is the value at the 99% mark: 99% of requests were at least that fast, and 1% were slower. It is a position in the crowd, not an average. The average is the sum divided by the count, and a hundred-second stall can move it while leaving almost every individual request untouched.

The chart below is a two-hour monitoring view. It plots the 25th, 50th, 75th, 90th, and 95th percentiles. The worst 5% of requests are not on the chart at all. When the 95th percentile spikes, the chart is telling you that the worst 5% got bad enough to drag the boundary upward. It is not telling you how bad they got.

{{< figure src="fig-01.jpg" alt="A dark monitoring dashboard with five percentile lines; the 95th spikes to about 490 milliseconds and an annotation reads 95% lie." caption="Fig. 1 — The chart plots everything except the worst 5% of requests. The spike is the only hint of what is missing. [05:28]" >}}

Averaging percentiles makes the problem worse. The average of the 95th percentile over two hours is not the 95th percentile of those two hours. There is no arithmetic that turns per-interval positions into a position for the whole interval. Gil Tene's example is fifteen one-minute maxima averaged to 42. The number 42 describes no request that ever happened, and neither does an “average p95” on a dashboard. You can average durations. You cannot average positions in a sorted list.

Then there is the scale question. A page view is not one request. Tene counted the HTTP requests generated by a single click and found that most pages produce dozens. Take a modest page: five clicks per session, forty resources per click, two hundred requests. If each request independently has a 1% chance of landing in the worst 1%, the chance that at least one of the two hundred does is `1 − 0.99^200`, about 87%. The 99th percentile is not rare for the user. It is the common case for the page.

The 95th percentile is stranger. The chance that all two hundred requests beat it is `0.95^200`, about 0.000035. So roughly 0.003% of page views never see anything worse than p95; the other 99.997% do. The median is the limiting case: `0.5^200` is about one in a trillion trillion trillion trillion trillion. Essentially every page view sees something worse than the median. A metric that describes the typical request describes no user's experience.

These calculations assume independent requests with the same distribution, which is not true. Real traffic is correlated, and real pages differ in size. The direction is what matters: more requests per page makes the tail more likely to be experienced, not less. When a service fans out to a hundred dependencies and reports a p99 for each, the chance that a user avoids every p99 is `0.99^100`, about 37%. Most users meet a tail somewhere.

## A stall can delete its own witnesses

Here is the experiment that makes coordinated omission visible. A service handles 100 requests per second, one millisecond each. Every 200 seconds it freezes for 100 seconds. No work happens during the freeze.

An honest description would count the requests that arrive while it is frozen. In the first 100 seconds, 10,000 requests finish in a millisecond. In the next 100 seconds, another 10,000 arrive, one every 10 milliseconds. They cannot be served until the freeze ends. A request that arrives at the start waits 100 seconds; one that arrives at the end waits almost nothing; the average is 50 seconds. Across the full 200 seconds, the average is 25 seconds. The 99.99th percentile is about 100 seconds. This is a bad system, and the numbers say so.

Now measure it the way a closed-loop load generator does. The generator sends one request, waits for the response, then sends the next. During the freeze, it is waiting, not issuing. It records ten thousand one-millisecond samples and one 100-second sample. The average is 10.9 milliseconds. The 50th, 75th, and 99.99th percentiles all read one millisecond. The tool is not lying about the samples it has. It is lying about the samples it does not have. The chart below is what it recorded.

{{< figure src="fig-02.jpg" alt="A chart labelled Measurement in practice: ten thousand measurements at one millisecond, one measurement at one hundred seconds, and an overall average of 10.9 milliseconds." caption="Fig. 2 — The freeze is visible as a single hundred-second sample. The ten thousand requests that would have arrived during it are absent. [19:55]" >}}

The chart below shows the same 200 seconds with every intended request counted. The black band is the stall. Every point in it is a request that arrived while the system was frozen, and every one of them waited. The 75th percentile moves from one millisecond to fifty seconds; the 99.99th moves to about a hundred seconds.

{{< figure src="fig-03.jpg" alt="The same run with the missing requests counted: a solid black band of samples fills the hundred-second stall, with the 75th percentile at 50 seconds and the 99.99th near 100 seconds." caption="Fig. 3 — The same 200 seconds with the missing requests counted. The black band is the stall; the 75th percentile moves from 1 ms to 50 seconds. [20:48]" >}}

The missing ten thousand are not a random sample. They are missing precisely because the system was bad. The generator coordinated with the stall: it backed off, stopped issuing, and therefore stopped observing. The bad period removed the sampler.

The same pattern appears inside a service. Start a timer, do the work, stop the timer. If the process freezes between two requests, every request waiting behind the freeze begins its timer after the freeze ends. Each one measures a fast service time. The one request that was in flight carries the stall, or the stall falls entirely outside the timed window and disappears. This is how a service gets a beautiful internal latency graph and a line out the door.

Tene calls the second pattern “cheating twice.” A rate-limited generator notices it is behind and replays the backlog as fast as it can. The requests that should have been slow are replaced by requests issued after the stall, which are fast. The measured distribution is now better than the one that merely dropped the samples.

The consequence is definitional. What the closed-loop tool measured was service time, not response time. The timer began when the work began. The queue, the wait, and the thing the caller experienced were outside the window. A dashboard full of those numbers is a dashboard of the barista's hands, with the line cropped out.

Tene's sharpest demonstration is that the error has no stable sign. Take the bad system and improve it: instead of freezing for 100 seconds, it answers every request in 5 milliseconds. The measured four-nines line moves from one millisecond to five milliseconds. By the metric, the improvement is a fivefold regression. A metric that calls a fix worse than the bug cannot guide a fix.

## The work did not get slower; the line did

The coffee shop returns, photographed. The barista's service time is the same whether the line is two people or twenty. The customer's response time is not.

{{< figure src="fig-04.jpg" alt="A photo of a coffee shop with a barista at the counter and a long line of customers; arrows point to the barista and to the customer at the back." caption="Fig. 4 — Service time is the barista's hands. Response time is the customer at the back of the line. [23:52]" >}}

Tene measured the same split on Cassandra. At 2,000 operations per second, response time and service time almost coincide, because nobody is waiting. Raise the load and the curves separate. At 90,000 operations per second, service time stays in the low hundreds of milliseconds while response time climbs to about 7.5 seconds. The database is doing the work at roughly the same speed. The requests are spending their time in line.

The ceiling in that run was about 87,000 operations per second. Push 90,000 and 3,000 requests per second join the queue. After 250 seconds, the wait is about eight seconds and still growing. Above the ceiling, response time grows linearly with time, because the backlog grows linearly. Below the ceiling, it reaches a plateau. The chart below shows the same system at 90K/s and 80K/s.

{{< figure src="fig-05.jpg" alt="Four charts comparing 90K and 80K operations per second; at 90K the maximum response time climbs in a straight line to eight seconds, while at 80K it oscillates around 150 milliseconds." caption="Fig. 5 — At 90K/s the maximum climbs in a straight line; at 80K/s it stays near 150 ms. The left-hand system is accumulating a queue, not slowing down. [25:59]" >}}

The useful number is not the maximum throughput. It is **sustainable throughput**: the highest rate at which the system still meets its latency target. Tene's image is a car hitting a pole. You can measure the shape of the bumper after impact, but the useful question is how fast the car can go without hitting the pole. A test at 1.5% below the collapse point is a test of the bumper.

A latency number without a load number is incomplete. “The p99 is 10 milliseconds” is not a claim about a system. It is a claim about a system at some arrival rate, with some concurrency, on some data. Change the rate and you change the queue. Change the queue and you change the number.

## Count the requests that never happened

The fix is not a better dashboard. It is a different sampling frame: measure the requests that should have arrived, not only the ones the system was able to accept.

An open-loop generator issues requests on a schedule, independent of responses. If the schedule says one request every 10 milliseconds, it issues one every 10 milliseconds, even while the service is frozen. The requests queue in the client or the network, as independent users would. Each one records its latency against the time it was supposed to start.

```
for t in schedule:   # intended
    done = send()    # may block
    record(done - t) # caller's wait
```

Here `t` is the time the request was supposed to start, not the time it actually left, and `record` takes the difference. With that change, the ten thousand requests that arrive during the freeze are all measured. The one that waited 100 seconds, the one that waited 90, the one that waited 10: all of them are in the distribution. The average returns to 25 seconds, where it belongs.

If the tool cannot issue open-loop, it can reconstruct the missing samples. HdrHistogram, the library Tene wrote, records a value with an expected interval. When a request takes 100 seconds and the intended rate is one per 10 milliseconds, it fills in 100 seconds, 99.99, 99.98, and so on down to 10 milliseconds. Those are the requests that would have been issued during the stall, each waiting slightly less than the one before. The reconstruction is an approximation of the right population, not a correction of the wrong one.

Calibrate the tool with a freeze. Under load, suspend the server process for a few seconds, then resume it. On Unix, `kill -STOP` and `kill -CONT` do this; Ctrl-Z suspends a foreground job with the same effect. If the measured maximum does not jump by roughly the length of the pause, the tool is not seeing the stall. Tene calls this the control-Z test. It is the cheapest audit in performance work: one deliberate stall, and the measurement either notices or confesses.

Then plot the maximum over time. The maximum is not noise; it is the signal. A single slow request is the only sample that contains the stall. Percentile lines can stay flat while the maximum goes vertical.

{{< figure src="fig-06.jpg" alt="Two time-series charts of maximum latency: System A is a dense field of red spikes up to 1,400 milliseconds, while System B is nearly flat." caption="Fig. 6 — Two systems at the same load. The maximum, plotted over time, separates them at a glance; the percentile lines would not. [36:16]" >}}

> That is not noise. That is the signal.

That is Tene on the maximum, and it is the right default. A vertical rise in a latency-over-time chart has a high chance of being coordinated omission rather than a change in the service's work. The shape is diagnostic: a real queue builds, while an omitted sample appears as a cliff.

The tooling matters less than the audit. In Tene's 2015 rundown, Gatling had fixed the problem; JMeter, Grinder, wrk, and most commercial generators had not. YCSB (Yahoo! Cloud Serving Benchmark) on GitHub had been fixed by a colleague; older versions had not. His own wrk2 and cassandra-stress2 were demonstrations, not products he was maintaining. The list is a decade old. The test is not: freeze the system and see whether the number moves.

## The correction has limits

Every correction embeds an assumption about demand. The fixed-rate model says the same number of requests would have arrived if the system had been healthy. That is a good model for a large population of independent users. It is a bad model for a single client that waits, and it is a bad model when demand is elastic.

When a service slows, users retry, abandon, or come back later. A retry can increase the arrival rate; an abandonment can decrease it. If the real population would have backed off, correcting at the nominal rate invents requests that never existed and reports waits no one experienced. The correction is a statement about a counterfactual, and the counterfactual needs to be defended.

When a system sheds load, the missing requests were not slow; they were rejected. A 429, a timeout, a circuit breaker, a full queue with a fail-fast policy: these are outcomes, not omissions. Record them as their own category. Do not synthesize a latency for a request that was never admitted, and do not let a rejection disappear from the denominator. The user experienced something. The graph should say what.

The correction cannot recover a stall outside the measurement window. If the delay happens in a proxy, in a DNS lookup, or in a dependency you did not instrument, no arithmetic at the server recovers it. Instrument the caller, or you are measuring the service's opinion of itself.

Then there is the arithmetic of rare events. A p99.9 computed from a hundred samples is the maximum. From a thousand, it is one of the two worst. Neither is an estimate of a rare event; it is a description of the edge of the sample. Report the count with the percentile. The maximum is one sample, so it is noisy by construction, which is why it belongs on a time series rather than in a single summary row. A histogram with bounded relative error, like HdrHistogram's log-linear buckets, buys the full spectrum in fixed space, but it is still a trade: precision for memory, and a range that has to be chosen in advance.

Clocks deserve their own paragraph and usually do not get one. Use a monotonic clock for durations. Do not subtract timestamps from different hosts unless you have measured the skew. A measurement system that is wrong by a few milliseconds is fine for a p99 of 10 milliseconds and useless for a p99 of 500 microseconds.

## Keep the caller's clock

Three questions make a latency claim checkable. Whose clock started the timer? Which population of requests does the number describe? What happened to the requests the system could not serve?

If the answer to the first is “the server, when it began the work,” you have service time. If it is “the caller, when it wanted the answer,” you have response time. If the answer to the second is “the requests that completed,” you have a survivor's sample; the requests that timed out, were rejected, or were never issued are missing. If the answer to the third is silence, the number is a marketing number.

Latency is a queueing phenomenon before it is a code phenomenon. The barista can be fast and the line can still be out the door. The database can answer in a hundred milliseconds and the user can wait seven seconds. The fix may be in the code, but the measurement has to be at the caller, on the intended schedule, with the maximum in view.

Measure the wait, not the work. Plot the maximum. Freeze the system once and check that the graph notices. Report the load with the latency, and report the requests that never made it into the sample. A latency number is only as honest as its denominator.

---

Source: [“How NOT to Measure Latency”](https://www.youtube.com/watch?v=lJ8ydIuPFeU) by Gil Tene at Strange Loop Conference, 43 min. Watched 22 October 2026. Figures are stills from the video at the timestamps in their captions.
