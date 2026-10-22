import copy, random
random.seed(5)
for _ in range(20000):
    s = set(); ops = []
    hi = random.choice([8, 16, 40, 70, 130, 260, 600])
    for _ in range(random.randint(1, 60)):
        r = random.random()
        if r < 0.65:
            n = random.randrange(hi); s.add(n); ops.append(f'a{n}')
        elif r < 0.85 and s:
            n = random.choice(list(s)) if random.random() < 0.8 else random.randrange(hi); s.discard(n); ops.append(f'd{n}')
        elif r < 0.92:
            s = copy.deepcopy(s); ops.append('k')
        else:
            s.clear(); ops.append('c')
    print(' '.join(ops) + '\t' + repr(list(s)))
