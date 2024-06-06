from io import StringIO

import gofai_pddl
from pddl_to_prolog import Rule, PrologProgram

def test_normalization():
    prog = PrologProgram()
    prog.add_fact(gofai_pddl.Atom("at", ["foo", "bar"]))
    prog.add_fact(gofai_pddl.Atom("truck", ["bollerwagen"]))
    prog.add_fact(gofai_pddl.Atom("truck", ["segway"]))
    prog.add_rule(Rule([gofai_pddl.Atom("truck", ["?X"])], gofai_pddl.Atom("at", ["?X", "?Y"])))
    prog.add_rule(Rule([gofai_pddl.Atom("truck", ["X"]), gofai_pddl.Atom("location", ["?Y"])],
                  gofai_pddl.Atom("at", ["?X", "?Y"])))
    prog.add_rule(Rule([gofai_pddl.Atom("truck", ["?X"]), gofai_pddl.Atom("location", ["?Y"])],
                  gofai_pddl.Atom("at", ["?X", "?X"])))
    prog.add_rule(Rule([gofai_pddl.Atom("p", ["?Y", "?Z", "?Y", "?Z"])],
                  gofai_pddl.Atom("q", ["?Y", "?Y"])))
    prog.add_rule(Rule([], gofai_pddl.Atom("foo", [])))
    prog.add_rule(Rule([], gofai_pddl.Atom("bar", ["X"])))
    prog.normalize()
    output = StringIO()
    prog.dump(file=output)
    sorted_output = "\n".join(sorted(output.getvalue().splitlines()))
    assert sorted_output == """\
Atom @object(bar).
Atom @object(bollerwagen).
Atom @object(foo).
Atom @object(segway).
Atom at(foo, bar).
Atom bar(X).
Atom foo().
Atom truck(bollerwagen).
Atom truck(segway).
none Atom at(?X, ?X@0) :- Atom truck(?X), Atom location(?Y), Atom =(?X, ?X@0).
none Atom at(?X, ?Y) :- Atom truck(?X), Atom @object(?Y).
none Atom at(?X, ?Y) :- Atom truck(X), Atom location(?Y), Atom @object(?X).
none Atom q(?Y, ?Y@0) :- Atom p(?Y, ?Z, ?Y, ?Z), Atom =(?Y, ?Y@0), Atom =(?Y, ?Y@1), Atom =(?Z, ?Z@2)."""
