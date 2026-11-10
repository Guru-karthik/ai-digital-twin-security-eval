# Models and licences (UNVERIFIED notes)

| Model | Use | Licence (from memory, not yet checked against the model card) |
| --- | --- | --- |
| qwen3:8b (Ollama) | local answer model and judge for hosted runs | Apache-2.0 expected; check the model page before publishing results |
| llama3.1:8b (Ollama) | local answer model and judge for Qwen answers | Llama 3.1 Community Licence (custom, not Apache); read its terms before publishing |
| gpt-5-nano (OpenAI API) | hosted answer model and judge for local runs | API terms of service; no weights are downloaded |

Approved by the owner: budget cap USD 10 total hosted spend plus USD 2 for the first D0 dev run (2026-11-10).
Prices in `eval/models.yaml` come from OpenAI's pricing page as read on 2026-11-10 and must be re-checked.
Weights are pulled with `ollama pull` outside the repository; they are not committed.
