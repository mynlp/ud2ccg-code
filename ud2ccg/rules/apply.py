from ud2ccg.rules import rules

RULES = {
    # basic
    'default': rules.default,
    'token': rules.token,
    'root': rules.root,
    # core arguments
    'ccomp': rules.comp,
    'xcomp': rules.comp,
    'csubj': rules.comp,
    'scop': rules.scop,
    'obl-ap': rules.oblap,
    # function words
    'mark': rules.mark,
    'case': rules.case,
    'cop': rules.scop,
    'det': rules.modifier,
    'aux': rules.modifier,
    'punct': rules.punct,
    'punct2': rules.modifier,
    # modifiers
    'advcl': rules.cmod,
    'acl': rules.cmod,
    'obl': rules.modifier,
    'amod': rules.modifier,
    'nmod': rules.nmod,
    'advmod': rules.modifier,
    'nummod': rules.modifier,
    'compound': rules.modifier,
    'fixed': rules.modifier,
    'flat': rules.modifier,
    'list': rules.modifier,
    'goeswith': rules.modifier,
    # coordination
    'conj': rules.conj,
    'conj-sent': rules.conj,
    'cc': rules.cc,
    # relative clause
    'advcl:relcl': rules.relcl,
    'acl:relcl': rules.relcl,
    # ref
    'ref-': rules.ref,
    # unclear
    'dep': rules.modifier,
    'clf': rules.modifier,
    'appos': rules.modifier,
    'parataxis': rules.modifier,
    'vocative': rules.modifier,
    'discourse': rules.modifier,
    'dislocated': rules.modifier,
    'reparandum': rules.modifier
}


# input should be subdtree and subbtree
def apply_rules(subbtree, dtree, subdtree_root_cat=None):
    # traverse subbtree top-down
    subbtree_root = subbtree.get_root()
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)

    # assign category to subbtree_root_node if it exists
    if subdtree_root_cat is not None:
        subbtree_root_node['category'] = subdtree_root_cat

    # apply appropriate rules
    def _apply_rules(subbtree_root, subbtree, dtree):
        subbtree_root_node = subbtree.get_btree_node(subbtree_root)
        subbtree_root_node_type = subbtree_root_node['node_type']

        # decide which rule to apply to current subtree
        if subbtree_root_node_type == 'deprel':
            subbtree_root_node_deprel = subbtree_root_node['deprel']
            if subbtree_root_node_deprel in RULES:
                rule = RULES[subbtree_root_node_deprel]
            elif 'ref-' in subbtree_root_node_deprel:
                rule = RULES['ref-']
            else:
                rule = RULES['default']
        else:
            rule = RULES['token']

        # call function
        rule(subbtree_root, subbtree, dtree)

        # recursion
        subbtree_children = subbtree.get_children(subbtree_root)
        for subbtree_child in subbtree_children:
            _apply_rules(subbtree_child, subbtree, dtree)

    _apply_rules(subbtree_root, subbtree, dtree)
