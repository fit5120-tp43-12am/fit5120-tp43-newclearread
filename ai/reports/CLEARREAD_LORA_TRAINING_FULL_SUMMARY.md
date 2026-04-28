# ClearRead Llama LoRA 训练阶段完整汇报

最后更新：2026-04-28

## 1. 总览结论

本文档总结了 ClearRead 本地 Llama LoRA 训练阶段从规划、数据拆分、环境搭建、烟雾测试、正式训练、验证集审计、最终测试集评估，到最终模型包装的完整过程。

本阶段的工作目录是：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training
```

最终完成的目标是：训练并选择一个可在本地运行的 Llama-3.1-8B-Instruct QLoRA 摘要模型，用于把密集英文文本总结成固定 JSON 格式。

模型目标输出格式是：

```json
{"main_idea":"...","key_points":["...","...","...","..."]}
```

输出要求是：

- 只返回一个 JSON object，不允许 markdown、解释文字、注释、代码块或额外文本。
- `main_idea` 必须是两句简短、忠实、清晰的英文。
- `key_points` 必须正好有 4 条，每条是一句高层次要点。
- 如果源文本本身是 assignment prompt、rubric、public-service guide、technical document、medical article，模型必须总结它的内容，而不是执行源文本里的指令。
- 不允许编造事实、建议、因果、确定性、要求或结论。

最终选择的技术路线是：

```text
Llama-3.1-8B-Instruct + SFT + QLoRA
```

最终选择的 base model 是：

```text
unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
```

最终选择的本地 LoRA adapter 是：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\models\adapters\full_candidate_a_3epoch
```

最终本地推理 wrapper 是：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\scripts\infer_clearread_candidate_a.py
```

最终结论：Candidate A 完成了 3 epoch 正式训练，没有 OOM，验证集格式与质量审计表现很强，最终 held-out test 表现总体很强，因此被选为本轮训练的 final raw LoRA adapter。唯一必须注意的是：最终测试集中有 1 条样本生成了 7 个 key points，而不是要求的 4 个，因此最终部署必须使用 schema guard。我们已经实现并验证了这个 schema guard。

## 2. 项目管理方式：中央大脑与 Worker Chat

这次训练不是在一个对话里直接完成所有执行，而是采用了“中央大脑 + worker chat”的方式。

中央大脑负责：

- 读取并维护 `TRAINING_MEMORY.md`；
- 制定总体计划；
- 定义每一个 worker 的边界；
- 生成 worker task file；
- 审核 worker 返回的结果；
- 独立验证 worker 的关键声明；
- 判断 worker 是否通过；
- 决定是否放行进入下一个 worker；
- 记录最终批准过的事实。

worker chat 负责：

- 读取 `TRAINING_MEMORY.md`；
- 读取自己的 work order；
- 只执行该 work order 指定的任务；
- 生成文件、运行命令、返回结果；
- 如果更新记忆，只能写 provisional section；
- 不能把自己的结论直接变成中央大脑批准结论。

之所以这样设计，是因为用户明确要求当前对话作为中央大脑，后续大步骤由其他对话框执行，但中央大脑必须评估每个 worker 的返回结果，决定是否通过，以及是否允许开始下一个 worker。

同时，用户还特别要求避免 worker 污染中央大脑记忆和判断。因此我们建立了 memory quarantine 规则：worker 结论只是 evidence，不是 authority。所有关键事实都必须由中央大脑通过本地文件、hash、count、Git status、log 等方式独立验证后，才能写入 approved memory。

相关协议文件：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\docs\CENTRAL_BRAIN_WORKER_PROTOCOL.md
```

总体计划文件：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\docs\MASTER_TRAINING_PLAN.md
```

训练阶段记忆文件：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\TRAINING_MEMORY.md
```

## 3. 项目核心约束

本阶段最重要的约束有四类。

第一，不能修改原始数据集。

原始数据集必须保持只读：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\data\final_lora_data\outputs\final_dataset_v1
```

任何后续数据处理、清洗、拆分、导出，都必须创建新的 derived output，不能直接改 source dataset。

第二，本次训练使用 system-prompt-cleaned derived dataset：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\data\final_lora_data\outputs\final_dataset_v1_training_system_clean
```

