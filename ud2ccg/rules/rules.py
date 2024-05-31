import random
from ud2ccg.cat import Category, VariableCategory, Functor, Index
from ud2ccg.ccg_rules import solve_functor


# for ablation study
APPLY_COINDEXATION = True
APPLY_COINDEXATION_COP = True
APPLY_COINDEXATION_COMP = True
APPLY_COINDEXATION_RELCL = True


# default rule:
# - if subbtree_root is not assigned a category, assign to it a VariableCategory
# - assign a variable category to the child with 'category_type' == 'argument'
# - solve for the other functor child using application rules
def default(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_cat = subbtree_root_node['category']

    if subbtree_root_cat is None:
        subbtree_root_node['category'] = VariableCategory()
        subbtree_root_cat = subbtree_root_node['category']

    children = subbtree.get_children(subbtree_root)

    # assign a variable category to the child with 'category_type' == 'argument'
    argument_cat = None
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'argument':
            child_node['category'] = VariableCategory()
            argument_cat = child_node['category']

    # solve for the other functor child
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'functor':
            # identify slash direction
            head_idx = subbtree_root_node['head_idx']
            dep_idx = subbtree_root_node['dep_idx']

            if head_idx > dep_idx:
                slash = '\\'
            else:
                slash = '/'

            child_node['category'] = solve_functor(res=subbtree_root_cat,
                                                   arg=argument_cat,
                                                   slash=slash)


def token(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_idx = subbtree_root_node['idx']

    dtree_node = dtree.get_dtree_node(subbtree_root_idx)
    dtree_node_upos = dtree_node['upos']
    dtree_node_deprel = dtree_node['deprel']

    new_cat = None

    # rule that assigns NP to tokens of the following POS tags
    if dtree_node_upos in ['NOUN', 'PRON', 'PROPN', 'NUM', 'SYM', 'X']:
        new_cat = Category.parse('NP')

    # rule that assigns NP to non-noun tokens acting as nsubj/obj/iobj
    elif dtree_node_upos in ['DET', 'ADJ', 'ADV']:
        if dtree_node_deprel in ['nsubj', 'obj', 'iobj', 'obl', 'obl-ap', 'nmod']:
            new_cat = Category.parse('NP')

    # assign new_cat to the token in question (subbtree_root/dtree_node)
    if new_cat is not None:
        subbtree_root_cat = subbtree_root_node['category']
        if subbtree_root_cat is None:
            subbtree_root_node['category'] = new_cat
        elif subbtree_root_cat.is_variable:
            subbtree_root_cat.update(new_cat)


# rules for ROOT of sentence (may not always true)
# - if dep root is not a noun with nsubj/csubj → category S
# - if dep root is not a noun without nsubj/csubj → category S|NP
# - if dep root is noun with cop → category S
# - if dep root is noun without cop -> category NP
# - other cases?
def root(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)

    children = subbtree.get_children(subbtree_root)
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] != 'ROOT':
            # identify the index of the dependent of root
            dep_idx = subbtree_root_node['dep_idx']

            # check the dependents (in dtree) of the token at this index
            has_nsubj = False
            has_expl = False
            has_cop = False
            for dep_child in dtree.get_children(dep_idx):
                #if dep_child in subbtree.get_leaf_node_indices(subbtree_root):
                dep_child_deprel = dtree.get_deprel(dep_child)
                if dep_child_deprel in ['nsubj', 'csubj']:
                    has_nsubj = True
                elif dep_child_deprel in ['expl']:
                    has_expl = True
                elif dep_child_deprel in ['cop']:
                    has_cop = True

            dep_upos = dtree.get_pos(dep_idx)
            if not has_nsubj:
                if dep_upos in ['NOUN', 'PRON', 'PROPN', 'NUM', 'SYM']:
                    if has_expl or has_cop:
                        child_node['category'] = Category.parse('S')
                    else:
                        child_node['category'] = Category.parse('NP')
                else:
                    if has_expl:
                        child_node['category'] = Category.parse('S')
                    else:
                        # in case of 1-node dtree with just PUNCT/INTJ/X
                        if len(dtree.get_children(dep_idx)) == 0 and dep_upos in ['PUNCT', 'INTJ', 'X']:
                            child_node['category'] = Category.parse('NP')
                        else:
                            child_node_cat = Category.parse('S|NP')

                            # adjust index of argument_cat so that it's the same as its result category
                            child_node_cat.index = child_node_cat.left.index

                            child_node['category'] = child_node_cat
            else:
                child_node['category'] = Category.parse('S')
        else:
            child_node['category'] = Category.parse('ROOT')


def punct(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_cat = subbtree_root_node['category']

    children = subbtree.get_children(subbtree_root)
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'argument':
            child_node['category'] = subbtree_root_cat
        else:
            form = child_node['name']
            if form in [',', '，', '、', '،', '՝', '/', '\\']:
                child_node['category'] = Category.parse(',')
            elif form in [':', '：']:
                child_node['category'] = Category.parse(':')
            elif form in [';', '；', '؛']:
                child_node['category'] = Category.parse(';')
            elif form in ['.', '．', '。', '!', '！', '?', '？', '؟', '।', '۔', '։', '።', '¿', '՞', '՛', '¡', '՜']:
                child_node['category'] = Category.parse('.')
            elif form in ['...', '…']:
                child_node['category'] = Category.parse(':')   # ellipsis
            else:   # should only be used for things at the end like "!!!!!!"
                child_node['category'] = Category.parse('.')


# a general rule for modifiers (amod, nmod, advmod, nummod, [...])
# the child with 'category_type' == 'argument' should have the same category as subbtree_root
def modifier(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_cat = subbtree_root_node['category']

    if subbtree_root_cat is None:
        subbtree_root_node['category'] = VariableCategory()
        subbtree_root_cat = subbtree_root_node['category']

    children = subbtree.get_children(subbtree_root)

    # the child with 'category_type' == 'argument' should have the same category as subbtree_root
    argument_cat = None
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'argument':
            child_node['category'] = subbtree_root_cat
            argument_cat = child_node['category']

    # solve for the other functor child
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'functor':
            # identify slash direction
            head_idx = subbtree_root_node['head_idx']
            dep_idx = subbtree_root_node['dep_idx']

            if head_idx > dep_idx:
                slash = '/'
            else:
                slash = '\\'

            functor_cat = solve_functor(res=subbtree_root_cat,
                                        arg=argument_cat,
                                        slash=slash)

            # a modifier should have category of type (X_i|X_i)_j
            # where the index of the entire category is different from the index
            # of result and argument categories
            functor_cat.index = Index()

            child_node['category'] = functor_cat


# basic rules for ccomp:
# - set argument as S    if it has a nsubj child
# - set argument as S|NP if it doesn't have a nsubj child
# - set argument as NP   if it doesn't have a nsubj/cop child and its head is a noun
def comp(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_cat = subbtree_root_node['category']

    if subbtree_root_cat is None:
        subbtree_root_node['category'] = VariableCategory()
        subbtree_root_cat = subbtree_root_node['category']

    children = subbtree.get_children(subbtree_root)

    # assign category to argument according to the rules above
    argument_cat = None
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'argument':
            # identify the index of the dependent of ccomp
            dep_idx = subbtree_root_node['dep_idx']

            # check the dependents (in dtree) of the token at this index
            has_nsubj = False
            has_cop = False
            for dep_child in dtree.get_children(dep_idx):
                if dep_child in subbtree.get_leaf_node_indices(subbtree_root):
                    dep_child_deprel = dtree.get_deprel(dep_child)
                    if dep_child_deprel in ['nsubj', 'csubj']:
                        has_nsubj = True
                    elif dep_child_deprel in ['cop']:
                        has_cop = True

            if has_nsubj:
                argument_cat = Category.parse('S')
            else:
                dep_upos = dtree.get_pos(dep_idx)
                if dep_upos in ['NOUN', 'PRON', 'PROPN', 'NUM', 'SYM'] and not has_cop:
                    argument_cat = Category.parse('NP')
                else:
                    argument_cat = Category.parse('S|NP')

                    # adjust index of argument_cat so that it's the same as its result category
                    argument_cat.index = argument_cat.left.index

                    # adjust index of argument_cat according to EUD
                    if APPLY_COINDEXATION_COMP:
                        eud_deps = dtree.get_eud_children(dep_idx, eud_only=True)
                        if eud_deps is not None:
                            # identify core eud dependent
                            core_eud_dep_idx = None
                            core_eud_deprel = None
                            for eud_dep in eud_deps:
                                eud_dep_idx = eud_dep[0]
                                eud_deprel = eud_dep[1]
                                eud_deprel = eud_deprel.split(':')
                                eud_deprel = eud_deprel[0]

                                if ':' in eud_deprel:
                                    eud_first_colon_idx = eud_deprel.index(":")
                                    eud_deprel = eud_deprel[:eud_first_colon_idx]

                                if eud_deprel in ['nsubj:xsubj', 'nsubj', 'obj', 'iobj']:
                                    core_eud_dep_idx = eud_dep_idx
                                    core_eud_deprel = eud_deprel
                                    break

                            # assign index of core eud dependent to argument of argument_cat
                            if core_eud_dep_idx is not None:
                                argument_cat.right.index = str(core_eud_dep_idx) + ':t'

            child_node['category'] = argument_cat

    # solve for the other functor child
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'functor':
            # identify slash direction
            head_idx = subbtree_root_node['head_idx']
            dep_idx = subbtree_root_node['dep_idx']

            if head_idx > dep_idx:
                slash = '\\'
            else:
                slash = '/'

            child_node['category'] = solve_functor(res=subbtree_root_cat,
                                                   arg=argument_cat,
                                                   slash=slash)


# basic rules for scop (same as ccomp, but with coindexation by default):
# - set argument as S    if it has a nsubj child
# - set argument as S|NP if it doesn't have a nsubj child
# - set argument as NP   if it doesn't have a nsubj/cop child and its head is a noun
def scop(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_cat = subbtree_root_node['category']

    if subbtree_root_cat is None:
        subbtree_root_node['category'] = VariableCategory()
        subbtree_root_cat = subbtree_root_node['category']

    children = subbtree.get_children(subbtree_root)

    # assign category to argument according to the rules above
    argument_cat = None
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'argument':
            # identify the index of the head of scop
            head_idx = subbtree_root_node['head_idx']

            # check the dependents (in dtree) of the token at this index
            # only consider nsubj/cop child that is a descendant of the dependent of scop
            has_nsubj = False
            has_cop = False
            for dep_child in dtree.get_children(head_idx):
                if dep_child in subbtree.get_leaf_node_indices(child):
                    dep_child_deprel = dtree.get_deprel(dep_child)
                    if dep_child_deprel in ['nsubj', 'csubj']:
                        has_nsubj = True
                    elif dep_child_deprel in ['cop']:
                        has_cop = True

            if has_nsubj:
                argument_cat = Category.parse('S')
            else:
                dep_upos = dtree.get_pos(head_idx)
                if dep_upos in ['NOUN', 'PRON', 'PROPN', 'NUM', 'SYM'] and not has_cop:
                    argument_cat = Category.parse('NP')
                else:
                    argument_cat = Category.parse('S|NP')

                    # adjust index of argument_cat so that it's the same as its result category
                    argument_cat.index = argument_cat.left.index

                    # adjust index of argument_cat's NP argument so that it's the same as
                    # the NP argument of subbtree_root_cat:
                    # - copula = (S|N_i)|(S|NP_i)
                    # - argument_cat = S|NP_i
                    if APPLY_COINDEXATION_COP:
                        if isinstance(subbtree_root_cat, Functor):
                            argument_cat.right.index = subbtree_root_cat.right.index

            child_node['category'] = argument_cat

    # solve for the other functor child
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'functor':
            # identify slash direction
            head_idx = subbtree_root_node['head_idx']
            dep_idx = subbtree_root_node['dep_idx']

            if head_idx > dep_idx:
                slash = '/'
            else:
                slash = '\\'

            child_node['category'] = solve_functor(res=subbtree_root_cat,
                                                   arg=argument_cat,
                                                   slash=slash)


# basic rules for mark:
# - set argument as S    if it has a nsubj child
# - set argument as S|NP if it doesn't have a nsubj child
# - set argument as NP   if it doesn't have a nsubj/cop child and its head is a noun
def mark(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_cat = subbtree_root_node['category']

    if subbtree_root_cat is None:
        subbtree_root_node['category'] = VariableCategory()
        subbtree_root_cat = subbtree_root_node['category']

    children = subbtree.get_children(subbtree_root)

    # assign category to argument according to the rules above
    argument_cat = None
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'argument':
            # identify the index of the head of mark
            head_idx = subbtree_root_node['head_idx']

            # check the dependents (in dtree) of the token at this index
            has_nsubj = False
            has_cop = False
            for head_child in dtree.get_children(head_idx):
                if head_child in subbtree.get_leaf_node_indices(subbtree_root):
                    head_child_deprel = dtree.get_deprel(head_child)
                    if head_child_deprel in ['nsubj', 'csubj']:
                        has_nsubj = True
                    elif head_child_deprel in ['cop']:
                        has_cop = True

            if has_nsubj:
                argument_cat = Category.parse('S')
            else:
                head_upos = dtree.get_pos(head_idx)
                if head_upos in ['NOUN', 'PRON', 'PROPN', 'NUM', 'SYM'] and not has_cop:
                    argument_cat = Category.parse('NP')
                else:
                    argument_cat = Category.parse('S|NP')

                    # adjust index of argument_cat so that it's the same as its result category
                    argument_cat.index = subbtree_root_cat.index
                    argument_cat.left.index = argument_cat.index

                    # adjust index of argument_cat according to EUD
                    if APPLY_COINDEXATION:
                        eud_deps = dtree.get_eud_children(head_idx, eud_only=True)
                        if eud_deps is not None:
                            # identify core eud dependent
                            core_eud_dep_idx = None
                            core_eud_deprel = None
                            for eud_dep in eud_deps:
                                eud_dep_idx = eud_dep[0]
                                eud_deprel = eud_dep[1]
                                eud_deprel = eud_deprel.split(':')
                                eud_deprel = eud_deprel[0]

                                if ':' in eud_deprel:
                                    eud_first_colon_idx = eud_deprel.index(":")
                                    eud_deprel = eud_deprel[:eud_first_colon_idx]

                                if eud_deprel in ['nsubj:xsubj', 'nsubj', 'obj', 'iobj']:
                                    core_eud_dep_idx = eud_dep_idx
                                    core_eud_deprel = eud_deprel
                                    break

                            # assign index of core eud dependent to argument of argument_cat
                            if core_eud_dep_idx is not None:
                                argument_cat.right.index = str(core_eud_dep_idx) + ':t'

            # adjust the index so that the index of the whole phrase (subbtree_root_cat)
            # is the same as the index of the argument
            argument_cat.index = subbtree_root_cat.index

            child_node['category'] = argument_cat

    # solve for the other functor child
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'functor':
            # identify slash direction
            head_idx = subbtree_root_node['head_idx']
            dep_idx = subbtree_root_node['dep_idx']

            if head_idx > dep_idx:
                slash = '/'
            else:
                slash = '\\'

            child_node_cat = solve_functor(res=subbtree_root_cat,
                                           arg=argument_cat,
                                           slash=slash)

            # similar to a modifier, the index of the whole category is different
            # from the index of the result or the index of the argument
            child_node_cat.index = Index()

            child_node['category'] = child_node_cat


# similar to default(), but the dependent (of case) is now the functor
def case(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_cat = subbtree_root_node['category']

    if subbtree_root_cat is None:
        subbtree_root_node['category'] = VariableCategory()
        subbtree_root_cat = subbtree_root_node['category']

    children = subbtree.get_children(subbtree_root)

    # assign a variable category to the child with 'category_type' == 'argument'
    argument_cat = None
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'argument':
            child_node['category'] = VariableCategory()
            argument_cat = child_node['category']

            # adjust the index so that the index of the whole phrase (subbtree_root_cat)
            # is the same as the index of the argument
            argument_cat.index = subbtree_root_cat.index

    # solve for the other functor child
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'functor':
            # identify slash direction
            head_idx = subbtree_root_node['head_idx']
            dep_idx = subbtree_root_node['dep_idx']

            if head_idx > dep_idx:
                slash = '/'
            else:
                slash = '\\'

            child_node_cat = solve_functor(res=subbtree_root_cat,
                                           arg=argument_cat,
                                           slash=slash)

            # similar to a modifier, the index of the whole category is different
            # from the index of the result or the index of the argument
            child_node_cat.index = Index()

            child_node['category'] = child_node_cat

    # TODO rule for case marker of core arguments?


# basic rules for clausal modifier:
# - the child with 'category_type' == 'argument' should have the same category as subbtree_root
# - if a marker does not exist in the subordinate clause, a type-changing rule will be applied
def cmod(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_cat = subbtree_root_node['category']

    if subbtree_root_cat is None:
        subbtree_root_node['category'] = VariableCategory()
        subbtree_root_cat = subbtree_root_node['category']

    children = subbtree.get_children(subbtree_root)

    # the child with 'category_type' == 'argument' should have the same category as subbtree_root
    argument_cat = None
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'argument':
            child_node['category'] = subbtree_root_cat
            argument_cat = child_node['category']

    # solve for the other functor child
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'functor':
            # identify slash direction
            head_idx = subbtree_root_node['head_idx']
            dep_idx = subbtree_root_node['dep_idx']

            if head_idx > dep_idx:
                slash = '/'
            else:
                slash = '\\'

            functor_cat = solve_functor(res=subbtree_root_cat,
                                        arg=argument_cat,
                                        slash=slash)

            # a modifier should have category of type (X_i|X_i)_j
            # where the index of the entire category is different from the index
            # of result and argument categories
            functor_cat.index = Index()

            # if no marker exists in the subordinate clause, this functor_cat
            # will be the "result" category of a type-changing rule;
            # otherwise it's just a normal category
            has_mark = False
            for dep_child in dtree.get_children(dep_idx):
                if dtree.get_deprel(dep_child) in ['mark']:
                    has_mark = True

            if has_mark:
                child_node['category'] = functor_cat
            else:
                child_node['category_tc'] = functor_cat

                # determine the "argument" (original) category of this type-changing rule
                # same logic as rules for ccomp/mark/etc.
                has_nsubj = False
                has_cop = False
                for dep_child in dtree.get_children(dep_idx):
                    if dep_child in subbtree.get_leaf_node_indices(subbtree_root):
                        dep_child_deprel = dtree.get_deprel(dep_child)
                        if dep_child_deprel in ['nsubj', 'csubj']:
                            has_nsubj = True
                        elif dep_child_deprel in ['cop']:
                            has_cop = True

                if has_nsubj:
                    functor_cat_ = Category.parse('S')
                else:
                    dep_upos = dtree.get_pos(dep_idx)
                    if dep_upos in ['NOUN', 'PRON', 'PROPN', 'NUM', 'SYM'] and not has_cop:
                        functor_cat_ = Category.parse('NP')
                    else:
                        functor_cat_ = Category.parse('S|NP')

                        # result of the original category should have the same index as the whole original category
                        # argument of original category and argument of type-changed category should have the same index
                        functor_cat_.left.index = functor_cat.index
                        functor_cat_.right.index = functor_cat.right.index

                        # adjust index of argument_cat according to EUD
                        if APPLY_COINDEXATION:
                            eud_deps = dtree.get_eud_children(dep_idx, eud_only=True)
                            if eud_deps is not None:
                                # identify core eud dependent
                                core_eud_dep_idx = None
                                core_eud_deprel = None
                                for eud_dep in eud_deps:
                                    eud_dep_idx = eud_dep[0]
                                    eud_deprel = eud_dep[1]
                                    eud_deprel = eud_deprel.split(':')
                                    eud_deprel = eud_deprel[0]

                                    if ':' in eud_deprel:
                                        eud_first_colon_idx = eud_deprel.index(":")
                                        eud_deprel = eud_deprel[:eud_first_colon_idx]

                                    if eud_deprel in ['nsubj:xsubj', 'nsubj', 'obj', 'iobj']:
                                        core_eud_dep_idx = eud_dep_idx
                                        core_eud_deprel = eud_deprel
                                        break

                                # assign index of core eud dependent to argument of argument_cat
                                if core_eud_dep_idx is not None:
                                    functor_cat_.right.index = str(core_eud_dep_idx) + ':t'

                # the "original" category should have the same index as the type-changed category
                functor_cat_.index = functor_cat.index

                child_node['category'] = functor_cat_


# for the most part, rule for nmod should be the same as rule for other modifiers;
# this rule below is designed for cases like "most of us", where "most" is the head of nmod
# but is not a noun, so the conversion algorithm fails to assign a category to "most"
def nmod(subbtree_root, subbtree, dtree):
    # call the general modifier rule here
    modifier(subbtree_root, subbtree, dtree)

    # now handle special case for nmod
    children = subbtree.get_children(subbtree_root)
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'argument':
            if child_node['category'].is_variable:
                child_node['category'].update(Category.parse('NP'))


# both children should share the same category,
# and their categories should have the same index
def conj(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_cat = subbtree_root_node['category']

    if subbtree_root_cat is None:
        subbtree_root_node['category'] = VariableCategory()
        subbtree_root_cat = subbtree_root_node['category']

    children = subbtree.get_children(subbtree_root)
    for child in children:
        child_node = subbtree.get_btree_node(child)

        if child_node['category_type'] == 'argument':
            child_node['category'] = subbtree_root_cat

            # TODO need to distinguish two conjuncts; not a good implementation
            ridx = random.randint(0, 999999999)
            child_node['conj'] = str(subbtree_root) + ':' + str(ridx)
            for descendant in subbtree.get_all_descendants(child):
                descendant_node = subbtree.get_btree_node(descendant)
                descendant_node['conj'] = str(subbtree_root) + ':' + str(ridx)

        elif child_node['category_type'] == 'functor':
            child_node['category'] = subbtree_root_cat

            # TODO need to distinguish two conjuncts; not a good implementation
            ridx = random.randint(0, 999999999)
            child_node['conj'] = str(subbtree_root) + ':' + str(ridx)
            for descendant in subbtree.get_all_descendants(child):
                descendant_node = subbtree.get_btree_node(descendant)
                descendant_node['conj'] = str(subbtree_root) + ':' + str(ridx)


# the conjunct should receive category 'conj'
def cc(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_cat = subbtree_root_node['category']

    if subbtree_root_cat is None:
        subbtree_root_node['category'] = VariableCategory()
        subbtree_root_cat = subbtree_root_node['category']

    children = subbtree.get_children(subbtree_root)
    for child in children:
        child_node = subbtree.get_btree_node(child)

        if child_node['category_type'] == 'functor':
            child_node['category'] = Category.parse('conj')

        elif child_node['category_type'] == 'argument':
            child_node['category'] = subbtree_root_cat


# basic rules for ref (whose dependent is usually a relative pronoun):
# - set argument as S    if it has a nsubj child and no core eud dependents
# - set argument as S|NP if it has a nsubj child and a core eud dependent
# - set argument as S|NP if it doesn't have a nsubj child
def ref(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_cat = subbtree_root_node['category']

    if subbtree_root_cat is None:
        subbtree_root_node['category'] = VariableCategory()
        subbtree_root_cat = subbtree_root_node['category']

    children = subbtree.get_children(subbtree_root)

    # assign category to argument according to the rules above
    argument_cat = None
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'argument':
            # identify the index of the head of ref
            head_idx = subbtree_root_node['head_idx']

            # check the dependents (in dtree) of the token at this index
            has_nsubj = False
            for head_child in dtree.get_children(head_idx):
                if head_child in subbtree.get_leaf_node_indices(subbtree_root):
                    head_child_deprel = dtree.get_deprel(head_child)
                    if head_child_deprel in ['nsubj', 'csubj']:
                        has_nsubj = True

            has_eud = False
            eud_deps = dtree.get_eud_children(head_idx, eud_only=True)
            if eud_deps is not None:
                for eud_dep in eud_deps:
                    eud_dep_deprel = eud_dep[1]
                    if eud_dep_deprel in ['nsubj:xsubj', 'nsubj', 'obj', 'iobj']:
                        has_eud = True

            if has_nsubj and not has_eud:
                argument_cat = Category.parse('S')
            else:
                argument_cat = Category.parse('S|NP')

                # adjust index of argument_cat so that it's the same as its result category
                argument_cat.index = subbtree_root_cat.index
                argument_cat.left.index = argument_cat.index

                # adjust index of argument_cat according to EUD
                if APPLY_COINDEXATION_RELCL:
                    eud_deps = dtree.get_eud_children(head_idx, eud_only=True)
                    if eud_deps is not None:
                        # identify core eud dependent
                        core_eud_dep_idx = None
                        core_eud_deprel = None
                        for eud_dep in eud_deps:
                            eud_dep_idx = eud_dep[0]
                            eud_deprel = eud_dep[1]
                            eud_deprel = eud_deprel.split(':')
                            eud_deprel = eud_deprel[0]

                            if ':' in eud_deprel:
                                eud_first_colon_idx = eud_deprel.index(":")
                                eud_deprel = eud_deprel[:eud_first_colon_idx]

                            if eud_deprel in ['nsubj:xsubj', 'nsubj', 'obj', 'iobj']:
                                core_eud_dep_idx = eud_dep_idx
                                core_eud_deprel = eud_deprel
                                break

                        # assign index of core eud dependent to argument of argument_cat
                        if core_eud_dep_idx is not None:
                            argument_cat.right.index = str(core_eud_dep_idx) + ':t'

            # adjust the index so that the index of the whole phrase (subbtree_root_cat)
            # is the same as the index of the argument
            argument_cat.index = subbtree_root_cat.index

            child_node['category'] = argument_cat

    # solve for the other functor child
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'functor':
            # identify slash direction
            head_idx = subbtree_root_node['head_idx']
            dep_idx = subbtree_root_node['dep_idx']

            if head_idx > dep_idx:
                slash = '/'
            else:
                slash = '\\'

            child_node_cat = solve_functor(res=subbtree_root_cat,
                                           arg=argument_cat,
                                           slash=slash)

            # similar to a modifier, the index of the whole category is different
            # from the index of the result or the index of the argument
            child_node_cat.index = Index()

            child_node['category'] = child_node_cat


# basic rules for relative clause:
# - the child with 'category_type' == 'argument' should have the same category as subbtree_root
# - if a ref-XXX (relative pronoun, etc.) does not exist in the subordinate clause, a type-changing rule will be applied
def relcl(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_cat = subbtree_root_node['category']

    if subbtree_root_cat is None:
        subbtree_root_node['category'] = VariableCategory()
        subbtree_root_cat = subbtree_root_node['category']

    children = subbtree.get_children(subbtree_root)

    # the child with 'category_type' == 'argument' should have the same category as subbtree_root
    argument_cat = None
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'argument':
            child_node['category'] = subbtree_root_cat
            argument_cat = child_node['category']

    # solve for the other functor child
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'functor':
            # identify slash direction
            head_idx = subbtree_root_node['head_idx']
            dep_idx = subbtree_root_node['dep_idx']

            if head_idx > dep_idx:
                slash = '/'
            else:
                slash = '\\'

            functor_cat = solve_functor(res=subbtree_root_cat,
                                        arg=argument_cat,
                                        slash=slash)

            # a modifier should have category of type (X_i|X_i)_j
            # where the index of the entire category is different from the index
            # of result and argument categories
            functor_cat.index = Index()

            # if no ref-XXX exists in the subordinate clause, this functor_cat
            # will be the "result" category of a type-changing rule;
            # otherwise it's just a normal category
            has_ref = False
            for dep_child in dtree.get_children(dep_idx):
                if dtree.get_deprel(dep_child) in ['ref-nsubj', 'ref-obj', 'ref-iobj']:
                    has_ref = True

            if has_ref:
                child_node['category'] = functor_cat
            else:
                child_node['category_tc'] = functor_cat

                # determine the "argument" (original) category of this type-changing rule
                # same logic as rules for ref
                has_nsubj = False
                for dep_child in dtree.get_children(dep_idx):
                    if dep_child in subbtree.get_leaf_node_indices(subbtree_root):
                        dep_child_deprel = dtree.get_deprel(dep_child)
                        if dep_child_deprel in ['nsubj', 'csubj']:
                            has_nsubj = True

                has_eud = False
                eud_deps = dtree.get_eud_children(dep_idx, eud_only=True)
                if eud_deps is not None:
                    for eud_dep in eud_deps:
                        eud_dep_deprel = eud_dep[1]
                        if eud_dep_deprel in ['nsubj:xsubj', 'nsubj', 'obj', 'iobj']:
                            has_eud = True

                if has_nsubj and not has_eud:
                    functor_cat_ = Category.parse('S')
                else:
                    functor_cat_ = Category.parse('S|NP')

                    # adjust index of argument_cat so that it's the same as its result category
                    functor_cat_.index = functor_cat.index
                    functor_cat_.left.index = functor_cat_.index

                    # adjust index of argument_cat according to EUD
                    if APPLY_COINDEXATION_RELCL:
                        eud_deps = dtree.get_eud_children(dep_idx, eud_only=True)
                        if eud_deps is not None:
                            # identify core eud dependent
                            core_eud_dep_idx = None
                            core_eud_deprel = None
                            for eud_dep in eud_deps:
                                eud_dep_idx = eud_dep[0]
                                eud_deprel = eud_dep[1]
                                eud_deprel = eud_deprel.split(':')
                                eud_deprel = eud_deprel[0]

                                if ':' in eud_deprel:
                                    eud_first_colon_idx = eud_deprel.index(":")
                                    eud_deprel = eud_deprel[:eud_first_colon_idx]

                                if eud_deprel in ['nsubj:xsubj', 'nsubj', 'obj', 'iobj']:
                                    core_eud_dep_idx = eud_dep_idx
                                    core_eud_deprel = eud_deprel
                                    break

                            # assign index of core eud dependent to argument of argument_cat
                            if core_eud_dep_idx is not None:
                                functor_cat_.right.index = str(core_eud_dep_idx) + ':t'

                # the "original" category should have the same index as the type-changed category
                functor_cat_.index = functor_cat.index

                child_node['category'] = functor_cat_


# basic rules for adpositional phrase:
# - the child with 'category_type' == 'argument' should have category 'PP'
def oblap(subbtree_root, subbtree, dtree):
    subbtree_root_node = subbtree.get_btree_node(subbtree_root)
    subbtree_root_cat = subbtree_root_node['category']

    if subbtree_root_cat is None:
        subbtree_root_node['category'] = VariableCategory()
        subbtree_root_cat = subbtree_root_node['category']

    children = subbtree.get_children(subbtree_root)

    # the child with 'category_type' == 'argument' should have the same category as subbtree_root
    argument_cat = None
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'argument':
            argument_cat = Category.parse('PP')
            child_node['category'] = argument_cat

    # solve for the other functor child
    for child in children:
        child_node = subbtree.get_btree_node(child)
        if child_node['category_type'] == 'functor':
            # identify slash direction
            head_idx = subbtree_root_node['head_idx']
            dep_idx = subbtree_root_node['dep_idx']

            if head_idx > dep_idx:
                slash = '\\'
            else:
                slash = '/'

            functor_cat = solve_functor(res=subbtree_root_cat,
                                        arg=argument_cat,
                                        slash=slash)

            child_node['category'] = functor_cat
