#!/usr/bin/env python3
"""Replace ```mermaid fences in a markdown file with rendered SVGs (via kroki.io).
Prints the path to convert (original file, unchanged, if no mermaid blocks found;
otherwise a sibling .rendered.md file). SVGs are cached in <name>_diagrams/ next
to the source file, keyed by a hash of the diagram source, so reruns are free.
"""
import sys, os, re, hashlib, subprocess

FENCE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)


def render(md_path: str) -> str:
    with open(md_path) as f:
        text = f.read()

    src_dir = os.path.dirname(md_path) or "."
    base = os.path.splitext(os.path.basename(md_path))[0]
    diagrams_dir = os.path.join(src_dir, f"{base}_diagrams")

    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        count += 1
        # weasyprint drops <foreignObject>, so force plain SVG text labels
        code = '%%{init: {"htmlLabels": false, "flowchart": {"htmlLabels": false}}}%%\n' + m.group(1)
        digest = hashlib.sha1(code.encode()).hexdigest()[:8]
        svg_name = f"diagram-{count}-{digest}.svg"
        svg_path = os.path.join(diagrams_dir, svg_name)
        if not os.path.exists(svg_path):
            os.makedirs(diagrams_dir, exist_ok=True)
            subprocess.run(
                [
                    "curl", "-sS", "--max-time", "30",
                    "-X", "POST", "-H", "Content-Type: text/plain",
                    "--data-binary", "@-",
                    "https://kroki.io/mermaid/svg", "-o", svg_path,
                ],
                input=code.encode(),
                check=True,
            )
        abs_path = os.path.abspath(svg_path)
        return f"\n::: {{.mermaid-diagram}}\n![]({abs_path})\n:::\n"

    new_text, n = FENCE.subn(repl, text)
    if n == 0:
        return md_path

    out_path = os.path.join(src_dir, f".{base}.rendered.md")
    with open(out_path, "w") as f:
        f.write(new_text)
    return out_path


if __name__ == "__main__":
    print(render(sys.argv[1]))