正式使用的 accepted 目录是：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\data\final_lora_data\outputs\final_dataset_v1_training_system_clean\accepted
```

第三，拆分规则必须尊重真实数据分布。最初讨论长度分布时，曾经容易误解为短、中、长三个 bucket 要均衡。用户明确纠正：不需要均衡，应该按照真实数据分布来拆。例如如果真实数据是短 20%、中 70%、长 10%，验证集和测试集也应尽量接近这个真实比例。进一步确认后，最终规则变成：先保证每个 split 的 domain 分布接近整体，再在每个 domain 内部保留该 domain 自己的短、中、长分布。

第四，Git 是强制流程门，不是可选记录。每个主要阶段完成后，Git-safe 的 scripts、configs、docs、reports、logs 都要提交并 push；但完整 JSONL 数据、模型权重、adapter、checkpoint、cache 等不能提交。

## 4. 源数据状态

训练使用的数据不是原始 `final_dataset_v1`，而是 system prompt 已替换过的 derived copy：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\data\final_lora_data\outputs\final_dataset_v1_training_system_clean\accepted\all_v1.jsonl
```

已确认事实：

- `all_v1.jsonl` 总记录数：1452。
- 原 accepted 数据记录数：1452。
- `user_changed`: 0。
- `assistant_changed`: 0。
- derived `all_v1.jsonl` 是 7 个 per-domain 文件的精确拼接。
- derived `all_v1.jsonl` SHA256：

```text
c82097c07054198a791297998786b18a3d202d78684fcef03dbe723659c0fea2
```

7 个领域分布如下：

| Domain | Count | Percent |
|---|---:|---:|
| assignment_rubric | 83 | 5.72% |
| tech_doc | 89 | 6.13% |
| academic_book | 233 | 16.05% |
| academic_paper | 486 | 33.47% |
| public_service | 198 | 13.64% |
| medlineplus | 230 | 15.84% |
| gen_know | 133 | 9.16% |
| Total | 1452 | 100.00% |

文本长度统计使用的 regex 是：

```text
[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*
```

真实长度 bucket 分布是：

| Bucket | Rule | Count | Percent |
|---|---|---:|---:|
| short | `<=400` words | 241 | 16.60% |
| medium | `401-800` words | 1018 | 70.11% |
| long | `>=801` words | 193 | 13.29% |

这也验证了用户之前对数据的记忆：大部分文本确实集中在 400 到 800 词之间，中位数也在 600 左右。实际测得用户文本 word count 中位数是 `622`，平均值是 `618.62`。

## 5. 总体计划

最终计划拆成 10 个 worker：

| Worker | 任务 | 最终状态 |
|---|---|---|
| 000 | Git branch 和 artifact safety setup | 通过 |
| 001 | 统计源数据分布并创建 train/val/test/smoke split | 通过 |
| 002 | 创建 teammate user/assistant exports | 通过 |
| 003 | 创建并验证 WSL 训练环境 | 通过，有 notes |
| 004 | 准备 smoke training scripts/configs 和 loss mask 检查 | 通过 |
| 005 | 运行 Llama smoke training | 通过 |
| 006 | 运行 Candidate A full training | 通过，有 notes |
| 007 | Candidate A validation quality audit | 通过 |
| 008 | Final held-out test evaluation | 通过，并选择 Candidate A |
| 009 | Final artifact packaging 和 local deployment notes | 通过 |

Candidate B 曾被设计为 optional fallback，但最终没有运行。原因是 Candidate A 的 validation audit 已经足够强，没有证据支持再训练一个 B；最终 test 使用后，也不能因为 test 上看到一个 schema miss 就再训练或调参，否则会污染 held-out test 的独立性。

## 6. Worker 000：Git 分支和安全保护

Worker 000 的目标是先建立 Git 安全边界，避免后续训练过程中把数据或模型大文件误提交。

团队 repo：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\code\fit5120-tp43-newclearread
```

使用分支：

```text
feature/ai-llama-lora-training
```

Worker 000 完成了：

- fetch remote；
- checkout latest `dev`；
- 创建 `feature/ai-llama-lora-training`；
- 添加或确认 AI artifact ignore 规则；
- 提交并 push Git-safe setup 记录。

关键 ignore 保护包括：

- `ai/data/**/*.jsonl`
- `ai/models/`
- `ai/outputs/`
- `ai/checkpoints/`
- `ai/cache/`
- `*.safetensors`
- `*.pt`
- `*.pth`
- `*.bin`
- `unsloth_compiled_cache/`

中央大脑审核确认：

- branch 正确；
- worktree clean；
- local HEAD 等于 upstream；
- `.gitignore` 能保护代表性 JSONL、模型、输出、checkpoint、cache 文件；
- 没有大文件被 staged。

Worker 000 通过。

## 7. Worker 001：数据分布统计与拆分

Worker 001 创建了拆分脚本：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\scripts\create_stratified_splits.py
```

