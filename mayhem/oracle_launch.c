/* Thin ELF launcher for the functional suite (mayhem/run_tests.py, upstream's own absltest suites).
 *
 * mayhem/test.sh runs THIS binary (a project, NON-system ELF under /mayhem) rather than python3
 * directly, so the anti-reward-hack sabotage check (SPEC §6.3) can neuter it: it LD_PRELOADs an
 * _exit(0) constructor into every non-system executable. Neutered, this launcher exits before
 * exec'ing python, no test results are printed, and test.sh reports a failure. Normally it execs
 * python3 on run_tests.py with the source tree on PYTHONPATH. */
#include <stdlib.h>
#include <unistd.h>

#ifndef PYTHON_BIN
#define PYTHON_BIN "/usr/bin/python3"
#endif
#ifndef ORACLE_PATH
#define ORACLE_PATH "/mayhem/mayhem/run_tests.py"
#endif
#ifndef SRC_ROOT
#define SRC_ROOT "/mayhem"
#endif

int main(void) {
    setenv("PYTHONPATH", SRC_ROOT, 1);
    setenv("PYTHONDONTWRITEBYTECODE", "1", 1);
    char *a[] = {(char *)PYTHON_BIN, (char *)"-s", (char *)ORACLE_PATH, (char *)0};
    execv(PYTHON_BIN, a);
    _exit(127);
}
