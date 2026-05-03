# Backend Limit Alignment

The deployment work found that the accepted training inputs could be longer than the earlier backend block limit. The AI service therefore uses:

```text
CLEARREAD_AI_MAX_CHARACTERS_PER_TEXT=11000
```

The earlier deployment branch also raised the backend-side reading block cap from `6000` to `11000` characters so the backend and AI service would not disagree about acceptable block size.

This package does not directly modify the main backend service. It records the integration requirement so the backend team can apply or verify the same limit in the final application branch.

Recommended backend alignment:

| Setting | Value |
|---|---:|
| Max characters per reading block sent to AI | 11000 |
| Current L4 MVP max blocks per AI request | 28 |
| Conservative product max blocks per AI request | 24 |
| Backend timeout for AI request | 125 to 130 seconds |