最终拆分方法是 deterministic approximate joint stratification over：

```text
domain x natural_length_bucket
```

也就是说，validation/test 首先匹配每个 domain 的目标数量，然后在每个 domain 内用 largest-remainder rounding 尽量保留该 domain 的真实 short/medium/long 分布。最后 train 拿剩余记录。

最终 split：

| Split | Count | Percent |
|---|---:|---:|
| train | 1162 | 80.03% |
| val | 145 | 9.99% |
| test | 145 | 9.99% |

domain split 数量：

| Domain | Total | Train | Val | Test |
|---|---:|---:|---:|---:|
| assignment_rubric | 83 | 67 | 8 | 8 |
| tech_doc | 89 | 71 | 9 | 9 |
| academic_book | 233 | 187 | 23 | 23 |
| academic_paper | 486 | 388 | 49 | 49 |
| public_service | 198 | 158 | 20 | 20 |
| medlineplus | 230 | 184 | 23 | 23 |
| gen_know | 133 | 107 | 13 | 13 |
| Total | 1452 | 1162 | 145 | 145 |

overall length bucket 数量：

| Bucket | Source | Train | Val | Test |
|---|---:|---:|---:|---:|
| short | 241 | 191 | 25 | 25 |
| medium | 1018 | 816 | 101 | 101 |
| long | 193 | 155 | 19 | 19 |

Worker 001 输出文件：

```text
reports/source_distribution_profile.json
reports/SOURCE_DISTRIBUTION_PROFILE.md
data/splits/train.jsonl
data/splits/val.jsonl
data/splits/test.jsonl
data/splits/smoke_test_10.jsonl
data/splits/split_manifest.json
data/splits/SPLIT_REPORT.md
logs/decisions/worker_001_profile_split.md
```

关键 hash：

| File | SHA256 |
|---|---|
| `train.jsonl` | `b99caa6b06963a05ca7e32da3c3be3237c9ea6b128ce1ccf329b78d2d56929fb` |
| `val.jsonl` | `a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be` |
| `test.jsonl` | `6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f` |
| `smoke_test_10.jsonl` | `8f51d083e8fafae143ec146c0155f85dc23a5cfdaf931a04092e7f8543d2d3a8` |
| `split_manifest.json` | `42bfe9974c31e74b98b45d45daa792f8582d517541e153439b510e9a9b307f19` |

验证结果：

- train/val/test 数量正确；
- 1452 条记录全部唯一分配；
- train、val、test 之间没有 stable hash overlap；
- per-domain counts 完全匹配目标；
- val/test 在每个 domain 内尽量保留真实 length bucket 分布；
- allocation 没有 deviation；
- smoke set 有 10 条，全部来自 train；
- manifest 有 1452 条 metadata-only entries；
- manifest 不包含 raw `messages`、`system`、`user`、`assistant`、`content`；
- 脚本 rerun 后 hash 不变；
- 源文件 hash 未改变。

Worker 001 通过中央大脑审核。

## 8. Worker 002：Teammate User/Assistant Exports

用户后续补充：队友的 benchmark packaging 暂时不做复杂处理，只需要把 user 和 assistant 拆出来，形成两个对应的数据集，至于队友如何使用由队友自己决定。

Worker 002 创建脚本：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\scripts\create_teammate_exports.py
```

输出目录：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\data\teammate_exports
```

导出数量：

| Scope | User Rows | Assistant Rows |
|---|---:|---:|
| train | 1162 | 1162 |
| val | 145 | 145 |
| test | 145 | 145 |
| all | 1452 | 1452 |

验证结果：

- user 和 assistant 文件逐行对齐；
- `pair_index`、`pair_id`、`record_id`、`stable_hash`、`split`、`domain`、`source_file`、`source_line`、`natural_length_bucket` 全部对应；
- user text 只来自源数据 user role；
- assistant text 只来自源数据 assistant role；
- export row 不包含 `messages`；
- system prompt 不出现在导出 text 中；
- teammate manifest 是 metadata-only；
- source split hash 前后不变；
- deterministic rerun passed。

