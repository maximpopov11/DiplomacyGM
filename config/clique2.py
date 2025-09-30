import networkx as nx

def load_graph_from_file(filename):
    G = nx.Graph()
    with open(filename, 'r') as file:
        for line in file:
            a, b = line.strip().split(',')
            G.add_edge(a, b)
    return G

def find_cliques(G, min_size=4):
    return [clique for clique in nx.find_cliques(G) if len(clique) >= min_size]

def find_induced_4_cycles(G):
    cycles = set()
    nodes = list(G.nodes())
    for a in nodes:
        for b in G.neighbors(a):
            for c in G.neighbors(b):
                if c == a or c in G.neighbors(a):
                    continue
                for d in G.neighbors(c):
                    if d == b or d in G.neighbors(b) or d not in G.neighbors(a):
                        continue
                    # Check that A–C and B–D do NOT exist
                    if not G.has_edge(a, c) and not G.has_edge(b, d):
                        # Sort to avoid duplicates
                        cycle = tuple(sorted([a, b, c, d]))
                        cycles.add(cycle)
    return list(cycles)

def main(filename):
    G = load_graph_from_file(filename)
    cliques = find_cliques(G)
    cycles = find_induced_4_cycles(G)

    print(f"\nCliques of size 4 or more:")
    for clique in cliques:
        print(clique)

    print(f"\nInduced 4-cycles (A–B–C–D–A with no A–C or B–D):")
    for cycle in cycles:
        print(cycle)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python script.py <filename>")
    else:
        main(sys.argv[1])

