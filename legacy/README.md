# Legacy Archive

`hello_os_colab_export.txt` preserves the original exported Colab notebook as
historical reference material. It is not part of the supported runtime package.

Reasons it stays outside the executable path:

- It mixes many independent experiments in one large file.
- It contains notebook shell magics and top-level side effects.
- It includes sections that require domain-specific safety review before any
  code promotion.

Promote archive material only by extracting a small, benign unit into the
`hello_os/` package and adding tests that import the real module.
