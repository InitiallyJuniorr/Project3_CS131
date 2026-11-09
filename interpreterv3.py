from intbase import InterpreterBase, ErrorType
from brewparse import parse_program


class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.func_defs = {}
        self.scopes = [{}]

    def run(self, program):
        self.func_defs = {}
        self.scopes = [{}]

        ast = parse_program(program)

        funcs = ast.get("functions") or []
        main_func_node = None
        for func in funcs:
            func_name = func.get("name")

        # Check duplicate function names 
            if func_name in self.func_defs:
                super().error(ErrorType.NAME_ERROR, f"Duplicate function definition found: {func_name}")

            self.func_defs[func_name] = func

        # Call error if there is no main function 
        if "main" not in self.func_defs:
            super().error(ErrorType.NAME_ERROR, "No main function found")
        else: 
            main_func_node = self.func_defs["main"]

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
        return str(val)

    def eval_expr(self, node):
        if node.elem_type == InterpreterBase.INT_NODE:
            return node.get("val") 

        if node.elem_type == InterpreterBase.STRING_NODE:
            return node.get("val")

        if node.elem_type == InterpreterBase.BOOL_NODE:
            return node.get("val")

        if node.elem_type == InterpreterBase.LIST_NODE:
            return [self.eval_expr(elem) for elem in node.get("elements")] or []

        if node.elem_type == InterpretBase.LAMBDA_NODE:
            return node.get("val")

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
            return self.get_var(var_name)

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
        func_name = fcall_node.get("fn").get("name")
        """ Handle function and variable overlapping names """
        var_overlap = False
        for scope in reversed(self.scopes):
            if func_name in scope:
                var_overlap = True
                break
        
        if var_overlap:
            super().error(ErrorType.TYPE_ERROR, f" Variable {func_name} is not a function, plz don't call it")

        func_args = fcall_node.get("args")
        evaluated_args = [self.eval_expr(arg) for arg in func_args]

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
                super().error(ErrorType.TYPE_ERROR, "Arithmetic operations require 2 arguments")

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
                super().error(ErrorType.TYPE_ERROR, f"The '!' operator requires exactly 1 argument given, while {len(evaluated_args)} arguments were given")
            if type(evaluated_args[0]) != bool:
                super().error(ErrorType.TYPE_ERROR, "The '!' operator only acceptse boolean arguments")
            return not evaluated_args[0]


        """ Handle comparison operations """
        if func_name in ("==","!=", "<", ">", "<=", ">="):
            if len(evaluated_args) != 2:
                super().error(ErrorType.TYPE_ERROR, "Comparison requires exactly two arguments")

            left = evaluated_args[0]
            right = evaluated_args[1]

            if type(left) != type(right):
                super().error(ErrorType.TYPE_ERROR, f"Comparison arguments are of type {type(left)} and {type(right)}")
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



        """ Handle user specified functions """
        if func_name in self.func_defs:
            return self.handle_custom_function(func_name, evaluated_args)

        """ Handle unkown functions """ 
        super().error(ErrorType.NAME_ERROR, f"Unknown function {func_name}")

    def handle_custom_function(self, func_name, evaluated_args):
        func_node = self.func_defs[func_name]
        param_nodes = func_node.get("args")

    # Input mismatch
        if len(param_nodes) != len(evaluated_args):
            super().error(ErrorType.NAME_ERROR, f"Function {func_name} expected {len(param_nodes)} inputs, and received {len(evaluated_args)}")

        old_scopes = self.scopes
        self.scopes = [{}]

        for param_node, val in zip(param_nodes, evaluated_args):
            self.define_var(param_node.get("name"), val)

        body_node = func_node.get("body")
        final_eval = self.eval_expr(body_node)

        self.scopes = old_scopes
        return final_eval
        