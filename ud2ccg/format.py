class LDescription:
    def __init__(self, ccg_cat, mod_pos, orig_pos, word, pred_arg_cat):
        self.ccg_cat = ccg_cat
        self.mod_pos = mod_pos
        self.orig_pos = orig_pos
        self.word = word.strip().replace(' ', '_')
        self.pred_arg_cat = pred_arg_cat

    def __repr__(self):
        return '<L {} {} {} {} {}>'.format(self.ccg_cat,
                                           self.mod_pos,
                                           self.orig_pos,
                                           self.word,
                                           self.pred_arg_cat)


class TDescription:
    def __init__(self, ccg_cat, head_child_idx, num_children=2):
        self.ccg_cat = ccg_cat
        self.head_child_idx = head_child_idx
        self.num_children = num_children

    def __repr__(self):
        return '<T {} {} {}>'.format(self.ccg_cat,
                                     self.head_child_idx,
                                     self.num_children)


class Node:
    def __init__(self, description, left_child=None, right_child=None):
        self.description = description
        self.left_child = left_child
        self.right_child = right_child

    def __repr__(self):
        if self.left_child is not None and self.right_child is not None:
            return '({} {} {} )'.format(self.description,
                                        self.left_child,
                                        self.right_child)
        elif self.left_child is not None and self.right_child is None:
            return '({} {} )'.format(self.description,
                                     self.left_child)
        else:
            return '({})'.format(self.description)


def to_auto(btree, dtree, debug=False):
    def _traverse(btree_root, expand_tc=True):
        btree_root_node = btree.get_btree_node(btree_root)

        if btree_root_node['category'] is None:
            btree_root_cat = '?'
            btree_root_pred_arg_cat = '?'
        else:
            btree_root_cat = str(btree_root_node['category'])
            btree_root_pred_arg_cat = btree_root_node['category'].to_str()

            if not btree_root_cat.strip():
                btree_root_cat = '?'

            if not btree_root_pred_arg_cat.strip():
                btree_root_pred_arg_cat = '?'

            # handle type-changing rule
            if expand_tc:
                if 'category_tc' in btree_root_node:
                    btree_root_cat_tc = btree_root_node['category_tc']

                    if debug:
                        btree_root_cat_tc = btree_root_node['category_tc'].to_str()

                    description = TDescription(ccg_cat=btree_root_cat_tc,
                                               head_child_idx=0,
                                               num_children=1)

                    return Node(description, _traverse(btree_root, expand_tc=False))

        if debug:
            btree_root_cat = btree_root_pred_arg_cat

        children = btree.get_children(btree_root)

        if children:
            if len(children) == 2:
                if btree.get_idx(children[0]) < btree.get_idx(children[1]):
                    head_child_idx = 0
                    left_child = children[0]
                    right_child = children[1]
                else:
                    head_child_idx = 1
                    left_child = children[1]
                    right_child = children[0]

                description = TDescription(ccg_cat=btree_root_cat,
                                           head_child_idx=head_child_idx,
                                           num_children=2)

                return Node(description, _traverse(left_child), _traverse(right_child))
            else:
                # if there is only one child
                head_child_idx = 0
                child = children[0]

                description = TDescription(ccg_cat=btree_root_cat,
                                           head_child_idx=head_child_idx,
                                           num_children=1)

                return Node(description, _traverse(child))
        else:
            pos = dtree.get_pos(btree_root_node['idx'])

            word = dtree.get_form(btree_root_node['idx'])

            description = LDescription(ccg_cat=btree_root_cat,
                                       mod_pos=pos,
                                       orig_pos=pos,
                                       word=word,
                                       pred_arg_cat=btree_root_pred_arg_cat)

            return Node(description)

    auto_root = _traverse(btree.get_root())

    return auto_root