这些 teammate export JSONL 文件没有提交到 Git。

Worker 002 通过。

## 9. Worker 003：WSL 训练环境

Worker 003 创建并验证了新的 WSL conda 环境：

```text
clearread-llama-lora
```

路径：

```text
/home/aufb/miniconda3/envs/clearread-llama-lora
```

关键环境信息：

| 项目 | 值 |
|---|---|
| WSL distro | Ubuntu |
| WSL version | 2 |
| Ubuntu release | 24.04.4 LTS |
| Python | 3.11.15 |
| GPU | NVIDIA GeForce RTX 4070 Ti SUPER |
| VRAM | about 16 GB |
| Driver | 560.94 |
| PyTorch | 2.10.0+cu128 |
| CUDA runtime | 12.8 |
| `torch.cuda.is_available()` | true |
| CUDA device count | 1 |
| BF16 support | true |

关键 package：

| Package | Version |
|---|---:|
| torch | 2.10.0 |
| transformers | 5.5.0 |
| datasets | 4.3.0 |
| accelerate | 1.13.0 |
| peft | 0.19.1 |
| trl | 0.24.0 |
| bitsandbytes | 0.49.2 |
| unsloth | 2026.4.8 |
| huggingface_hub | 1.12.0 |
| safetensors | 0.7.0 |
| sentencepiece | 0.2.1 |
| xformers | 0.0.35 |

发现的问题：

1. Hugging Face CLI 可用，但没有登录。
2. 官方 Meta Llama 3.1 8B Instruct 是 gated/manual。
3. public Unsloth 4-bit model metadata 可以访问。
4. Flash Attention 2 broken，Unsloth 自动 fallback 到 xformers。
5. Unsloth pip resolver 最终把 stack 解析到 `torch 2.10.0+cu128`。

解决方式：

- 使用 public Unsloth 4-bit model 作为 preferred base model，因此 HF 未登录不阻塞。
- 官方 Meta 模型只保留为 fallback，如果以后使用才需要登录和接受 access。
- Flash Attention 2 不可用不阻塞，因为 xformers fallback 可用，CUDA、BF16、tensor test、imports 全部通过。
- `torch 2.10.0+cu128` 被接受，因为实际 runtime 验证通过。

Worker 003 通过，有 notes。

## 10. Worker 004：Smoke Training 准备和 Loss Mask 检查

Worker 004 准备 smoke training 脚本和配置，但没有运行真实训练。

创建文件：

```text
configs/smoke_llama31_8b_qlora.yaml
scripts/training_data_utils.py
scripts/verify_assistant_loss_mask.py
scripts/train_smoke_qlora.py
scripts/run_inference_check.py
reports/LABEL_MASK_SANITY_CHECK.md
reports/SMOKE_TRAINING_PREP_REPORT.md
```

smoke config 核心参数：

| 参数 | 值 |
|---|---|
| Base model | `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit` |
| Data | `data/splits/smoke_test_10.jsonl` |
| Max sequence length | 3072 |
| QLoRA | 4-bit NF4 |
| LoRA r | 16 |
| LoRA alpha | 32 |
| LoRA dropout | 0.05 |
| Target modules | `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj` |
| Batch size | 1 |
| Gradient accumulation | 4 |
| Max steps | 20 |
| Learning rate | 2e-4 |
| Seed | 5120 |

最关键的技术点是 assistant-only loss masking。

我们没有直接依赖 TRL 的 `assistant_only_loss`，因为该路径依赖 chat template 的 generation mask。这里采用更明确的方式：使用 tokenizer chat template 分别渲染 prompt 和 full text，把 system/user prompt 区域 label 设为 `-100`，只让 assistant JSON completion tokens 参与 loss。

label mask 检查结果：

- smoke records checked: 10；
- records with trainable assistant tokens: 10；
- decoded trainable labels parse as JSON: 10；
- decoded trainable JSON matches source assistant JSON: 10；
- total masked prompt tokens: 12071；
- total trainable assistant tokens: 1323；
- truncated records: 0。

Worker 004 通过。

## 11. Worker 005：Smoke Training

Worker 005 在 10 条 smoke set 上运行第一次真实训练。

结果：

