import json

with open("data/eval_results.json", encoding="utf-8") as f:
    data = json.load(f)

# Sample across all categories
sample_ids = [1, 2, 4, 11, 14, 17, 21, 24, 31, 32, 42, 46, 50]
for sid in sample_ids:
    item = next(d for d in data if d["id"] == sid)
    print(f"\n=======================================================")
    print(f"Q{item['id']} [{item['category']}]: {item['question']}")
    print(f"Top Matches: {item['top_matches']}")
    print(f"Score: {item['top_scores']}")
    print(f"Answer:\n{item['answer']}")
