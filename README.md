# How to Stop a Model Picking the Wrong Fact From a Long Prompt

**TL;DR:** A model reading a long prompt favors the passage that best matches your question, true or not. Long prompts hurt mostly because they carry more look-alikes, so keep those out and ask questions only the right passage answers.

Published from [The AI Commit](https://theaicommit.com/#2026-11-05/code) — Applied Research, 2026-11-05.

## Run

```bash
python3 code_example.py
```

## Output

```
Question that echoes the look-alikes (toy model):
  tokens             500    4000   16000   64000
  clean             100%    100%    100%    100%
  look-alikes         0%      0%      0%      0%
Question naming what only the true passage has (toy model):
  tokens             500    4000   16000   64000
  clean             100%    100%    100%    100%
  look-alikes       100%    100%    100%    100%

assemble_context on six retrieved chunks:
  kept 2 of 6; refund rules left in the prompt:
   - Refunds are allowed within 30 days of delivery.
   - Orders ship within two business days.

```

## Code

See [`code_example.py`](code_example.py).
