# Source Assessment: General Knowledge / Background Encyclopedia

## Recommendation

Do **not** use `Salesforce/wikitext` as the primary source for this dataset build.

Use **`wikimedia/wikipedia`** instead.

## Why `Salesforce/wikitext` is not the best fit

`Salesforce/wikitext` is a strong **language-modeling benchmark**, but it is a weak fit for your final goal:

1. It is organized as massive `text` rows for LM training, not as a convenient article dataset with stable provenance fields on each row.
2. In practice, the data contains article headings, section markers, raw-token formatting, and article fragments that need reconstruction/cleanup before they become student-facing reading samples.
3. The Hugging Face page only exposes a single `text` field for the rows, which makes attribution and source tracking weaker than a dataset that already gives article title and URL.
4. Your requirement is not “general Wikipedia-like text” in the abstract; it is **150 complete, understandable, single-source encyclopedia/background passages**. `wikitext` makes that harder than necessary.

Conclusion: `wikitext` is usable only if you must stay with that dataset, but it is **not the simplest or safest choice** for this task.

## Recommended source: `wikimedia/wikipedia`

Recommended dataset:

- Hugging Face dataset: `wikimedia/wikipedia`
- Suggested English config: `20231101.en`
- Real upstream source: Wikimedia / Wikipedia dumps

Why this is better:

1. Each row is one cleaned Wikipedia article.
2. The dataset is already designed around article-level content, which matches your single-source requirement.
3. It is directly callable from Python with `datasets.load_dataset(...)`.
4. It exposes article-level provenance such as title / URL / ID, which is much better for traceability.
5. It is much easier to extract 250–1200 word coherent excerpts from article leads.

## Optional richer source

There is also `wikimedia/structured-wikipedia`, which is newer and more structured.

It is attractive because it includes parsed article structure, but for this project it is **not simpler** than `wikimedia/wikipedia`. The extra structure is useful, but it also adds parsing complexity that you do not need for a 150-row SFT dataset.

## License note

Wikipedia/Wikimedia text is open-license content, but it is **not public domain**.

You must preserve the fact that it comes from Wikipedia/Wikimedia and keep attribution/share-alike obligations in mind when documenting or redistributing the resulting dataset.

For that reason, every extracted sample in this pipeline keeps source metadata such as:

- source dataset
- source config
- article title
- article URL
- article ID

## Final recommendation for this task

If the task is “学科通识与背景百科” and the goal is 150 coherent student-readable source passages, the best practical choice is:

- **Use `wikimedia/wikipedia`**
- **Do not use `Salesforce/wikitext` unless you have a special reason**
