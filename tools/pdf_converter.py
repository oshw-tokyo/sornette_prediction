#!/usr/bin/env python3
"""
PDF軽量化・変換ツール（Claude Code用）
Sornette論文のContext low問題解決
"""

import pdfplumber
import os
import sys
from pathlib import Path

def extract_clean_text(pdf_path, output_path=None):
    """PDFからクリーンなテキストを抽出"""
    
    if not output_path:
        base_name = Path(pdf_path).stem
        output_path = f"{base_name}_extracted.txt"
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    # ページヘッダー追加
                    full_text += f"\n{'='*50}\n"
                    full_text += f"PAGE {page_num}\n"
                    full_text += f"{'='*50}\n\n"
                    
                    # テキスト整理（過度な改行削除）
                    cleaned_text = ' '.join(text.split())
                    full_text += cleaned_text + "\n"
        
        # ファイル保存
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        # サイズ情報表示
        original_size = os.path.getsize(pdf_path) / 1024
        new_size = os.path.getsize(output_path) / 1024
        reduction = (1 - new_size/original_size) * 100
        
        print(f"✅ 変換完了!")
        print(f"   元ファイル: {original_size:.1f} KB")
        print(f"   新ファイル: {new_size:.1f} KB")
        print(f"   削減率: {reduction:.1f}%")
        print(f"   出力先: {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return None

def split_by_sections(text_file, sections=['Abstract', 'Introduction', 'Conclusion', 'References']):
    """テキストをセクション別に分割"""
    
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    base_name = Path(text_file).stem
    sections_found = {}
    
    # セクション分割ロジック
    lines = content.split('\n')
    current_section = 'Header'
    current_content = []
    
    for line in lines:
        # セクション検出
        section_found = None
        for section in sections:
            if section.lower() in line.lower() and len(line.strip()) < 50:
                section_found = section
                break
        
        if section_found:
            # 前のセクション保存
            if current_content:
                sections_found[current_section] = '\n'.join(current_content)
            
            current_section = section_found
            current_content = [line]
        else:
            current_content.append(line)
    
    # 最後のセクション保存
    if current_content:
        sections_found[current_section] = '\n'.join(current_content)
    
    # セクション別ファイル出力
    output_files = []
    for section_name, section_content in sections_found.items():
        if len(section_content.strip()) > 100:  # 空でないセクション
            safe_name = section_name.replace(' ', '_').replace('/', '_')
            output_path = f"{base_name}_{safe_name}.txt"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(section_content)
            
            output_files.append(output_path)
            print(f"📄 セクション保存: {output_path}")
    
    return output_files

def main():
    """メイン実行関数"""
    
    print("🔧 Sornette論文PDF変換ツール")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("使用法: python pdf_converter.py <PDFファイル>")
        print("\nまたは直接実行:")
        pdf_file = input("PDFファイルパスを入力: ").strip()
    else:
        pdf_file = sys.argv[1]
    
    if not os.path.exists(pdf_file):
        print(f"❌ ファイルが見つかりません: {pdf_file}")
        return
    
    # Step 1: PDF → テキスト変換
    print("\n📝 Step 1: PDFをテキストに変換中...")
    text_file = extract_clean_text(pdf_file)
    
    if not text_file:
        print("❌ PDF変換に失敗しました")
        return
    
    # Step 2: セクション分割
    print("\n✂️  Step 2: セクション別に分割中...")
    section_files = split_by_sections(text_file)
    
    print("\n✅ 変換完了!")
    print(f"   メインファイル: {text_file}")
    print(f"   セクション数: {len(section_files)}")
    
    return text_file, section_files

if __name__ == "__main__":
    main()