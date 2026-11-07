# Variant A — human-grounded validation of MLLM video annotation

Gold: manual close-viewing scene typology — **247 scenes** (scene_descriptions.xlsx). Shared lexicon applied to both human label and model keywords (minimal DOF).

**Recall** = of scenes the *human* marked as category C (label matches lexicon), share where the *model's keywords* also match C. I.e. did the model see what the human saw?

| Category | human scenes (gold) | GPT-4o recall | LLaVA recall |
|---|---:|---:|---:|
| police / detention | 115 | 71% | 57% |
| protest / crowd | 137 | 87% | 81% |
| voting / election | 23 | 35% | 17% |
| flag / symbol | 51 | 100% | 96% |
| night scene | 47 | 100% | 100% |
| **macro avg** | | **79%** | **70%** |

> GPT-4o recovers the human-coded scene theme in **79%** of scenes on average; LLaVA in **70%**. The gap is the open-vs-closed capability difference made concrete on a human gold standard — and it is exactly the kind of per-category validation that the multimodal frontier currently lacks in the Slavic-language setting.

**Honesty note:** this is a presence-of-term recall against a human free-text typology, not full inter-coder κ (the human labels are sequential scene descriptions, not a fixed category scheme). It is a lower-bound sanity check on whether the model surfaces the human-identified content, deliberately low in researcher degrees of freedom (one shared lexicon).
