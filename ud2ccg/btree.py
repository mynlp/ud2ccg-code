import networkx as nx
import networkx.algorithms.dag as nx_dag
from ud2ccg.config.config import read_obliqueness_hierarchy


# TODO move to config file
obliqueness_hierarchy_path = "ud2ccg/config/ud2-obliqueness-hierarchy.json"
obliqueness_hierarchy = read_obliqueness_hierarchy(obliqueness_hierarchy_path)


class BTree:
    def __init__(self, btree=None):
        self.btree = btree

    @staticmethod
    def from_dtree(dtree):
        # initialize binary tree
        btree = nx.DiGraph()

        # follow https://www.aclweb.org/anthology/D17-1009.pdf
        def _binarize(btree, dtree, parent):
            # get immediate children
            children = dtree.get_children(parent)

            # add children to their stacks according to their position relative to parent
            left_stack = []
            for child in children:
                if child < parent:
                    left_stack.append(child)

            right_stack = []
            for child in reversed(children):
                if child > parent:
                    right_stack.append(child)

            # get obliqueness hierarchy scores of children
            obliqueness_hierarchy_scores = {}
            for child in children:
                obliqueness_hierarchy_scores[child] = obliqueness_hierarchy[dtree.get_deprel(child)]

            # compare scores of children on top of the stacks
            sorted_children = []
            while len(left_stack) > 0 or len(right_stack) > 0:
                if len(left_stack) == 0 and len(right_stack) > 0:
                    sorted_children.append(right_stack[-1])
                    right_stack.pop()
                    continue
                elif len(left_stack) > 0 and len(right_stack) == 0:
                    sorted_children.append(left_stack[-1])
                    left_stack.pop()
                    continue

                top_left = left_stack[-1]
                top_right = right_stack[-1]

                top_left_score = obliqueness_hierarchy_scores[top_left]
                top_right_score = obliqueness_hierarchy_scores[top_right]

                if top_left_score <= top_right_score:
                    sorted_children.append(top_left)
                    left_stack.pop()
                else:
                    sorted_children.append(top_right)
                    right_stack.pop()

            # recursively binarize tree
            dtree_parent = dtree.get_dtree_node(parent)
            btree_parent = (dtree_parent['form'] + ':' + str(parent))   # a unique alias for this node in btree
            btree.add_node(btree_parent,
                           name=dtree_parent['form'],
                           node_type='token',
                           idx=parent,
                           feature=None,
                           category=None,
                           category_type=None,
                           conj='')

            for child in sorted_children:
                this_deprel = dtree.get_deprel(child)

                feature = None

                temp_root = (this_deprel + ':' + str(parent) + '-' + str(child))   # a unique alias for this node in btree
                btree.add_node(temp_root,
                               name=this_deprel,
                               node_type='deprel',
                               deprel=this_deprel,
                               head_idx=parent,
                               dep_idx=child,
                               idx=child,
                               feature=feature,
                               category=None,
                               category_type=None,
                               conj='')

                btree.add_edge(temp_root, btree_parent)
                btree_child = _binarize(btree, dtree, child)
                btree.add_edge(temp_root, btree_child)

                # determine functor/argument
                # TODO move these lists to config
                if this_deprel in ['root']:
                    category_types = {btree_parent: 'ROOT', btree_child: 'argument'}
                elif this_deprel in ['nsubj', 'csubj', 'obj', 'iobj', 'xcomp', 'ccomp'] + ['expl'] + ['scop'] + ['obl-ap']:
                    category_types = {btree_parent: 'functor', btree_child: 'argument'}
                else:
                    category_types = {btree_parent: 'argument', btree_child: 'functor'}
                nx.set_node_attributes(btree, category_types, 'category_type')

                btree_parent = temp_root

            return btree_parent

        # root = 0
        # root only has one child
        _binarize(btree, dtree, dtree.get_root())

        return BTree(btree)

    def tree(self):
        return self.btree

    def get_btree_node(self, node):
        return self.btree.nodes[node]

    def get_root(self):
        return [n for n, d in self.btree.in_degree() if d == 0][0]

    def get_children(self, node):
        children = sorted(list(self.btree.successors(node)))
        if node in children:
            children.remove(node)
        return children

    def get_all_descendants(self, node):
        return nx_dag.descendants(self.btree, node)

    def get_category_type(self, node):
        return self.btree.nodes[node]['category_type']

    def get_leaf_nodes(self):
        return [x for x in self.btree.nodes() if self.btree.out_degree(x)==0 and self.btree.in_degree(x)==1]

    def get_leaf_node_indices(self, node):
        descendants = self.get_all_descendants(node)
        return [self.btree.nodes[x]['idx'] for x in descendants if self.btree.out_degree(x) == 0 and self.btree.in_degree(x) == 1]

    def get_name(self, node):
        return self.btree.nodes[node]['name']

    def get_idx(self, node):
        return self.btree.nodes[node]['idx']

    def remove_node(self, node):
        self.btree.remove_node(node)

    def height(self):
        depths = nx.shortest_path_length(self.btree, source=self.get_root())
        return max(depths.values())
