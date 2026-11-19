import json, random, shlex
random.seed(11)
alpha = ['a', 'b', ' ', ' ', '"', "'", '\\', '\t', '\n', '$', 'x', '{', '}', ':', 'é']
seen = set()
for _ in range(20000):
    s = ''.join(random.choice(alpha) for _ in range(random.randint(0, 12)))
    if s in seen:
        continue
    seen.add(s)
    try:
        ans = shlex.split(s)
    except ValueError as e:
        ans = str(e)
    print(json.dumps([s, ans]))
