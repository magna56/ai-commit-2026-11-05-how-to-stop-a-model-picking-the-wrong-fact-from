"""Keep look-alike passages out of a long prompt, and test whether they were fooling your model.

A model answering from a long prompt leans toward the passage that best matches the question's
wording. A passage that echoes the question, such as last year's version of the same policy, can
beat the true answer. Two liftable pieces:

  assemble_context()  drops superseded versions, out-of-scope sources and near-duplicates
                      before they reach the prompt
  sweep()             a length x look-alike test you point at your own model call

`toy_model` is a stand-in for a real call so this runs with no API key: it picks the passage
whose words best match the question, plus noise. Its numbers show the harness working, not how
any real model behaves. Swap in your client: ask(prompt, question) -> answer text.
Run: python3 code_example.py
"""
import random
import re

LENGTHS = [500, 4000, 16000, 64000]   # approximate prompt tokens; add the length your app really sends
TRIALS = 20                           # per cell; 10 is too few to trust a 1-in-10 difference
NEAR_DUP = 0.6                        # word-overlap ratio above which two chunks count as copies

STOP = set("a an the of to in on and or is was were be it its that this my me i your you their "
           "them they what which who how did do does for with from at by as if not".split())


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP}


def overlap(a, b):
    wa, wb = words(a), words(b)
    return len(wa & wb) / max(1, min(len(wa), len(wb)))


def assemble_context(chunks, scope, budget_tokens):
    """chunks: dicts with text, doc_id, version, source. Returns the texts to put in the prompt.

    Order matters: drop by metadata first (cheap and exact), then by similarity (fuzzy)."""
    newest = {}
    for c in chunks:
        if c["source"] not in scope:          # a forwarded email is not the policy, however alike
            continue
        if c["doc_id"] not in newest or c["version"] > newest[c["doc_id"]]["version"]:
            newest[c["doc_id"]] = c           # keep only the current version of each document
    kept, used = [], 0
    for c in newest.values():
        if any(overlap(c["text"], k) > NEAR_DUP for k in kept):
            continue                          # a second copy adds a rival, never information
        cost = len(c["text"]) // 4            # rough tokens; use your tokenizer's count if you have it
        if used + cost > budget_tokens:
            break
        kept.append(c["text"])
        used += cost
    return kept


FILLER = ["The team moved the weekly sync to Thursdays after the holiday schedule changed.",
          "Our office plants survived the winter because someone finally fixed the heating.",
          "The new laptop shipped with a keyboard layout nobody on the floor could use.",
          "Lunch orders now go through a shared sheet that nobody remembers to update.",
          "The parking garage closes early on Fridays, which surprised the night shift.",
          "Somebody labeled every cable in the server closet, and nobody knows who."]


def build_prompt(needle, lookalikes, tokens, depth, seed):
    """Unrelated filler up to `tokens`, the true passage at `depth`, look-alikes at random spots."""
    rnd = random.Random(seed)
    passages = [rnd.choice(FILLER) for _ in range(max(1, tokens // 16))]
    passages.insert(int(depth * len(passages)), needle)
    for la in lookalikes:
        passages.insert(rnd.randrange(len(passages) + 1), la)
    return "\n\n".join(passages)


def sweep(ask, needle, answer_word, lookalikes, question):
    """Accuracy per (length, with or without look-alikes). The two rows are the whole test."""
    table = {}
    for with_la in (False, True):
        for tokens in LENGTHS:
            hits = 0
            for i in range(TRIALS):
                prompt = build_prompt(needle, lookalikes if with_la else [], tokens,
                                      (i + 0.5) / TRIALS, seed=i)
                hits += answer_word in ask(prompt, question).lower()
            table[(with_la, tokens)] = hits / TRIALS
    return table


def toy_model(prompt, question, noise=0.08, _rnd=random.Random(7)):
    # Stand-in: answer with the passage that best matches the question's words, plus noise.
    return max(prompt.split("\n\n"), key=lambda p: overlap(question, p) + _rnd.gauss(0, noise))


def show(title, table):
    print(title)
    print("  tokens        " + "".join(f"{t:>8}" for t in LENGTHS))
    for with_la, label in ((False, "clean"), (True, "look-alikes")):
        print(f"  {label:<14}" + "".join(f"{table[(with_la, t)]:>8.0%}" for t in LENGTHS))


def main():
    needle = ("Looking back, the most useful thing my old manager taught me was to write the "
              "rollback plan before writing the migration.")
    lookalikes = ["My former boss said the most useful thing she taught me was to write tests first.",
                  "The most useful thing a former boss taught my friend was to write the alert first.",
                  "Another former boss taught me the most useful thing: write the deploy script first.",
                  "A former boss once taught me that the most useful thing is writing the changelog."]
    echo_q = "What was the most useful thing the author's former boss taught them?"
    show("Question that echoes the look-alikes (toy model):",
         sweep(toy_model, needle, "rollback", lookalikes, echo_q))
    specific_q = "What did the old manager say to plan before a migration?"
    show("Question naming what only the true passage has (toy model):",
         sweep(toy_model, needle, "rollback", lookalikes, specific_q))

    print("\nassemble_context on six retrieved chunks:")
    chunks = [
        {"doc_id": "refunds", "version": 3, "source": "policy", "text": "Refunds are allowed within 30 days of delivery."},
        {"doc_id": "refunds", "version": 2, "source": "policy", "text": "Refunds are allowed within 14 days of purchase."},
        {"doc_id": "fwd-17", "version": 1, "source": "email", "text": "FYI refunds are allowed within 60 days for VIPs."},
        {"doc_id": "faq", "version": 5, "source": "policy", "text": "Refunds are allowed within 30 days of delivery, as stated."},
        {"doc_id": "ship", "version": 1, "source": "policy", "text": "Orders ship within two business days."},
        {"doc_id": "faq-old", "version": 1, "source": "wiki", "text": "Refunds within 14 days, no exceptions."},
    ]
    kept = assemble_context(chunks, scope={"policy"}, budget_tokens=2000)
    print(f"  kept {len(kept)} of {len(chunks)}; refund rules left in the prompt:")
    for t in kept:
        print("   -", t)


if __name__ == "__main__":
    main()
