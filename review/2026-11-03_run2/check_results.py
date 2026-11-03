import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
def walk(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)
S = list(walk(d))
print("top-level keys:", list(d))
print("strings:", len(S), "non-empty:", sum(1 for s in S if s.strip()))
for s in S[:3]:
    print("-", s[:70].replace("\n", " "))