| 项目 | 值 |
|---|---|
| Status | success |
| OOM | no |
| Model | `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit` |
| Adapter | `models/adapters/smoke_llama31_8b_qlora` |
| Steps | 20 |
| Final training loss | 0.5587 |
| Final step loss | 0.02816 |
| Trainer runtime | 87.37 seconds |
| Script elapsed | 89.61 seconds |
| Final callback speed | 4.368 seconds/step |

训练后 inference sanity check：

- checked examples: 3；
- schema pass: 3/3；
- valid JSON shape: 3/3；
- required keys present: 3/3。

发现的问题：

- 第一次尝试从 PowerShell 用 `Start-Process` 后台启动 WSL 训练失败，因为 WSL `bash -lc` quoting 在 conda activation 前被破坏。

解决方式：

- 这次失败没有真正开始训练，也没有写 adapter。
- 后续直接在 WSL 中运行训练命令，成功完成。

Worker 005 通过。它证明环境、masking、adapter 保存、推理 sanity check 流程都能工作。

## 12. Worker 006：Candidate A 正式训练

Worker 006 运行正式 Candidate A 训练。

训练配置：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\configs\train_llama31_8b_qlora_candidate_a.yaml
```

核心参数：

| 参数 | 值 |
|---|---|
| Base model | `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit` |
| Method | SFT |
| Tuning | QLoRA |
| Train data | `data/splits/train.jsonl` |
| Val data | `data/splits/val.jsonl` |
| Max sequence length | 3072 |
| LoRA r/alpha/dropout | `16 / 32 / 0.05` |
| Effective batch size | 8 |
| Epochs | 3 |
| Learning rate | 0.0002 |
| Warmup ratio | 0.03 |
| Weight decay | 0.01 |
| Optimizer | `adamw_8bit` |
| Seed | 5120 |
| Adapter output | `models/adapters/full_candidate_a_3epoch` |

preflight 结果：

| Split | Records | Max Input Tokens | Max Assistant Tokens | Total Assistant Tokens | Truncated | JSON OK |
|---|---:|---:|---:|---:|---:|---:|
| train | 1162 | 2296 | 192 | 148979 | 0 | 1162 |
| validation | 145 | 2171 | 204 | 18677 | 0 | 145 |

正式训练结果：

| 项目 | 值 |
|---|---|
| Status | success |
| OOM | no |
| Epochs | 3 |
| Optimizer steps | 438 |
| Final train loss | 0.4797596574748216 |
| Validation loss | 0.9654271602630615 |
| Start | 2026-04-28T15:29:34+10:00 |
| End | 2026-04-28T16:34:13+10:00 |
| Elapsed | 1h 04m 39s |
| Final ETA callback speed | 8.68 seconds/step |
| Validation eval runtime | 75.1215 seconds |

训练后 validation sanity：

- checked examples: 10；
- schema pass: 10/10。

发现的问题：

- train 中有 2 条 decoded label exact JSON object mismatch，是 tokenizer decode spacing around `.gov` 导致。

解决方式：

- 两条仍然能 parse as JSON；
- labels 非空；
- 没有 truncation；
- 因此不作为 blocker。

中央大脑额外 rerun 了 5 条 validation inference，结果 5/5 schema pass。Worker 006 通过，有 notes。

## 13. Worker 007：Validation Quality Audit

Worker 007 只使用 validation split，没有使用 test，没有训练。

输入：

```text
Adapter: models/adapters/full_candidate_a_3epoch
Validation data: data/splits/val.jsonl
Validation SHA256: a7cf5277eda97ef1868376caa79343b040ba6920602bc607dc145a2039d2d4be
```

生成耗时：

| 项目 | 值 |
|---|---|
| Started | 2026-04-28T17:40:57+10:00 |
| Finished | 2026-04-28T17:52:35+10:00 |
| Elapsed | 11m 38s |
| Average | 4.814 seconds/example |

validation deterministic metrics：

| Metric | Value |
|---|---|
| Records | 145 |
| JSON parse | 145/145 |
| Schema pass | 145/145 |
| Exact key order | 145/145 |
| Exactly 4 key points | 145/145 |
| Main idea two-sentence heuristic | 144/145 |
| Each key point one-sentence heuristic | 143/145 |
| Markdown/code-fence leakage | 0 |
| Extra text outside JSON | 0 |
| Refusal/meta-response phrases | 0 |
| Prediction mojibake rows | 0 |
| Gold mojibake rows | 0 |

manual review：

| Label | Count |
|---|---:|
| pass | 14 |
| minor_issue | 2 |
| major_issue | 0 |
| uncertain | 0 |

结论：

- 没有 instruction-following failure；
- 没有 refusal/meta behavior；
- 没有 mojibake；
- 没有 domain 或 length bucket 的整体崩坏；
- 两个 minor issues 只是局部事实精度或措辞问题；
- Candidate B 不推荐；
- Candidate A 可以进入 final test evaluation。

发现的问题：

- 有一个 validation 样本在 terminal 显示中看起来像 mojibake。

解决方式：

- 中央大脑用 Python UTF-8 parsing 重新检查；
- 判断为 terminal/rendering artifact，不是数据或预测文件损坏。

Worker 007 通过。

## 14. Worker 008：Final Held-Out Test Evaluation

Worker 008 是第一次获批使用 `data/splits/test.jsonl`。这个阶段不训练、不调参、不跑 Candidate B。

输入：

```text
Adapter: models/adapters/full_candidate_a_3epoch
Test data: data/splits/test.jsonl
Test SHA256: 6613390f654c55a69c5ddb90234f81005fc3baca8e57651206f1ef024c939b7f
```

生成耗时：

| 项目 | 值 |
|---|---|
| Started | 2026-04-28T18:17:52+10:00 |
| Finished | 2026-04-28T18:29:42+10:00 |
| Elapsed | 11m 50s |
| Average | 4.899 seconds/example |

final test deterministic metrics：

| Metric | Value |
|---|---|
| Records | 145 |
| JSON parse | 145/145 |
| Schema pass | 144/145 |
| Exact key order | 145/145 |
| Main idea string | 145/145 |
| Key points list | 145/145 |
| Exactly 4 key points | 144/145 |
| All key points strings | 145/145 |
| Main idea two-sentence heuristic | 144/145 |
| Each key point one-sentence heuristic | 144/145 |
| Empty-string rows | 0 |
| Output too short / too long | 0 / 0 |
| Markdown/code-fence leakage | 0 |
| Extra text outside JSON | 0 |
| Refusal/meta-response phrases | 0 |
| Prediction mojibake rows | 0 |
| Gold mojibake rows | 0 |

manual review：

| Label | Count |
|---|---:|
| pass | 14 |
| minor_issue | 2 |
| major_issue | 1 |
| uncertain | 0 |

关键发现：

- Row 66 的 sentence heuristic failure 是因为 `E. coli` 的标点导致，manual review 判断输出有效且忠实。
- Row 87 是真实 schema failure：
  - row: 87；
  - record id: `academic_paper:000458:8541ac16b79f`；
  - domain: `academic_paper`；
  - bucket: `medium`；
  - schema error: `key_points_len_7`。

Row 87 的内容大体忠实，JSON 可解析，但生成了 7 个 key points，不符合“正好 4 个”的输出契约。

中央大脑决定：

- Candidate A 选为本轮 final raw LoRA adapter；
- 不因为 held-out test 的 row 87 再训练 Candidate B；
- 原因是 test set 已经被使用，如果用这个 test 结果来调参或训练替代模型，会污染最终评估；
- 部署时必须使用 schema guard，不能直接裸用 raw adapter 输出。

Worker 008 通过，并完成 final model selection。

## 15. Worker 009：最终包装与本地部署说明

Worker 009 将 Candidate A 包装为最终 raw adapter，并创建本地推理 wrapper 和 runbook。

创建或更新：

```text
configs/final_candidate_a_inference.yaml
scripts/infer_clearread_candidate_a.py
docs/LOCAL_INFERENCE_RUNBOOK.md
reports/FINAL_MODEL_SELECTION_REPORT.md
models/final/clearread_llama31_8b_qlora_candidate_a/FINAL_ARTIFACT_MANIFEST.json
models/final/clearread_llama31_8b_qlora_candidate_a/README.md
logs/decisions/worker_009_package_artifact_and_deployment_notes.md
```

最终 metadata 目录：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\models\final\clearread_llama31_8b_qlora_candidate_a
```

