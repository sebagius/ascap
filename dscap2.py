from lark import Lark, Transformer

# 1. Define the Grammar (The "What", not the "How")
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

class AscapTransformer(Transformer):
    def __init__(self, scap_namespace):
        self.scap_namespace = scap_namespace

    def _s(self, s): return str(s)[1:-1]

    def _gen_id_oval(self, id_type, local_name):
        return f"oval:{self.scap_namespace}:{id_type}:{local_name}"
    
    def _gen_id_xccdf(self, id_type, local_name):
        return f"xccdf_{self.scap_namespace}_{id_type}_{local_name}"

    def title(self, s): return ("title", self._s(s[0]))
    def version(self, s): return ("version", self._s(s[0]))
    def description(self, s): return ("description", self._s(s[0]))
    def namespace(self, s): return ("namespace", self._s(s[0]))
    def wql(self, s): return ("wql", self._s(s[0]))
    def value(self, s): return ("value", self._s(s[0]))

    def rule_ref(self, s): 
        return ("rule_ref", self._gen_id_xccdf("rule", str(s[0])))

    def check_ref(self, s): 
        return ("check_ref", self._gen_id_oval("def", str(s[0])))

    def group_block(self, args):
        name, *items = args
        print(items)
        return {"type": "group", "id": self._gen_id_xccdf("group", str(name)), "properties": dict(items)}

    def rule_block(self, args):
        name, *items = args
        return {"type": "rule", "id": self._gen_id_xccdf("rule", str(name)), "properties": items} # dict in future

    def check_block(self, args):
        ctype, name, *items = args
        return {"type": f"check_{ctype}", "id": self._gen_id_oval("def", str(name)), "properties": items}  # dict in future

parser = Lark(ascap_grammar, start='start', parser='lalr')
tree = parser.parse(open("test.ascap").read())
data = AscapTransformer("dev.agius.testscap").transform(tree)

print(data)