from lark import Lark, Transformer, v_args

ascap_grammar = r"""
    start: block+

    ?block: group_block | rule_block | check_block

    group_block: "group" NAME "{" group_content+ "}"
    rule_block:  "rule" NAME "{" rule_content+ "}"
    check_block: "check:" TYPE NAME "{" check_content+ "}"

    ?group_content: "title" ESCAPED_STRING        -> title
                  | "rule" NAME                   -> rule_ref

    ?rule_content:  "version" ESCAPED_STRING      -> version
                  | "title" ESCAPED_STRING        -> title
                  | "description" ESCAPED_STRING  -> description
                  | "criteria:" LOGIC "{" check_ref+ "}" -> criteria

    check_ref: "check" NAME

    ?check_content: "namespace" ESCAPED_STRING    -> namespace
                  | "wql" ESCAPED_STRING          -> wql
                  | "expect:" LOGIC "{" expect_content+ "}" -> expect

    ?expect_content: "field" ESCAPED_STRING        -> field
                   | "entity_check" ESCAPED_STRING -> entity_check
                   | "value" ESCAPED_STRING        -> value

    LOGIC: "and" | "or" | "equals" | "not_equal"
    TYPE: "wmi" | "reg" | "file"
    NAME: /[a-zA-Z0-9_-]+/

    COMMENT: /#.*/
    
    %import common.ESCAPED_STRING
    %import common.WS
    %ignore WS
    %ignore COMMENT
"""

class SymbolTracker:
    def __init__(self):
        self.definitions = {}
        self.references = []
    
    def add_definition(self, obj_id, obj_type, line_num):
        self.definitions[obj_id] = {'type': obj_type, 'line': line_num}

    def add_reference(self, to_id, line_num):
        self.references.append({'to': to_id, 'line': line_num})

    def _ref_exists(self, ref_id):
        return ref_id in list(self.definitions.keys())

    def validate_references(self):
        errors = []
        for ref in self.references:
            ref_id = ref['to']
            if self._ref_exists(ref_id):
                continue
            errors.append(f"Reference error {ref_id} on line {ref['line']}")
        
        return errors
            
            

@v_args(meta=True)
class AscapTransformer(Transformer):
    def __init__(self, scap_namespace, symbol_tracker):
        self.scap_namespace = scap_namespace
        self.symbol_tracker = symbol_tracker

    def _s(self, s): return str(s)[1:-1]

    def _gen_id_oval(self, id_type, local_name):
        return f"oval:{self.scap_namespace}:{id_type}:{local_name}"
    
    def _gen_id_xccdf(self, id_type, local_name):
        return f"xccdf_{self.scap_namespace}_{id_type}_{local_name}"

    def title(self, meta, s): return ("title", self._s(s[0]))
    def version(self, meta, s): return ("version", self._s(s[0]))
    def description(self, meta, s): return ("description", self._s(s[0]))
    def namespace(self, meta, s): return ("namespace", self._s(s[0]))
    def wql(self, meta, s): return ("wql", self._s(s[0]))
    def value(self, meta, s): return ("value", self._s(s[0]))

    def rule_ref(self, meta, s): 
        rule_id = self._gen_id_xccdf("rule", str(s[0]))
        self.symbol_tracker.add_reference(rule_id, meta.line)
        return ("rule_ref", rule_id)

    def check_ref(self, meta, s): 
        check_id = self._gen_id_oval("def", str(s[0]))
        self.symbol_tracker.add_reference(check_id, meta.line)
        return ("check_ref", check_id)

    
    def group_block(self, meta, children):
        name, *items = children
        group_id = self._gen_id_xccdf("group", str(name))
        self.symbol_tracker.add_definition(group_id, "group", meta.line)
        return {"type": "group", "id": group_id, "properties": dict(items)}

    def rule_block(self, meta, children):
        name, *items = children
        rule_id = self._gen_id_xccdf("rule", str(name))
        self.symbol_tracker.add_definition(rule_id, "rule", meta.line)
        return {"type": "rule", "id": rule_id, "properties": items} # dict in future

    def check_block(self, meta, children):
        ctype, name, *items = children
        check_id = self._gen_id_oval("def", str(name))
        self.symbol_tracker.add_definition(check_id, "check", meta.line)
        return {"type": f"check_{ctype}", "id": check_id, "properties": items}  # dict in future

parser = Lark(ascap_grammar, start='start', parser='lalr',propagate_positions=True)
tree = parser.parse(open("test.ascap").read())
symbol_tracker = SymbolTracker()
data = AscapTransformer("dev.agius.testscap", symbol_tracker).transform(tree)

for err in symbol_tracker.validate_references():
    print(err)

print(data)