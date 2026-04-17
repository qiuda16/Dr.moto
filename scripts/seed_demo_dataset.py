import sys


MESSAGE = """
This legacy demo seeder has been deprecated because the old source data contained mojibake.

Use the clean replacement instead:
  py -3.9 scripts/seed_demo_dataset_clean.py

If you need to repair existing demo text after old seeds:
  powershell -ExecutionPolicy Bypass -File scripts/repair_demo_text.ps1
""".strip()


def main() -> None:
    print(MESSAGE)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