该目录只保存 metadata，不复制 `.safetensors` 权重。

manifest 关键内容：

| 项目 | 值 |
|---|---|
| Artifact name | `clearread_llama31_8b_qlora_candidate_a` |
| Selection status | `selected_final_raw_adapter` |
| Base model | `unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit` |
| Training route | `Llama-3.1-8B-Instruct + SFT + QLoRA` |
| Adapter model SHA256 | `ef220721c78e72f41c3b14749f25a09ef39f6aaf351266b276cee41ec724cf92` |

schema guard 行为：

- valid output：默认只输出最终 JSON；
- parseable JSON 且 key_points 超过 4 个：截断到前 4 个，并在 debug 中标记 `schema_guard_action: truncated_key_points`；
- key_points 少于 4 个：返回 machine-readable error object；
- JSON parse error：返回 machine-readable error object；
- wrong keys/order/types：返回 machine-readable error object。

中央大脑验证：

- wrapper compile passed；
- wrapper dry-run passed；
- manifest JSON validation passed；
- manifest 中 adapter file hashes 全部匹配；
- approved split hashes 全部匹配；
- 用 non-test smoke data 做了一次 live wrapper check，结果：

```text
status: ok
schema_guard_action: none
input_id: smoke_test_10.jsonl:1
```

Worker 009 通过。训练、模型选择、包装阶段完成。

