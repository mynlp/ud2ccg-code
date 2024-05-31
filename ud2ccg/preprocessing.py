# identify coordination between sentences (conj-sent)
# change conj to conj-sent if:
# - both the head of the dependent of conj have its own subject, or
# - the dependent does not share a subject with the head (via EUD)
def preprocess_conj(dtree):
    for node in dtree.dtree.nodes():
        if dtree.get_deprel(node) in ['conj']:
            to_convert = False

            # head of the current node in UD tree
            head = dtree.get_head(node)

            # check if head has a subject child
            head_children = dtree.get_children(head, only_edges='nsubj')
            if head_children and len(head_children) > 0:
                nsubj_of_head = head_children[0]

                # check if dependent has a subject child
                node_children = dtree.get_children(node, only_edges='nsubj')
                if node_children and len(node_children) > 0:
                    to_convert = True
                else:
                    # check EUD dependents of node
                    eud_deps = dtree.get_eud_children(node)
                    if eud_deps and len(eud_deps) > 0:
                        to_convert = True
                        for eud_dep in eud_deps:
                            if eud_dep[0] == nsubj_of_head:
                                to_convert = False
                    else:
                        to_convert = True

            if to_convert:
                dtree.set_deprel(node, 'conj-sent')


# change the basic dependency label of relative pronoun (which has enhanced deprel "ref") into
# label of the form ref-XXX (where XXX can be nsubj/iobj/obj/etc.)
def preprocess_ref(dtree):
    for node in dtree.eud_deps_to_heads:
        node_eud_heads = dtree.eud_deps_to_heads[node]

        is_ref = False
        for node_eud_head in node_eud_heads:
            node_eud_head_deprel = node_eud_head[1]
            if node_eud_head_deprel == 'ref':
                is_ref = True

        if is_ref:
            deprel = dtree.get_deprel(node)
            new_deprel = 'ref-' + deprel
            dtree.set_deprel(node, new_deprel)

            # rule for cases like "whose", "whatever", etc.
            # change the deprel of head to ref-XXX also
            if deprel in ['nmod']:
                head = dtree.get_head(node)
                head_deprel = dtree.get_deprel(head)
                new_head_deprel = 'ref-' + head_deprel
                dtree.set_deprel(head, new_head_deprel)


# change the dependency label 'obl' to 'obl-ap' if:
# - there exists a parallel UP argument dependency (e.g., A0|1|2|3|4)
# - this head of the oblique nominal phrase has a 'case' dependent
def preprocess_ap(dtree, up_sentence):
    for node in dtree.dtree.nodes():
        if dtree.get_deprel(node) in ['obl', 'nmod']:
            # head of the current node in UD tree
            ud_head = dtree.get_head(node)

            # check if current node has a 'case' child
            has_case = False
            node_children = dtree.get_children(node, only_edges='case')
            if node_children and len(node_children) > 0:
                has_case = True

            # check in up_sentence if there is an argument dependency
            # from ud_head to node
            to_change_label = False
            if has_case:
                for up_token in up_sentence:
                    pred_idx = up_token.idx
                    argheads = up_token.argheads

                    if pred_idx == ud_head:
                        if argheads != "_":
                            parts = argheads.split("|")
                            for part in parts:
                                first_colon_idx = part.index(":")
                                label = part[:first_colon_idx]
                                arg_idx = int(part[first_colon_idx + 1:])

                                if arg_idx == node:
                                    if label in ['A0', 'A1', 'A2', 'A3', 'A4',
                                                 'ARG0', 'ARG1', 'ARG2', 'ARG3', 'ARG4']:
                                        to_change_label = True

            if to_change_label:
                dtree.set_deprel(node, "obl-ap")
