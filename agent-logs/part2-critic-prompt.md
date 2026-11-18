# Part II: the critic's brief

Every round used a **new critic session**, so no critic had seen the code being written or
reviewed it before. Each one received the same core brief; from round 2 on it also received
the earlier critiques and was asked to re-run their exact inputs.

> You are the CRITIC in a generator–critic loop. You did NOT write this code. Another agent
> did, and it believes the code is correct. Assume it has bugs and find them. Every finding
> must be reproducible.
>
> READ-ONLY ROLE (hard rule): you must not edit, create or delete any file in the repository,
> and you must not commit, stage, stash, checkout or change branches. You MAY read files, run
> `git diff`/`git log`, run the test suite, and run throwaway Python probes.
>
> THE RUBRIC: docs/RUBRIC.md. Judge strictly against it: correctness, tests, clarity, with
> severities blocker / major / minor. ACCEPT only if no blockers and no majors remain.
>
> OUTPUT: verdict, findings (severity, exact input, actual vs expected, why it matters,
> one-line fix), rubric check, what is good.

Two lines were added in later rounds:

- **Round 3 and 4:** the scope decisions I had made (units not pluralised, item sizes not
  scaled, factor limited to 0.01–100, decimal commas left unchanged) were listed so the critic
  would not count them as findings, while still being allowed to flag a consequence that
  produced a wrong amount.
- **Round 3 and 4:** "Do not invent problems to justify a REVISE; if the code meets the
  rubric, ACCEPT it." This was added so that a REVISE meant a real problem and an ACCEPT meant
  a real sign-off, not a critic trying to look useful.

The critic's reviews are committed unedited in `reviews/critique-round-1.md` to `-4.md`.
I committed them, since the critic itself could not write to the repository.
