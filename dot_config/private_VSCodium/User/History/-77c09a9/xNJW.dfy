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
        GaussLemma(n - 1); 
        calc {
            Sum(n);
        ==  Sum(n - 1) + n; // by definition
        == (n - 1) * n / 2 + n; // by induction hypothesis
        == (n - 1) * n / 2 + n * 2 / 2;
        == (n - 1) * n / 2 + 2 * n / 2;
        == ((n - 1) * n + 2 * n) / 2;
        == (n * n - n + 2 * n) / 2;
        == (n * n + n) / 2;
        == n * (n + 1) / 2;
        }
    }
}

method Gauss(n: nat) returns (s: nat)
    ensures s == Sum(n)
    ensures s == n * (n + 1) / 2 // use the GaussLemma