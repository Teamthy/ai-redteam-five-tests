# Security

## Reporting a problem in this repo

If you find a security problem in this code, for example a way the harness
leaks the API key it is given or writes it into `results/`, please don't open
a public issue. Use GitHub's private vulnerability reporting on this
repository (Security tab, "Report a vulnerability"). I'll reply within five
working days.

## Using the harness

Run it only against models and endpoints you own or have written permission
to test. The sample support bot's "internal key" is a made-up string that
exists so the detectors have something to find. It isn't a real credential.

The harness sends your system prompt and the test inputs to whatever
`OPENAI_BASE_URL` points at. Don't point it at a third-party endpoint with a
system prompt you aren't allowed to share with that provider.
