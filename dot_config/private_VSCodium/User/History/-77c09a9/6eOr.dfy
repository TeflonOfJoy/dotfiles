/** Exercise: prove the Gauss formula for some of the first n naturals */

function Sum(n: nat): nat
{
    if n == 0 then 0
    else Sum(n - 1) + n
}

lemma {:induction false} GaussLemma(n: nat)
    ensures Sum(n) == n * (n + 1) / 2
{
    if (n == 0) {
        assert Sum(n) == n;
    } else { // n > 0
        calc {
            Sum(n);
        ==  Sum(n - 1) + n; // by definition
        == { GaussLemma(n - 1); 
             assert GaussLemma(n - 1) == Sum(n - 1);}
        }
    }
}

method Gauss(n: nat) returns (s: nat)
    ensures s == Sum(n)
    ensures s == n * (n + 1) / 2 // use the GaussLemma