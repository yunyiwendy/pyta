import astroid.inference
import astroid
from astroid.node_classes import *
from typing import *
from typing import CallableMeta, TupleMeta, Union, _gorg, _geqv, _ForwardRef
from astroid.transforms import TransformVisitor
from ..typecheck.base import op_to_dunder_binary, op_to_dunder_unary, Environment, TypeConstraints, TypeInferenceError
from ..typecheck.type_store import TypeStore


class NoType:
    pass


class TypeErrorInfo:
    """Class representing an error in type inference."""
    def __init__(self, msg, node):
        self.msg = msg
        self.node = node

    def __str__(self):
        return self.msg


class TypeInfo:
    """A class representing the inferred type of a value.

    === Instance attributes ===
    - type (Union[type, TypeErrorInfo]): type of the inferred value
    """
    def __init__(self, type_: Union[type, TypeErrorInfo]):
        self.type = type_


class TypeInferer:
    """The class responsible for inferring types given an astroid AST.
    """
    type_constraints = TypeConstraints()
    type_store = TypeStore(type_constraints)

    def __init__(self):
        self.type_constraints.clear_tvars()

    ###########################################################################
    # Setting up the environment
    ###########################################################################
    def environment_transformer(self) -> TransformVisitor:
        """Return a TransformVisitor that sets an environment for every node."""
        visitor = TransformVisitor()
        visitor.register_transform(astroid.FunctionDef, self._set_function_def_environment)
        visitor.register_transform(astroid.ClassDef, self._set_classdef_environment)
        visitor.register_transform(astroid.Module, self._set_module_environment)
        visitor.register_transform(astroid.ListComp, self._set_listcomp_environment)
        visitor.register_transform(astroid.DictComp, self._set_dictcomp_environment)
        visitor.register_transform(astroid.SetComp, self._set_setcomp_environment)
        return visitor

    def _set_module_environment(self, node):
        """Method to set environment of a Module node."""
        node.type_environment = Environment(
            globals_={name: self.type_constraints.fresh_tvar() for name in node.globals})
        self._populate_local_env(node)

    def _set_classdef_environment(self, node):
        """Method to set environment of a ClassDef node."""
        node.type_environment = Environment()
        for name in node.instance_attrs:
            node.type_environment.locals[name] = self.type_constraints.fresh_tvar()
        for name in node.locals:
            node.type_environment.locals[name] = self.type_constraints.fresh_tvar()

    def _set_function_def_environment(self, node):
        """Method to set environment of a FunctionDef node."""
        node.type_environment = Environment()
        self._populate_local_env(node)
        node.type_environment.locals['return'] = self.type_constraints.fresh_tvar()

    def _set_listcomp_environment(self, node):
        """Set the environment of a ListComp node representing a list
        comprehension expression."""
        node.type_environment = Environment()
        for name in node.locals:
            node.type_environment.locals[name] = self.type_constraints.fresh_tvar()

    def _set_dictcomp_environment(self, node):
        """Environment setter for DictComp node representing a dictionary
        comprehension expression."""
        node.type_environment = Environment()
        for name in node.locals:
            node.type_environment.locals[name] = self.type_constraints.fresh_tvar()

    def _set_setcomp_environment(self, node):
        """Environment setter for SetComp node representing a set comprehension expression"""
        node.type_environment = Environment()
        for name in node.locals:
            node.type_environment.locals[name] = self.type_constraints.fresh_tvar()

    def _populate_local_env(self, node):
        """Helper to populate locals attributes in type environment of given node."""
        for var_name in node.locals:
            try:
                var_value = node.type_environment.lookup_in_env(var_name)
            except KeyError:
                var_value = self.type_constraints.fresh_tvar()
            node.type_environment.locals[var_name] = var_value

    ###########################################################################
    # Type inference methods
    ###########################################################################
    def type_inference_transformer(self) -> TransformVisitor:
        """Instantiate a visitor to perform type inference on an AST.
        """
        type_visitor = TransformVisitor()
        for klass in astroid.ALL_NODE_CLASSES:
            if hasattr(self, f'visit_{klass.__name__.lower()}'):
                type_visitor.register_transform(klass, getattr(self, f'visit_{klass.__name__.lower()}'))
        return type_visitor

    ##############################################################################
    # Literals
    ##############################################################################
    def visit_const(self, node):
        """Populate type constraints for astroid nodes for num/str/bool/None/bytes literals."""
        node.type_constraints = TypeInfo(type(node.value))

    def visit_tuple(self, node):
        # Tuple is being evaluated rather than assigned to - find types of its elements
        if node.ctx == astroid.Load:
            node.type_constraints = TypeInfo(
                Tuple[tuple(x.type_constraints.type for x in node.elts)])
        else:
            # Tuple is on LHS; will never have a type.
            node.type_constraints = TypeInfo(NoType)

    def visit_list(self, node):
        if len(node.elts) == 0:
            node.type_constraints = TypeInfo(List[Any])
        else:
            node_type = node.elts[0].type_constraints.type
            for elt in node.elts:
                node_type = self.type_constraints.least_general_unifier(elt.type_constraints.type, node_type)
            node.type_constraints = TypeInfo(List[node_type])

    def visit_set(self, node):
        if len(node.elts) == 0:
            node.type_constraints = TypeInfo(Set[Any])
        else:
            node_type = node.elts[0].type_constraints.type
            for elt in node.elts:
                node_type = self.type_constraints.least_general_unifier(elt.type_constraints.type, node_type)
            node.type_constraints = TypeInfo(Set[node_type])

    def visit_dict(self, node):
        if len(node.items) == 0:
            node.type_constraints = TypeInfo(Dict[Any, Any])
        else:
            key_type, val_type = node.items[0][0].type_constraints.type, node.items[0][1].type_constraints.type
            for key_node, val_node in node.items:
                key_type = self.type_constraints.least_general_unifier(key_node.type_constraints.type, key_type)
                val_type = self.type_constraints.least_general_unifier(val_node.type_constraints.type, val_type)
            node.type_constraints = TypeInfo(Dict[key_type, val_type])

    def visit_index(self, node):
        node.type_constraints = node.value.type_constraints

    def visit_slice(self, node):
        node.type_constraints = TypeInfo(slice)

    def visit_expr(self, node):
        """Expr nodes take the type of their child
        """
        node.type_constraints = node.value.type_constraints

    def _closest_frame(self, node):
        """Helper method to find the closest ancestor node with an environment relative to the given node."""
        closest_scope = node
        if node.parent:
            closest_scope = node.parent
            if hasattr(closest_scope, 'type_environment'):
                return closest_scope
            else:
                return self._closest_frame(closest_scope)
        else:
            return closest_scope

    def visit_name(self, node):
        try:
            node.type_constraints = TypeInfo(self._closest_frame(node).type_environment.lookup_in_env(node.name))
        except KeyError:
            self._closest_frame(node).type_environment.create_in_env(self.type_constraints, 'globals', node.name)
            node.type_constraints = TypeInfo(node.frame().type_environment.globals[node.name])

    ##############################################################################
    # Operation nodes
    ##############################################################################
    def _handle_call(self, node, func_name, *args):
        """Helper to lookup a function and unify it with given arguments.
           Returns the return type of unified function call."""
        arg_types = [self.type_constraints.lookup_concrete(arg) for arg in args]
        if len(arg_types) == 2:
            func_call = op_to_dunder_binary(func_name)
        elif len(arg_types) == 1:
            func_call = op_to_dunder_unary(func_name)
        else:
            func_call = func_name
        try:
            func_type = self.type_store.lookup_function(func_call, *arg_types)
        except KeyError:
            return TypeInfo(
                TypeErrorInfo(f'Function {func_call} not found with given args:\
                              {arg_types}', node))

        try:
            return_type = self.type_constraints.unify_call(func_type, *arg_types)
        except TypeInferenceError:
            return TypeInfo(
                TypeErrorInfo('Bad unify_call of function {func_call} given\
                              args: {arg_types}', node))
        else:
            return TypeInfo(return_type)

    def visit_binop(self, node):
        node.type_constraints = self._handle_call(node, node.op, node.left.type_constraints.type,
                                                  node.right.type_constraints.type)

    def visit_unaryop(self, node):
        if node.op == 'not':
            node.type_constraints = TypeInfo(bool)
        else:
            node.type_constraints = self._handle_call(node, node.op, node.operand.type_constraints.type)

    def visit_subscript(self, node):
        if hasattr(node.value, 'type_constraints') and hasattr(node.slice, 'type_constraints'):
            node.type_constraints = self._handle_call(node, '__getitem__', node.value.type_constraints.type,
                                                      node.slice.type_constraints.type)

    def visit_boolop(self, node):
        """Boolean operators are 'and', 'or'; the result type can be either of the argument types."""
        node_type_constraints = {operand_node.type_constraints.type for operand_node in node.values}
        if len(node_type_constraints) == 1:
            node.type_constraints = TypeInfo(node_type_constraints.pop())
        else:
            node.type_constraints = TypeInfo(Any)

    def visit_compare(self, node):
        """Comparison operators are: '<', '>', '==', '<=', '>=', '!=', 'in', 'is'.
        All comparisons yield boolean values."""
        # TODO: 'in' comparator
        return_types = set()
        left_value = node.left
        for comparator, right_value in node.ops:
            if comparator == 'is':
                return_types.add(bool)
            else:
                function_type = self.type_store.lookup_function(op_to_dunder_binary(comparator),
                                                            left_value.type_constraints.type,
                                                            right_value.type_constraints.type)
                left_value = right_value
                return_types.add(self.type_constraints.unify_call(function_type, left_value.type_constraints.type,
                                                              right_value.type_constraints.type))
        if len(return_types) == 1:
            node.type_constraints = TypeInfo(return_types.pop())
        else:
            node.type_constraints = TypeInfo(Any)

    ##############################################################################
    # Statements
    ##############################################################################
    def visit_assign(self, node):
        # multi-assignment; LHS is a tuple of AssignName target nodes as "elements"
        if isinstance(node.targets[0], astroid.Tuple):
            if isinstance(node.value, astroid.Tuple):
                target_type_tuple = zip(node.targets[0].elts, node.value.elts)
                for target_node, value in target_type_tuple:
                    target_tvar = node.frame().type_environment.lookup_in_env(target_node.name)
                    self.type_constraints.unify(target_tvar, value.type_constraints.type)
            else:
                value_tvar = node.frame().type_environment.lookup_in_env(node.value.name)
                value_type = self.type_constraints.lookup_concrete(value_tvar)
                rtype = self._handle_call(node, '__iter__', value_type).type
                for target_node in node.targets[0].elts:
                    target_type_var = node.frame().type_environment.lookup_in_env(target_node.name)
                    self.type_constraints.unify(target_type_var, rtype.__args__[0])
        else:
            # assignment(s) in single statement
            for target_node in node.targets:
                if isinstance(target_node, astroid.AssignName):
                    target_type_var = node.frame().type_environment.lookup_in_env(target_node.name)
                    self.type_constraints.unify(target_type_var, node.value.type_constraints.type)
        node.type_constraints = TypeInfo(NoType)

    def visit_return(self, node):
        t = node.value.type_constraints.type
        self.type_constraints.unify(node.frame().type_environment.locals['return'], t)
        node.type_constraints = TypeInfo(NoType)

    def visit_functiondef(self, node):
        arg_types = [self.type_constraints.lookup_concrete(node.type_environment.lookup_in_env(arg))
                     for arg in node.argnames()]

        # Check whether this is a method in a class
        if isinstance(node.parent, astroid.ClassDef) and isinstance(arg_types[0], TypeVar):
            self.type_constraints.unify(arg_types[0], _ForwardRef(node.parent.name))

        # check if return nodes exist; there is a return statement in function body.
        if len(list(node.nodes_of_class(astroid.Return))) == 0:
            func_type = Callable[arg_types, None]
        else:
            rtype = self.type_constraints.lookup_concrete(node.type_environment.lookup_in_env('return'))
            func_type = Callable[arg_types, rtype]
        func_type.polymorphic_tvars = [arg for arg in arg_types
                                       if isinstance(arg, TypeVar)]
        self.type_constraints.unify(node.parent.frame().type_environment.lookup_in_env(node.name), func_type)
        node.type_constraints = TypeInfo(NoType)

    def visit_call(self, node):
        func_name = node.func.name
        if isinstance(node.frame().locals.get(func_name)[0], astroid.ClassDef):
            # This is the constructor of a class
            func_t = self.type_constraints.lookup_concrete(
                node.frame().locals[func_name][0].type_environment.locals['__init__'])
            arg_types = [_ForwardRef(func_name)] + [arg.type_constraints.type for arg in node.args]
            self.type_constraints.unify_call(func_t, *arg_types)
            node.type_constraints = TypeInfo(_ForwardRef(func_name))
        else:
            func_t = self.type_constraints.lookup_concrete(node.frame().type_environment.locals[func_name])
            arg_types = [arg.type_constraints.type for arg in node.args]
            ret_type = self.type_constraints.unify_call(func_t, *arg_types)
            node.type_constraints = TypeInfo(ret_type)

    def visit_for(self, node):
        for_node = list(node.nodes_of_class(astroid.For))[0]
        rtype = self._handle_call(node, '__iter__', for_node.iter.type_constraints.type).type
        # there may be one target, or a Generic of targets to unify.
        if isinstance(for_node.target, astroid.AssignName):
            self.type_constraints.unify(rtype.__args__[0], node.frame().type_environment.lookup_in_env(for_node.target.name))
        else:
            target_tvars = [node.frame().type_environment.lookup_in_env(target_node.name) for target_node in for_node.target.elts]
            for i in range(len(target_tvars)):
                self.type_constraints.unify(rtype.__args__[0], target_tvars[i])

    def visit_ifexp(self, node):
        if self.type_constraints.can_unify(node.body.type_constraints.type, node.orelse.type_constraints.type):
            self.type_constraints.unify(node.body.type_constraints.type, node.orelse.type_constraints.type)
            node.type_constraints = TypeInfo(node.body.type_constraints.type)
        else:
            node.type_constraints = TypeInfo(Any)

    def visit_comprehension(self, node):
        arg_type = self.type_constraints.lookup_concrete(node.iter.type_constraints.type)
        rtype = self._handle_call(node, '__iter__', arg_type).type
        if isinstance(node.target, astroid.Tuple):
            for target_node in node.target.elts:
                target_tvar = self._closest_frame(node).type_environment.lookup_in_env(target_node.name)
                self.type_constraints.unify(target_tvar, rtype)
        else:
            target_tvar = self._closest_frame(node).type_environment.lookup_in_env(node.target.name)
            self.type_constraints.unify(target_tvar, rtype.__args__[0])
        node.type_constraints = TypeInfo(NoType)

    def visit_listcomp(self, node):
        val_type = self.type_constraints.lookup_concrete(node.elt.type_constraints.type)
        node.type_constraints = TypeInfo(List[val_type])

    def visit_dictcomp(self, node):
        key_type = self.type_constraints.lookup_concrete(node.key.type_constraints.type)
        val_type = self.type_constraints.lookup_concrete(node.value.type_constraints.type)
        node.type_constraints = TypeInfo(Dict[key_type, val_type])

    def visit_setcomp(self, node):
        elt_type = self.type_constraints.lookup_concrete(node.elt.type_constraints.type)
        node.type_constraints = TypeInfo(Set[elt_type])

    def visit_module(self, node):
        node.type_constraints = TypeInfo(NoType)
        # print('All sets:', self.type_constraints._sets)
        # print('Global bindings:', {k: self.type_constraints.lookup_concrete(t) for k, t in node.type_environment.locals.items()})
