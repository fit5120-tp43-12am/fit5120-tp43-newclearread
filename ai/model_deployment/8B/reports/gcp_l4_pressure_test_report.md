# Google Cloud L4 Pressure Test Report

Date: 2026-05-02

## Overview

The Google Cloud L4 pressure test measured how many already-prepared text blocks the ClearRead AI Summary service could summarise within the project target of approximately 30 seconds.

The main outcome:

| Setting | Decision |
|---|---|
| 28 representative blocks | Accepted current MVP cap. |
| 24 representative blocks | Conservative product setting. |
| 32 representative blocks | Not recommended for the current 30-second target. |

## Test Environment

| Item | Value |
|---|---|
| Cloud provider | Google Cloud |
| Region | Singapore region |
| Machine type | `g2-standard-8` |
| GPU | 1 x NVIDIA L4 |
| GPU memory | about 23 GB |
| Model route | Llama-3.1-8B-Instruct with QLoRA adapter |
| Serving runtime | vLLM behind ClearRead API wrapper |
| Public route tested | ClearRead AI Summary API |
| Internal vLLM exposure | localhost-only |

## Behaviour Checked

The tests checked:

- `/health` returned `200`;
- `/ready` returned `200`;
- unauthenticated summarize requests returned `401`;
- wrapper docs routes were disabled;
- each successful block returned exactly one `summary`;
- each successful block returned exactly four `keyPoints`;
- result order was preserved;
- raw vLLM response fields were not returned by the public wrapper.

## Initial Configuration Result

The first cloud setup kept wrapper-to-vLLM internal concurrency at `8`.

| Blocks | Latency range | Result |
|---:|---|---|
| 8 | 23.376s to 28.698s | passed |
| 9 | 33.389s to 35.632s | over target |
| 10 | 39.059s to 39.318s | over target |
| 11 | 40.189s to 41.878s | over target |
| 12 | 40.607s to 41.240s | over target |

This showed that the 8-block result was largely caused by a configuration bottleneck.

## Improved Configuration

The runtime was then tuned:

| Setting | Improved value |
|---|---:|
| Wrapper internal concurrency | 16, then 28 for final MVP |
| vLLM max sequences | 16, then 28 for final MVP |
| Maximum output tokens | 256 |
| vLLM eager mode | disabled |

With improved settings:

| Blocks | Latency | Result |
|---:|---:|---|
| 8 | 20.504s | 8/8 ok |
| 10 | 21.261s | 10/10 ok |
| 12 | 21.950s | 12/12 ok |
| 16 | 23.408s to 27.209s | 16/16 ok |
| 17 | 24.603s to 26.988s | 17/17 ok |
| 18 | 31.122s | over target |
| 20 | 36.442s | over target |

## Capacity Discovery

Higher concurrency settings were tested to find the practical boundary:

| Config | Blocks | Latency | Result |
|---|---:|---:|---|
| 16/16 | 16 | 22.252s | pass |
| 16/16 | 18 | 31.066s | over target |
| 24/24 | 24 | 23.740s | pass |
| 32/32 | 28 | 25.432s | pass |
| 32/32 | 32 | 25.492s | passed once, not stable |
| 48/48 | 48 | 29.913s | passed once, not stable |
| 64/64 | 64 | 31.320s | over target |

Single passing runs at 32 or 48 blocks were not accepted as stable product settings.

## Stability Testing

Repeated 28-block tests passed:

| Blocks | Latency | Result |
|---:|---:|---|
| 28 | 26.438s | 28/28 ok |
| 28 | 22.669s | 28/28 ok |
| 28 | 25.037s | 28/28 ok |

Repeated 32-block tests failed the target:

| Blocks | Latency | Result |
|---:|---:|---|
| 32 | 34.484s | over target |
| 32 | 31.619s | over target |
| 32 | 34.330s | over target |

## Final MVP Configuration

```text
max text blocks per request: 28
max characters per text block: 11000
request body limit: 2 MiB
wrapper-to-vLLM internal concurrency: 28
maximum output tokens: 256
vLLM max sequences: 28
vLLM eager mode: disabled
```

## Conclusion

The pressure test showed that the initial 8-block result was not the true capacity. After tuning vLLM and wrapper concurrency, the L4 deployment could handle substantially larger batches. The highest stable repeated setting under the current target was 28 representative blocks, while 32 blocks was not stable enough.
