# Weekly Metrics Report — Week of 2026-05-26

DAU and revenue both up week-over-week. Latency p99 regressed mid-week and recovered. Two notable launches.

## Headline numbers

| Metric | This week | Last week | Δ |
|--------|-----------|-----------|---|
| DAU | 1.24M | 1.18M | +5.1% |
| Revenue | $487K | $452K | +7.7% |
| New signups | 18,400 | 16,900 | +8.9% |
| Churn | 0.9% | 1.1% | -0.2pp |

DAU growth is being driven by the search experiment graduation (Tuesday rollout). Revenue growth tracks DAU plus a small ARPU lift from the new tier.

## Latency incident

Wednesday 11:23-12:08 UTC: API p99 jumped from 240ms to 1.4s. Root cause was an underprovisioned cache cluster after a routine restart. SRE added a node and increased the cluster's reserved capacity by 30%. Postmortem in #sev2-postmortems.

## Launches

- Search v2 graduated to 100% on Tuesday after 4 weeks at 50%
- Pricing tier "Pro Annual" launched Thursday; 312 conversions in 48 hours

## Looking ahead

Next week: holiday-shopping load test on Wednesday night. Expect higher-than-usual write traffic on the order service.
