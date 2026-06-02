# Rate Limiter Design: Token Bucket vs Leaky Bucket

When traffic spikes hit production, you want a rate limiter that lets normal bursts through while still protecting downstream systems. This article walks through the two classic algorithms and why we picked token bucket for our API gateway.

## The burst problem

Real traffic is never smooth. Average request rate looks fine on a dashboard, but peaks can be 5-10x the average. A naive "fixed requests per second" limiter rejects valid bursts and produces user-visible failures. The MAU growth chart from last quarter shows the gap: average 800 req/s but peaks above 4000 req/s during morning logins.

You need an algorithm that absorbs short bursts without sustaining them indefinitely.

## Token bucket algorithm

Imagine a bucket with capacity 200 tokens, refilling at 100 tokens/sec. Each incoming request takes one token. When the bucket is empty, requests get 429s until it refills.

This means:
- During quiet periods, the bucket fills to capacity
- A burst of up to 200 requests passes immediately
- Sustained load above the refill rate eventually gets throttled

The bucket size controls burst tolerance; the refill rate controls sustained throughput.

## Leaky bucket vs token bucket

Leaky bucket smooths output but adds latency. Requests queue up and drain at a fixed rate. Token bucket allows controlled bursts and rejects excess immediately.

For our API gateway, latency matters more than smoothness. Users would rather get a 429 they can retry than wait 3 seconds for their request to drip through. We picked token bucket.

## Implementation notes

A simple in-memory token bucket fits in 20 lines of Go. The hard part is making it work across a horizontally scaled fleet — that's a separate post about Redis-backed counters and the tradeoffs of strong vs eventual consistency.