## 16. Git 与可复现性

项目分支：

```text
feature/ai-llama-lora-training
```

Worker 009 通过后，中央大脑最终 Git HEAD：

```text
fe793bf489708771a13e1678e31c3e47a04a0e60 docs(ai): approve final artifact packaging
```

Git 中只提交 Git-safe 文件，包括：

- scripts；
- configs；
- docs；
- reports；
- markdown logs；
- decision logs；
- small metadata。

明确不提交：

- full JSONL train/val/test data；
- teammate export JSONL；
- validation/test prediction JSONL；
- model weights；
- LoRA adapter `.safetensors`；
- checkpoints；
- optimizer states；
- Hugging Face cache；
- Unsloth cache；
- `.pt`、`.pth`、`.bin` 文件。

反复验证过：

```text
git ls-files 'ai/**/*.jsonl' -> empty
git ls-files 'ai/**/*.safetensors' 'ai/**/*.pt' 'ai/**/*.pth' 'ai/**/*.bin' -> empty
```

主要 Git 记录：

| Commit | Purpose |
|---|---|
| `cea843f` | 初始 branch safety setup |
| `1105b24` | stratified split profiling workflow |
| `704225f` | teammate export workflow |
| `9e1ff8a` | WSL environment documentation |
| `a118a70` | smoke training preparation |
| `6e6b7bf` / `919fc29` | smoke training result |
| `cdba362` | Candidate A QLoRA workflow |
| `2adc1f2` | Candidate A validation audit |
| `f53e1fe` | final Candidate A test evaluation |
| `3418651` | final Candidate A artifact packaging |
| `fe793bf` | central approval of final artifact packaging |

## 17. 过程中发现的问题与解决方式

| 问题或风险 | 出现阶段 | 解决方式 | 最终影响 |
|---|---|---|---|
| 拆分规则可能被误解为短中长均分 | 计划阶段 | 用户明确纠正，应保留真实分布；Worker 001 使用 `domain x natural_length_bucket` stratification | 最终 split 贴合真实 domain 和长度分布 |
| 原始数据集可能被误改 | 数据阶段 | 明确 `final_dataset_v1` 和 clean source 都只读，所有输出在 training 下生成 | 原始数据未修改 |
| Worker 可能污染中央记忆 | 流程设计 | 建立 central-brain/worker protocol 和 provisional memory 规则 | 中央大脑审核保持权威 |
| Git 可能误提交数据或权重 | Worker 000 及后续 | `.gitignore` 加保护，所有阶段运行 `git ls-files` 安全检查 | 未提交 JSONL 或模型二进制 |
| `rg` 在部分 worker 环境 access denied | 多个 worker | 改用 PowerShell/Python 检查 | 不阻塞 |
| Hugging Face 未登录 | Worker 003 | 使用 public Unsloth 4-bit model，官方 Meta 只作为 gated fallback | 不阻塞训练 |
| Flash Attention 2 broken | Worker 003 起 | 接受 xformers fallback，因为 CUDA 和 imports 通过 | 不阻塞 |
| Unsloth resolver 改成 torch 2.10.0+cu128 | Worker 003 | 通过 CUDA tensor、BF16、imports 验证后接受 | 环境可用 |
| PowerShell background WSL quoting 失败 | Worker 005/006 | 改为直接在 WSL 执行训练命令 | 训练成功 |
| `.gov` 附近 tokenizer decode spacing 导致 exact mismatch | Worker 006 preflight | 确认 labels 仍 parse JSON、非空、无 truncation | 不阻塞 |
| validation 中疑似 mojibake display | Worker 007 | 用 Python UTF-8 parsing 重查，判断是 terminal/rendering artifact | 没有数据损坏 |
| `E. coli` 导致 sentence heuristic false positive | Worker 008 | manual review 判断输出有效忠实 | 不算模型失败 |
| held-out test 一条输出 7 个 key points | Worker 008 | 不重新训练；最终 wrapper 增加 schema guard | raw adapter 选中，但部署必须 guard |
| 使用 test 结果再训练会污染评估 | Worker 008 | Candidate B 跳过，不基于 test 调参 | held-out evaluation 保持有效 |

