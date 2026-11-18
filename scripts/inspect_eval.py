import json

with open("data/eval_results.json", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total: {len(data)}")
missed = [d for d in data if not d.get("entity_recalled")]
print(f"Missed entity count: {len(missed)}")
for m in missed:
    print(f"\n--- Q{m['id']}: {m['question']} ---")
    print("Top matches:", m["top_matches"])
    print("Answer snippet:", m["answer"][:250])
