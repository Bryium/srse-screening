from z3 import Int, Solver, And, Or, sat

def find_pythagorean_triples(n_triples=5, bound=100):
    a, b, c = Int("a"), Int("b"), Int("c")
    s = Solver()

    s.add(a >= 1, b >= 1, c >= 1)
    s.add(a <= bound, b <= bound, c <= bound)
    s.add(a * a + b * b == c * c)
    s.add(a < b)

    triples = []
    for i in range(n_triples):
        if s.check() != sat:
            print("no more solutions")
            break
        m = s.model()
        triple = (m[a].as_long(), m[b].as_long(), m[c].as_long())
        triples.append(triple)
        print(f"  found: {triple}")
        s.add(Or(a != m[a], b != m[b], c != m[c]))
    return triples


def test_pythagoras_with_z3():
    triples = find_pythagorean_triples(n_triples=5, bound=50)
    for a, b, c in triples:
        assert a * a + b * b == c * c
        assert c > a and c > b
    print(f"\nall {len(triples)} triples satisfy the property")


if __name__ == "__main__":
    test_pythagoras_with_z3()