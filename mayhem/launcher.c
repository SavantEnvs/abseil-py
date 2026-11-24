/*
 * launcher.c — tiny ELF shim so each Mayhem target `cmd` is a native executable.
 *
 * absl-py is pure Python and is fuzzed with Atheris (a coverage-guided Python fuzzer that speaks the
 * libFuzzer CLI). Mayhem requires the target `cmd` to be an ELF, so this shim exec()s CPython on the
 * Atheris harness, forwarding every argument unchanged; exec() replaces the process image, so the
 * running process IS the Atheris/libFuzzer harness. With libFuzzer flags it fuzzes; with a single
 * file argument it replays that input once (so it is also its own standalone reproducer).
 *
 * The harness imports absl straight from the source tree (/mayhem, via PYTHONPATH), not from an
 * installed wheel, so a patched source tree is what gets fuzzed and graded. atheris lives in the
 * $HOME-independent /opt/toolchains/python/site (SPEC §6.2 item 8), so any uid can import it.
 * SCRIPT_PATH, SRC_ROOT and SITE_DIR are fixed at compile time by mayhem/build.sh.
 */
#include <stdlib.h>
#include <unistd.h>

#ifndef PYTHON_BIN
#define PYTHON_BIN "/usr/bin/python3"
#endif
#ifndef SCRIPT_PATH
#error "SCRIPT_PATH must be defined"
#endif
#ifndef SRC_ROOT
#define SRC_ROOT "/mayhem"
#endif
#ifndef SITE_DIR
#define SITE_DIR "/opt/toolchains/python/site"
#endif

int main(int argc, char **argv) {
    char **a = (char **)calloc((size_t)argc + 3, sizeof(char *));
    if (!a) return 1;
    setenv("PYTHONPATH", SRC_ROOT ":" SITE_DIR, 1);
    /* never write __pycache__ into the (read-only under Mayhem) source tree */
    setenv("PYTHONDONTWRITEBYTECODE", "1", 1);
    int n = 0;
    a[n++] = (char *)PYTHON_BIN;
    a[n++] = (char *)"-s"; /* ignore any per-user site dir: results must not depend on $HOME */
    a[n++] = (char *)SCRIPT_PATH;
    for (int i = 1; i < argc; i++) a[n++] = argv[i];
    a[n] = (char *)0;
    execv(PYTHON_BIN, a);
    return 127; /* execv only returns on error */
}
