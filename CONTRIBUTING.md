# Contributing to lightaero

Thank you for your interest in contributing to lightaero! As a research-focused project, we value contributions that improve the accuracy, documentation, and usability of the library.

## Workflow

We follow a standard GitHub flow:

1. **Fork** the repository.
2. **Clone** your fork to your local machine.
3. **Create a branch** for your feature or bug fix: `git checkout -b feature/your-feature-name`.
4. **Implement** your changes.
5. **Run tests** to ensure everything is working as expected: `pytest`. All tests must pass before a pull request can be merged.
6. **Commit** your changes with a clear message and DCO sign-off (see below).
7. **Push** your branch to your fork.
8. **Open a Pull Request** against the `master` branch of the main repository.

## Developer Certificate of Origin (DCO)

To ensure that all contributions are legally cleared for inclusion in this Apache 2.0 licensed project, we require that every commit be signed off using the Developer Certificate of Origin (DCO).

By adding a `Signed-off-by` line to your commit message, you certify the following:

> Developer's Certificate of Origin 1.1
>
> By making a contribution to this project, I certify that:
>
> (a) The contribution was created in whole or in part by me and I
>     have the right to submit it under the open source license
>     indicated in the file; or
>
> (b) The contribution is based upon previous work that, to the best
>     of my knowledge, is covered under an appropriate open source
>     license and I have the right under that license to submit that
>     work with modifications, whether created in whole or in part
>     by me, under the same open source license (unless I am
>     permitted to submit under a different license), as indicated
>     in the file; or
>
> (c) The contribution was provided directly to me by some other
>     person who certified (a), (b) or (c) and I have not modified
>     it.
>
> (d) I understand and agree that this project and the contribution
>     are public and that a record of the contribution (including all
>     personal information I submit with it, including my sign-off) is
>     maintained indefinitely and may be redistributed consistent with
>     this project or the open source license(s) involved.

### How to Sign-Off

Simply use the `-s` or `--signoff` flag when committing:

```bash
git commit -s -m "feat: add new aerodynamic solver"
```

This will append `Signed-off-by: Your Name <your.email@example.com>` to the end of your commit message.

## Code Standards

- Follow PEP 8 for Python code.
- Ensure all new features are documented.
- Add tests for any new functionality.
