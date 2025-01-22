#!/usr/bin/env python3
import os
import subprocess
import argparse

# 引数を解析する
def parse_args():
    parser = argparse.ArgumentParser(
        description="Export folder structure and code files in Markdown format.",
        epilog="Example: ./export_code.py -e py js -o output.md"
    )
    parser.add_argument(
        "-e", "--extensions", 
        nargs="+", 
        required=True, 
        help="File extensions to include (e.g., py js html). Specify multiple extensions separated by spaces."
    )
    parser.add_argument(
        "-o", "--output", 
        help="Output file (default: standard output). Specify a file path to save the output."
    )
    return parser.parse_args()

# tree コマンドの出力を取得する
def get_tree_structure():
    try:
        tree_output = subprocess.check_output(["tree"], universal_newlines=True)
        return tree_output
    except FileNotFoundError:
        print("Error: 'tree' command not found. Please install it using 'sudo apt install tree'.")
        exit(1)

# 指定した拡張子を持つファイルを再帰的に収集する
def collect_files_by_extension(extensions):
    matched_files = []
    for root, _, files in os.walk("."):
        for file in files:
            if any(file.endswith(f".{ext}") for ext in extensions):
                matched_files.append(os.path.join(root, file))
    return matched_files

# Markdown形式で出力する
def generate_markdown(tree_output, files):
    markdown = []

    # tree コマンドの結果
    markdown.append("# Folder Structure\n")
    markdown.append("## Tree Command Output\n")
    markdown.append("```")
    markdown.append(tree_output)
    markdown.append("```")

    # ファイルの内容
    markdown.append("\n# Extracted Files\n")
    for file in files:
        markdown.append(f"## File: {file}\n")
        markdown.append("```")
        try:
            with open(file, "r") as f:
                markdown.append(f.read())
        except Exception as e:
            markdown.append(f"Error reading file: {e}")
        markdown.append("```")
        markdown.append("\n")

    return "\n".join(markdown)

# メイン処理
def main():
    args = parse_args()

    # tree コマンドの出力を取得
    tree_output = get_tree_structure()

    # 指定した拡張子のファイルを収集
    files = collect_files_by_extension(args.extensions)

    # Markdownを生成
    markdown = generate_markdown(tree_output, files)

    # 出力
    if args.output:
        with open(args.output, "w") as f:
            f.write(markdown)
        print(f"Markdown output saved to {args.output}")
    else:
        print(markdown)

if __name__ == "__main__":
    main()
