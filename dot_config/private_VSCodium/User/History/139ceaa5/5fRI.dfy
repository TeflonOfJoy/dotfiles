/*********************************** 
Lecture 4
    4.1 Lemmas definition and usage
***********************************/

/*  It may be cumbersome to verify programs by just interspersing 
    assertions in the code; also it is often necessary to prove non trivial
    logical implications, which are not established automatically.

    In such cases Dafny provides lemmas. These are ghost objects (namely they are
    just part of the specification, not of the code, hence ignored by the compiler)
    whose syntax resambles that of methods, but the only effect is to produce
    the assertions in the ensures clauses (the thesis), possibly after consuming 
    (namely, verifying in the call context) assertions in the requires clause 
    (hypotheses):

    lemma <lemma name>([<paramteres with types>])
        [requires <hypothesis>]
        ensures <thesis>
    {
        <proof body>
    }

    The proof body may be either empty, when the thesis is establisched automatically, 
    or a direct argument, that is a sequence of assertions, or a case analysis, 
    or an inductive proof. 
    
    To begin with, let us consider the following function:
*/


function More(x: int): int
{
    if x <= 0 then 1
    else More(x - 2) + 3
}

//  We express with a lemma the property that x < More(x) for all integer x, 
//  namely More is a strictly increasing function:

lemma Increasing(x: int)
    // no hypotheses here; if any, use requires
    ensures x < More(x)   // thesis
{} // automatic proof

/*  The proof is automatically found by Dafny; before making this proof explicit,
    let us see a possible use of the lemma while establishing an assertion in the
    body of a method.
*/

method ExampleLemmaUse(a: int)
{
    var b := More(a); // 1.
    Increasing(a);    // 2.
    Increasing(b);    // 3.
    var c := More(b); // 4.
    assert 2 <= c - a; // 5
}

/*  The proof is obtained By calling the lemma with the parameters a and b respectively. 
    Here is a rephrasing of the proof of the final assertion 5 that Dafny computes:

    Proof of: assert 2 <= c - a
        5.   b == More(a)                  { by 1 }
        6.   a < More(a)                   { by 2 }
        7.   b < More(b)                   { by 3 }
        8.   a < More(a) < More(More(a))   { by 5, 6, 7 }
        9.   c == More(More(a))            { by 4, 5 }
        10   a < More(a) < c               { by 8, 9 }
        11   a + 2 <= c                    { by property of < and <= }
        12   2 <= c - a                    { by property of <= }

*/

/*  To have a look into the proof of the lemma Increasing, we can add the instruction
    {:induction false} preventing Dafny from searching it automatically (which is
    only possible in some simple cases, however), and write the proof by hand.
    First we draft the proof as follows:
*/

lemma {:induction false} IncreasingProof(x: int)
    ensures x < More(x)
{
    if x <= 0 {
        // base case: then x <= 0 < 1 == More(x) by def.
        // nothing to prove
    }
    else { // 0 < x
        IncreasingProof(x - 2); // then
        // x - 2 < More(x - 2)          { by ind. hyp. }
        // x + 1 < More(x - 2) + 3      { adding 3 to both sides }
        // x + 1 < More(x)              { def. of More }
        // x < More(x)                  { by trans. of < }
    }
}

/*  This proof is accpted, but it is still implicit, performing the steps
    which we have guessed and written as comments. In the next proof, we let
    Dafny to check the single steps explicitly:
*/

lemma {:induction false} IncreasingVerbose(x: int)
    ensures x < More(x)
{
    if x <= 0 {
        assert More(x) == 1; // def. of More
        assert x < More(x); // since x <= 0 < 1 == More(x)
    } else {
        assert 0 < x && More(x) == More(x - 2) + 3; // def. of More
        IncreasingVerbose(x - 2); // ind. hyp.
        assert x - 2 < More(x - 2); 
        assert x + 1 < More(x - 2) + 3; // adding 3 to both sides
        assert x + 1 < More(x); // def. of More
        assert x < More(x);     // by trans. of <
    }
    assert x < More(x);
}

/*  Reference: based on Leino, chapter 5 paragraphs 5.0 - 5.2.
*/