## 18. 最终产物位置

final raw adapter：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\models\adapters\full_candidate_a_3epoch
```

final metadata：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\models\final\clearread_llama31_8b_qlora_candidate_a
```

final inference config：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\configs\final_candidate_a_inference.yaml
```

final inference wrapper：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\scripts\infer_clearread_candidate_a.py
```

local inference runbook：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\docs\LOCAL_INFERENCE_RUNBOOK.md
```

final model selection report：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\reports\FINAL_MODEL_SELECTION_REPORT.md
```

final test report：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\reports\FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md
```

本完整汇报文件：

```text
C:\Users\Aufb\Desktop\fit5120\iteration1\training\reports\CLEARREAD_LORA_TRAINING_FULL_SUMMARY.md
```

## 19. 当前最终状态

已经完成：

- 保护原始数据；
- 确定训练数据源；
- 统计 domain 和 length distribution；
- 创建 deterministic train/val/test/smoke split；
- 创建 teammate user/assistant exports；
- 创建并验证 WSL 训练环境；
- 准备 smoke training scripts 和 label mask；
- 完成 smoke training；
- 完成 Candidate A full training；
- 完成 validation quality audit；
- 完成 final held-out test evaluation；
- 选择 Candidate A 作为 final raw adapter；
- 创建 final inference wrapper 和 schema guard；
- 创建 final model manifest、runbook、selection report；
- Git-safe 文件已提交并推送；
- 模型权重、JSONL 数据、prediction outputs 未提交 Git。

本阶段未完成，也不属于当前阶段范围：

- backend/application integration；
- ClearRead app 如何调用本地 wrapper；
- teammate-facing handoff package；
- adapter 在普通 Git 之外的备份策略；
- wrapper error 的 controlled retry policy。

当前没有批准 Worker 010。下一阶段需要先由中央大脑和用户决定边界，再创建新的 work order。

## 20. 本文档依据的证据文件

本文档不是凭记忆重写，而是基于以下本地文件和记录整理：

```text
TRAINING_MEMORY.md
docs/CENTRAL_BRAIN_WORKER_PROTOCOL.md
docs/MASTER_TRAINING_PLAN.md
reports/SOURCE_DISTRIBUTION_PROFILE.md
data/splits/SPLIT_REPORT.md
reports/TEAMMATE_EXPORT_REPORT.md
reports/WSL_ENVIRONMENT_REPORT.md
reports/LABEL_MASK_SANITY_CHECK.md
reports/SMOKE_TRAINING_PREP_REPORT.md
reports/SMOKE_TRAINING_RUN_REPORT.md
reports/FULL_TRAIN_CANDIDATE_A_REPORT.md
reports/CANDIDATE_A_VALIDATION_QUALITY_REPORT.md
reports/FINAL_TEST_EVALUATION_CANDIDATE_A_REPORT.md
reports/FINAL_MODEL_SELECTION_REPORT.md
configs/train_llama31_8b_qlora_candidate_a.yaml
configs/final_candidate_a_inference.yaml
models/final/clearread_llama31_8b_qlora_candidate_a/FINAL_ARTIFACT_MANIFEST.json
logs/decisions/central_review_worker_001.md
logs/decisions/central_review_worker_002.md
logs/decisions/central_review_worker_003.md
logs/decisions/central_review_worker_004.md
logs/decisions/central_review_worker_005.md
logs/decisions/central_review_worker_006.md
logs/decisions/central_review_worker_007.md
logs/decisions/central_review_worker_008.md
logs/decisions/central_review_worker_009.md
```

本文档的结论以中央大脑审核通过的事实为准，而不是单独以 worker 的 provisional report 为准。
