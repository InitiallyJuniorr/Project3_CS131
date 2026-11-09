from intbase import InterpreterBase, ErrorType
from brewparse import parse_program


class Lambda_Func:
    def __init__(self,formals,body,captured):
        self.formals = formals
        self.body = body
        self.captured = captured

class Func_Value:
    def __init__(self, name):
        self.name = name

class Interpreter(InterpreterBase):
    BUILTINS = {"print", "inputi", "inputs", "car", "cdr", "cons", "append", "length", "+", "-", "*", "/", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "!"}

    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.func_defs = {}
        self.scopes = [{}]

    def run(self, program):
        self.func_defs = {}
        self.func_names = set()
        self.scopes = [{}]

        ast = parse_program(program)

        funcs = ast.get("functions") or []
        main_func_node = None
        for func in funcs:
            name = func.get("name")
            params = [arg.get("name") for arg in (func.get("args") or [])]
            if len(params) != len(set(params)):
                super().error(ErrorType.NAME_ERROR, f"Duplicate param names in function {name}")
            func_pair = (name, len(params))
            if func_pair in self.func_defs:
                super().error(ErrorType.NAME_ERROR, f"Duplicate function {name} with {len(params)} paramters")

            self.func_defs[func_pair] = func
            self.func_names.add(name)

        # Call error if there is no main function 
        if ("main",0) not in self.func_defs:
            super().error(ErrorType.NAME_ERROR, "No main function found with exactly 0 arguments")
        else: 
            main_func_node = self.func_defs[("main", 0)]

        args = main_func_node.get("args")
        if len(args) > 0:
            super().error(ErrorType.NAME_ERROR, "Main function must have no arguments")
            
        body_node = main_func_node.get("body")
        self.eval_expr(body_node)

    def push_scope(self):
        """ Adds empty list of vars to scope list """
        self.scopes.append({})

    def pop_scope(self):
        """ Removes top scope from scope list """
        self.scopes.pop()

    def scope_search(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return True, scope[name]
        return False, None

    def get_var(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        super().error(ErrorType.NAME_ERROR, f"Variable {name} could not be found within scope")        

    def define_var(self, name, val):
        if name in self.scopes[-1]:
            super().error(ErrorType.NAME_ERROR, f"Variable {name} cannot be defined twice")
        self.scopes[-1][name] = val

    def set_var(self, name, val):
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name] = val
                return
        super().error(ErrorType.NAME_ERROR, f"Variable {name} has not yet been defined")

    def print_format(self, val):
        if val is True:
            return "#t"
        if val is False:
            return "#f"
        if type(val) is list: return "{" + " ".join(self.print_format(c) for c in val) + "}"
        return str(val)

    def call_value(self, func, args):
        if isinstance(func, Func_Value):
            return self.handle_custom_function(func.name, args)
        if isinstance(func, Lambda_Func):
            return self.call_lambda(func, args)
        super().error(ErrorType.TYPE_ERROR, f"please do not call the function that you called")

    def call_lambda(self, func, args):
        if len(args) != len(func.formals):
            super().error(ErrorType.NAME_ERROR, f"lambda args did not match given")

        old_scopes = self.scopes
        self.scopes = [dict(func.captured), {}]

        for name, val in zip(func.formals, args):
            self.define_var(name, val)

        result = self.eval_expr(func.body)
        self.scopes = old_scopes
        return result



    def eval_expr(self, node):
        if node.elem_type == InterpreterBase.INT_NODE:
            return node.get("val") 

        if node.elem_type == InterpreterBase.STRING_NODE:
            return node.get("val")

        if node.elem_type == InterpreterBase.BOOL_NODE:
            return node.get("val")

        if node.elem_type == InterpreterBase.LIST_NODE:
            return [self.eval_expr(elem) for elem in node.get("elements") or []]

        if node.elem_type == InterpreterBase.LAMBDA_NODE:
            formals = [arg.get("name") for arg in (node.get("formals") or [])]
            if len(formals) != len(set(formals)):
                super().error(ErrorType.NAME_ERROR, "Duplicates parameters in lambda")
            body = node.get("body")
            captured = {}
            for scope in self.scopes:
                captured.update(scope)
            return Lambda_Func(formals,body, captured)

        if node.elem_type == InterpreterBase.NOT_NODE:
            val = self.eval_expr(node.get("op1"))
            if type(val) is not bool:
                super().error(ErrorType.TYPE_ERROR, "'!' Operator requires boolean argument")
            return not val

        if node.elem_type == InterpreterBase.IF_NODE:
            cond = self.eval_expr(node.get("cond"))
            if type(cond) != bool: 
                super().error(ErrorType.TYPE_ERROR, "If condition must be boolean")
            if (cond):
                return self.eval_expr(node.get("then_expr"))
            else:
                return self.eval_expr(node.get("else_expr")) 

        if node.elem_type == InterpreterBase.QUALIFIED_NAME_NODE:
            var_name = node.get("name")
            exists, val = self.scope_search(var_name)
            if exists:
                return val
            if var_name in self.func_names:
                return Func_Value(var_name)
            if var_name in self.BUILTINS:
                super().error(ErrorType.NAME_ERROR, f"BUILTIN {var_name} can't be used")
            super().error(ErrorType.NAME_ERROR, f"Variable {var_name} can't be identified")            

        if node.elem_type == InterpreterBase.FCALL_NODE:
            return self.eval_fcall(node)

        if node.elem_type == InterpreterBase.SEQ_NODE:
            return self.eval_seq(node)

    def eval_seq(self, seq_node):
        self.push_scope()
        vars_list = seq_node.get("vars") or []
        exprs_list = seq_node.get("exprs") or []

        for var_def in vars_list:
            var_name = var_def.get("name")
            var_val = self.eval_expr(var_def.get("val"))
            self.define_var(var_name, var_val)

        final_expr = None
        for expr in exprs_list:
            final_expr = self.eval_expr(expr)

        self.pop_scope()
        return final_expr

    def eval_fcall(self, fcall_node):
        evaluated_args = [self.eval_expr(arg) for arg in (fcall_node.get("args") or [])]
        func_node = fcall_node.get("fn")

        """ Handle user specified functions / built-ins """
        if func_node.elem_type == InterpreterBase.QUALIFIED_NAME_NODE:
            name = func_node.get("name")
            exists, val = self.scope_search(name)
            if exists:
                return self.call_value(val, evaluated_args)
            elif name in self.BUILTINS:
                return self.handle_builtin(name, evaluated_args)
            elif name in self.func_names:
                return self.handle_custom_function(name, evaluated_args)
            super().error(ErrorType.NAME_ERROR, f"Unknown function {name} with {len(evaluated_args)} params")

        return self.call_value(self.eval_expr(func_node), evaluated_args)

    def handle_builtin(self, func_name, evaluated_args):
        """ Handle print statement by outputting the evaluated arguments """
        if func_name == "print":
            out_str = "".join(self.print_format(arg) for arg in evaluated_args)
            super().output(out_str)
            return True

        """ Handle 'inputi' by receiving user input and returing the valid int, or 0 in a 
        # case where the input is not a valid int, handle inputs similarly, but for strings """
        if func_name in ("inputi","inputs"):
            if len(evaluated_args) > 1:
                super().error(ErrorType.NAME_ERROR, "Input require 0 or 1 arguments")
            elif len(evaluated_args) == 1:
                super().output(self.print_format(evaluated_args[0]))

            user_input = super().get_input()

            if func_name == "inputi":
                if user_input == None:
                    return 0

                try: 
                    return int(user_input)

                except ValueError:
                    return 0

            if func_name == "inputs":
                if user_input == None:
                    return ""
                else:
                    return str(user_input)



        """ Arithmetic operations """
        if func_name in ("+","-","*","/"):
            if len(evaluated_args) != 2:
                super().error(ErrorType.NAME_ERROR, "Arithmetic operations require 2 arguments")

            left = evaluated_args[0]
            right = evaluated_args[1]

            if type(left) is not int or type(right) is not int:
                if func_name != "+":
                    super().error(ErrorType.TYPE_ERROR, "Arguments must be integers")
                if type(left) not in (int, str) or type(right) not in (int, str) or type(left) != type(right):
                    super().error(ErrorType.TYPE_ERROR, "Arguments for the '+' operation must be either string or integer")

            if func_name == "+":
                return left + right
            elif func_name == "-":
                return left - right
            elif func_name == "*":
                return left * right
            elif func_name == "/":
                if right == 0:
                    return 0
                else:
                    return left // right
            

        """ Handle binary logical operations """
        if func_name in ("&&", "||"):
            if len(evaluated_args) != 2:
                super().error(ErrorType.TYPE_ERROR, f"Binary logical operators require exactly 2 inputs, while {len(evaluated_args)} arguments were given")
        
            left = evaluated_args[0]
            right = evaluated_args[1]

            if not isinstance(left, bool) or not isinstance(right, bool):
                super().error(ErrorType.TYPE_ERROR, "Binary logical operators require boolean arguments")

            if func_name == "&&":
                return left and right
            if func_name == "||":
                return left or right


        """ Handle unary logical operations """
        if func_name in ("!"):
            if len(evaluated_args) != 1:
                super().error(ErrorType.NAME_ERROR, f"The '!' operator requires exactly 1 argument given, while {len(evaluated_args)} arguments were given")
            if type(evaluated_args[0]) != bool:
                super().error(ErrorType.TYPE_ERROR, "The '!' operator only acceptse boolean arguments")
            return not evaluated_args[0]


        """ Handle comparison operations """
        if func_name in ("==","!=", "<", ">", "<=", ">="):
            if len(evaluated_args) != 2:
                super().error(ErrorType.NAME_ERROR, "Comparison requires exactly two arguments")

            left = evaluated_args[0]
            right = evaluated_args[1]

            if type(left) != type(right):
                super().error(ErrorType.TYPE_ERROR, f"Comparison arguments are of type {type(left)} and {type(right)}")
            if type(left) in (list, Func_Value, Lambda_Func):
                super().error(ErrorType.TYPE_ERROR, "Cannot compare lists/funcs")
            if func_name == "==":
                return left == right
            if func_name == "!=":
                return left != right

            if type(left) not in (int,str) or type(right) not in (int,str):
                super().error(ErrorType.TYPE_ERROR, "Ordering operators require int or string arguments")
            if func_name == "<":
                return left < right
            if func_name == ">":
                return left > right
            if func_name == "<=":
                return left <= right
            if func_name == ">=":
                return left >= right

        """ ALL LIST OPERATORS """
        """ car returns the first value of a nonempty list """
        if func_name == "car":
            if len(evaluated_args) != 1:
                super().error(ErrorType.NAME_ERROR, "car takes 1 arg")
            arg = evaluated_args[0]
            if type(arg) is not list:
                super().error(ErrorType.TYPE_ERROR, "car takes only list arguments")
            if len(arg) == 0:
                super().error(ErrorType.FAULT_ERROR, "car must not be taken of an empty list FAULT")
            return arg[0]

        """ cdr returns a new list containing every element except the first """
        if func_name == "cdr":
                    if len(evaluated_args) != 1:
                        super().error(ErrorType.NAME_ERROR, "cdr takes 1 arg")
                    arg = evaluated_args[0]
                    if type(arg) is not list:
                        super().error(ErrorType.TYPE_ERROR, "cdr takes only list arguments")
                    if len(arg) == 0:
                        super().error(ErrorType.FAULT_ERROR, "cdr must not be taken of an empty list FAULT")
                    return arg[1:]

        """ cons operator prepends a list with any element """
        if func_name == "cons":
            if len(evaluated_args) != 2:
                super().error(ErrorType.NAME_ERROR, "cons takes 2 args")
            arg1, arg2 = evaluated_args[0], evaluated_args[1]
            if type(arg2) is not list:
                super().error(ErrorType.TYPE_ERROR, "cons arg2 must be list")
            return [arg1] + arg2

        """ append concatenates two lists """
        if func_name == "append":
            if len(evaluated_args) != 2:
                super().error(ErrorType.NAME_ERROR, "append takes 2 args")
            arg1, arg2 = evaluated_args[0], evaluated_args[1]
            if type(arg1) is not list or type(arg2) is not list:
                super().error(ErrorType.TYPE_ERROR, "append must take both list arguments")
            return arg1 + arg2

        """ length returns the number of elements in a list """
        if func_name == "length":
            if len(evaluated_args) != 1:
                super().error(ErrorType.NAME_ERROR, "length takes 1 argument")
            arg = evaluated_args[0]
            if type(arg) is not list:
                super().error(ErrorType.TYPE_ERROR, "length takes only list arguments")
            return len(list)

    def handle_custom_function(self, func_name, evaluated_args):
        key = (func_name, len(evaluated_args))
        if key not in self.func_defs:
            super().error(ErrorType.NAME_ERROR, f"{func_name} with {len(evaluated_args)} arguments was not found")

        func_node = self.func_defs[key]
        param_nodes = func_node.get("args")

        old_scopes = self.scopes
        self.scopes = [{}]

        for param_node, val in zip(param_nodes, evaluated_args):
            self.define_var(param_node.get("name"), val)

        body_node = func_node.get("body")
        final_eval = self.eval_expr(body_node)

        self.scopes = old_scopes
        return final_eval
        