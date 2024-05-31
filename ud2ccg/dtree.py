import networkx as nx


class DTree:
    def __init__(self, dtree, eud_heads_to_deps=None, eud_deps_to_heads=None):
        self.dtree = dtree
        self.eud_heads_to_deps = eud_heads_to_deps
        self.eud_deps_to_heads = eud_deps_to_heads

    @staticmethod
    def from_sentence(sentence):
        # initialize dependency tree
        dtree = nx.DiGraph()

        # create a dummy root node
        dtree.add_node(0, form="ROOT", upos="ROOT", pron_type=None, deprel=None, head=None)

        # mappings for enhanced dependencies
        # value is a tuple ({index}, {eud}), for example: (5, nsubj:xsubj)
        eud_heads_to_deps = dict()
        eud_deps_to_heads = dict()

        # add nodes to dtree
        for token in sentence:
            # remove sub-dependency type (e.g., nmod:poss --> nmod)
            # exception: acl:relcl, advcl:relcl
            deprel = token.deprel
            if deprel not in ["acl:relcl", "advcl:relcl"]:
                deprel = token.deprel.split(":")
                deprel = deprel[0]

            # extract PronType
            feats = token.feats
            pron_type = None
            if feats != "_":
                parts = feats.split("|")
                for part in parts:
                    if part.startswith("PronType="):
                        pron_type = part[9:]
                        break

            # extract EUD
            eud = token.eud
            if eud != "_":
                parts = eud.split("|")
                for part in parts:
                    first_colon_idx = part.index(":")
                    eud_head = int(part[:first_colon_idx])
                    eud_deprel = part[first_colon_idx+1:]

                    # extract enhanced dependencies only
                    if eud_head not in eud_heads_to_deps:
                        eud_heads_to_deps[eud_head] = list()
                    eud_heads_to_deps[eud_head].append((token.idx, eud_deprel))

                    if token.idx not in eud_deps_to_heads:
                        eud_deps_to_heads[token.idx] = list()
                    eud_deps_to_heads[token.idx].append((eud_head, eud_deprel))

            dtree.add_node(
                token.idx, form=token.form, upos=token.upos, pron_type=pron_type, deprel=deprel, head=token.head
            )

        # add edges to dtree
        for token in sentence:
            dtree.add_edge(token.head, token.idx)

        return DTree(dtree, eud_heads_to_deps, eud_deps_to_heads)

    def get_root(self):
        return [n for n, d in self.dtree.in_degree() if d == 0][0]

    def get_dtree_node(self, idx):
        return self.dtree.nodes[idx]

    def get_children(self, idx, only_edges=None):
        if only_edges is None:
            return sorted(list(self.dtree.successors(idx)))
        else:
            valid_children = list()
            for child in self.dtree.successors(idx):
                this_deprel = self.get_deprel(child)
                if this_deprel in only_edges:
                    valid_children.extend([child])
            return sorted(set(valid_children))

    # if node at this index has any children
    def has_children(self, idx):
        if self.dtree.out_degree(idx) == 0:
            return False
        return True

    def get_deprel(self, idx):
        return self.dtree.nodes[idx]['deprel']

    def set_deprel(self, idx, new_deprel):
        self.dtree.nodes[idx]['deprel'] = new_deprel

    def get_form(self, idx):
        return self.dtree.nodes[idx]['form']

    def get_pos(self, idx):
        return self.dtree.nodes[idx]['upos']

    def get_head(self, idx):
        return self.dtree.nodes[idx]['head']

    def set_head(self, idx, new_head):
        self.dtree.nodes[idx]['head'] = new_head

    def get_subdtree(self, nodes):
        return DTree(self.dtree.subgraph(nodes))

    def get_eud_children(self, idx, eud_only=False):
        if not eud_only:
            if idx in self.eud_heads_to_deps:
                return self.eud_heads_to_deps[idx]
        else:
            ud_children = self.get_children(idx)
            if idx in self.eud_heads_to_deps:
                all_children = self.eud_heads_to_deps[idx]

                filtered_children = list()
                for child in all_children:
                    if child[0] not in ud_children:
                        filtered_children.append(child)

                return filtered_children
        return None

    def get_eud_parent(self, idx):
        if idx in self.eud_deps_to_heads:
            return self.eud_deps_to_heads[idx]
        return None

    def add_eud(self, head_idx, dep_idx, eud_deprel):
        if head_idx not in self.eud_heads_to_deps:
            self.eud_heads_to_deps[head_idx] = list()
        self.eud_heads_to_deps[head_idx].append((dep_idx, eud_deprel))

        if dep_idx not in self.eud_deps_to_heads:
            self.eud_deps_to_heads[dep_idx] = list()
        self.eud_deps_to_heads[dep_idx].append((head_idx, eud_deprel))

    def to_conllu(self):
        template = '{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'
        conllu_str = ''
        for i in range(1, self.dtree.number_of_nodes()):
            node = self.get_dtree_node(i)
            conllu_str += template.format(i,
                                          node['form'],
                                          '_',
                                          node['upos'],
                                          '_',
                                          '_',
                                          node['head'],
                                          node['deprel'],
                                          '_',
                                          '_'
                                          )

        return conllu_str
