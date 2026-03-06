# Sublingo i18n workflow

- Source strings live in Python code and must stay in English.
- Use `self.tr("...")` or `QCoreApplication.translate("Context", "...")` for Qt-visible text.
- Update `.ts` files with `uv run pyside6-lupdate src/sublingo/**/*.py -ts src/sublingo/i18n/sublingo_en.ts src/sublingo/i18n/sublingo_zh_Hans.ts`.
- Compile `.qm` files with `uv run pyside6-lrelease src/sublingo/i18n/sublingo_en.ts src/sublingo/i18n/sublingo_zh_Hans.ts`.
- Keep `sublingo_en.ts` as an identity translation and put Simplified Chinese text in `sublingo_zh_Hans.ts`.
