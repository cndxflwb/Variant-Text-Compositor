import re
import sys
import random
import string
import argparse

def generate_random_id(length=8):
    """生成指定长度的随机字母数字字符串"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def extract_versions(content):
    """从内容中提取版本信息"""
    version_match = re.search(r'\\banbenzhuce\{([^}]+)\}', content)
    versions = []
    if version_match:
        version_text = version_match.group(1)
        versions = [v.strip() for v in version_text.split(',')]
    return versions

def find_section_titles(content, position):
    """在内容中查找给定位置之前的章节标题"""
    content_before = content[:position]
    
    # 查找最近的章节标题
    chapter_match = None
    section_match = None
    subsection_match = None
    
    # 查找所有章节标题及其位置
    for match in re.finditer(r'\\chapter\{([^}]+)\}', content_before):
        chapter_match = match
    
    for match in re.finditer(r'\\section\{([^}]+)\}', content_before):
        section_match = match
    
    for match in re.finditer(r'\\subsection\{([^}]+)\}', content_before):
        subsection_match = match
    
    chapter_title = chapter_match.group(1) if chapter_match else "未知卷"
    section_title = section_match.group(1) if section_match else "未知节"
    subsection_title = subsection_match.group(1) if subsection_match else "未知小节"
    
    return chapter_title, section_title, subsection_title

def process_banben_commands(content, versions, mode='table', selected_version=None):
    """处理banben命令的核心函数"""
    variants = []
    
    def replace_banben(match):
        base_text = match.group(1)
        optional_params = match.group(2) if match.group(2) else ""
        
        if optional_params:
            variant_dict = {'base': base_text}
            
            variant_matches = re.findall(r'(\w+)=\{([^}]*)\}', optional_params)
            for version, variant_text in variant_matches:
                variant_dict[version] = variant_text
            
            variants.append(variant_dict)
            
            if mode == 'table' or mode == 'endnote':
                # 表格模式或校勘记模式：使用底本文字，蓝色标注
                endnote_content = f"底本「{base_text}」："
                variant_list = []
                for version in versions:
                    if version in variant_dict:
                        variant_list.append(f"{version}作「{variant_dict[version]}」")
                endnote_content += "，".join(variant_list)
                
                result = f"{{\\textcolor{{blue}}{{{base_text}}}}}\\endnote{{ {endnote_content}。}}"
                return result
            elif mode == 'replace':
                # 替换模式：使用指定版本文字，红色标注
                if selected_version in variant_dict:
                    replacement_text = variant_dict[selected_version]
                    result = f"{{\\textcolor{{red}}{{{replacement_text}}}}}\\endnote{{底本「{base_text}」，{selected_version}作「{replacement_text}」。}}"
                    return result
                else:
                    return base_text
        else:
            return base_text
    
    banben_pattern = r'\\banben\{([^}]*)\}(?:\[([^]]*)\])?'
    processed_content = re.sub(banben_pattern, replace_banben, content)
    
    return processed_content, variants

def generate_variant_table(variants, versions, chapter_title, subsection_title):
    """生成异文对照表"""
    if not variants:
        return ""
    
    table_header = "序号 & 底本 & " + " & ".join(versions) + " \\\\"
    table_rows = []
    for i, variant in enumerate(variants, 1):
        row_data = [str(i)]
        row_data.append(variant['base'])
        for version in versions:
            if version in variant:
                row_data.append(variant[version])
            else:
                row_data.append("")
        table_rows.append(" & ".join(row_data) + " \\\\")
    
    table_caption = f"异文对照表——{chapter_title}丨{subsection_title}"
    table_content = "\\begin{longtblr}[\n"
    table_content += "  theme = fancy,\n"
    table_content += f"  caption = {{{table_caption}}},\n"
    table_content += f"  label = {{tblr:{generate_random_id(8)}}},\n"
    table_content += "]{" + f"colspec = {{cX" + "X" * len(versions) + "}, width = 1\\linewidth, rowhead = 1, row{odd}={black!3},row{1}={black!10},row{1}={font=\\heiti},row{2-Z}={font=\\kaishu}" + "}\n"
    table_content += "\\hline\n"
    table_content += table_header + "\n"
    table_content += "\\hline\n"
    table_content += "\n".join(table_rows) + "\n"
    table_content += "\\hline\n"
    table_content += "\\end{longtblr}"
    
    return table_content

def process_table_mode(content, versions):
    """对照表模式：使用底本文字，为每个diben环境输出独立的长表格"""
    
    # 查找所有的diben环境
    diben_pattern = r'(\\begin\{diben\}.*?\\end\{diben\})'
    
    def process_single_diben(match):
        full_diben_match = match.group(0)
        diben_start_pos = match.start()
        
        # 提取diben环境内的内容
        inner_match = re.search(r'\\begin\{diben\}(.*?)\\end\{diben\}', full_diben_match, re.DOTALL)
        if not inner_match:
            return full_diben_match
            
        diben_content = inner_match.group(1)
        
        # 处理banben命令
        processed_content, variants = process_banben_commands(diben_content, versions, 'table')
        
        # 为当前diben环境生成异文表格
        if variants:
            # 查找当前diben环境所在的章节标题
            chapter_title, section_title, subsection_title = find_section_titles(content, diben_start_pos)
            table_content = generate_variant_table(variants, versions, chapter_title, subsection_title)
        else:
            table_content = ""
        
        replacement_content = table_content# + "\n\n\\theendnotes"
        final_diben_content = processed_content.replace('\\printyiwenlist', replacement_content)
        
        return f"\\begin{{diben}}{final_diben_content}\\end{{diben}}"
    
    # 处理每个diben环境
    processed_content = re.sub(diben_pattern, process_single_diben, content, flags=re.DOTALL)
    
    return processed_content

def process_endnote_mode(content, versions):
    """校勘记模式：只输出endnotes"""
    # 处理banben命令
    processed_content, variants = process_banben_commands(content, versions, 'endnote')
    
    # 只保留endnotes，不生成表格
    final_content = processed_content.replace('\\printyiwenlist', '\\theendnotes')
    
    return final_content, len(variants)

def process_replace_mode(content, versions, selected_version):
    """替换模式：将底本文字替换为指定版本的文字"""
    # 处理banben命令
    processed_content, variants = process_banben_commands(content, versions, 'replace', selected_version)
    
    # 替换模式下不生成表格，只保留endnotes
    final_content = processed_content.replace('\\printyiwenlist', '\\theendnotes')
    
    return final_content, len(variants)

def process_paracol_mode(content, versions):
    """对照版模式：将diben环境转换为paracol环境，生成多版本对照"""
    
    # 确保加载必要的包
    if r'\usepackage{paracol}' not in content:
        content = re.sub(
            r'(\\documentclass\{ctexbook\})',
            r'\1\n\\usepackage{paracol}',
            content
        )
    
    # 添加横向页面的geometry设置
    if r'\usepackage[a4paper,landscape]{geometry}' not in content:
        content = re.sub(
            r'(\\documentclass\{ctexbook\})',
            r'\1\n\\usepackage[a4paper,landscape]{geometry}',
            content
        )
    
    # 查找所有的diben环境
    diben_pattern = r'\\begin\{diben\}(.*?)\\end\{diben\}'
    diben_matches = list(re.finditer(diben_pattern, content, re.DOTALL))
    
    if not diben_matches:
        print("错误：未找到diben环境")
        return content, 0
    
    total_variant_count = 0
    
    # 从后往前处理，避免位置变动影响
    for match in reversed(diben_matches):
        diben_content = match.group(1)
        
        # 移除\printyiwenlist命令
        diben_content_clean = re.sub(r'\\printyiwenlist', '', diben_content)
        
        # 为每个版本生成列内容
        all_versions = ['底本'] + versions
        column_contents = {}
        
        # 处理底本内容
        def process_base_text(match):
            base_text = match.group(1)
            optional_params = match.group(2) if match.group(2) else ""
            return base_text
        
        base_content = re.sub(r'\\banben\{([^}]*)\}(?:\[([^]]*)\])?', process_base_text, diben_content_clean)
        column_contents['底本'] = base_content
        
        # 处理其他版本
        for version in versions:
            def process_version_text(match, ver=version):
                base_text = match.group(1)
                optional_params = match.group(2) if match.group(2) else ""
                
                if optional_params:
                    variant_dict = {}
                    variant_matches = re.findall(r'(\w+)=\{([^}]*)\}', optional_params)
                    for v, variant_text in variant_matches:
                        variant_dict[v] = variant_text
                    
                    if ver in variant_dict:
                        # 用红色标注异文
                        return "{\\textcolor{red}{" + variant_dict[ver] + "}}"
                    else:
                        return base_text
                else:
                    return base_text
            
            version_content = re.sub(r'\\banben\{([^}]*)\}(?:\[([^]]*)\])?', process_version_text, diben_content_clean)
            column_contents[version] = version_content
        
        # 构建paracol环境
        paracol_content = "\\begin{paracol}{" + str(len(all_versions)) + "}\n"
        paracol_content += "\\setlength{\\parindent}{0em}\n"  # 取消对照列的缩进
        
        # 添加各列内容
        for i, version in enumerate(all_versions):
            if i > 0:
                paracol_content += "\\switchcolumn\n"
            paracol_content += f"\\textbf{{{version}}}\n"
            paracol_content += column_contents[version]
        
        paracol_content += "\n\\end{paracol}"
        
        # 替换原内容中的当前diben环境为paracol环境
        content = content[:match.start()] + paracol_content + content[match.end():]
        
        # 统计当前diben环境中的异文数量
        variant_count = len(re.findall(r'\\banben\{[^}]*\}\[[^]]*\]', diben_content))
        total_variant_count += variant_count
    
    return content, total_variant_count

def add_required_packages(content, mode):
    """添加必要的LaTeX包"""
    packages_to_add = []
    
    if r'\usepackage{endnotes}' not in content:
        packages_to_add.append(r'\usepackage{endnotes}')
    
    if mode == 'table' and r'\usepackage{tabularray}' not in content:
        packages_to_add.append(r'\usepackage{tabularray}')
    
    if packages_to_add:
        packages_str = '\n'.join(packages_to_add)
        content = re.sub(
            r'(\\documentclass\{ctexbook\})',
            r'\1\n' + packages_str,
            content
        )
    
    return content

def select_version_interactive(versions):
    """交互式选择版本"""
    print("请选择要使用的版本：")
    print("0. 底本")
    for i, version in enumerate(versions, 1):
        print(f"{i}. {version}")
    
    try:
        choice = int(input("请输入版本序号: "))
        if choice == 0:
            return 'base'
        elif 1 <= choice <= len(versions):
            return versions[choice-1]
        else:
            print("无效选择，使用默认底本")
            return 'base'
    except ValueError:
        print("输入无效，使用默认底本")
        return 'base'

def process_tex_file(input_file, output_file, mode='table', selected_version=None):
    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 添加必要的包
    content = add_required_packages(content, mode)
    
    # 提取版本信息
    versions = extract_versions(content)
    
    # 根据模式处理内容
    if mode == 'table':
        final_content = process_table_mode(content, versions)
        print(f"对照表模式：使用底本文字，为每个diben环境生成独立的异文对照表")
    elif mode == 'endnote':
        final_content, variant_count = process_endnote_mode(content, versions)
        print(f"校勘记模式：只输出校勘记，发现 {variant_count} 处异文")
    elif mode == 'replace':
        if selected_version is None:
            selected_version = select_version_interactive(versions)
        
        final_content, variant_count = process_replace_mode(content, versions, selected_version)
        print(f"替换模式：将底本文字替换为 {selected_version} 版本文字，发现 {variant_count} 处异文")
    elif mode == 'paracol':
        final_content, variant_count = process_paracol_mode(content, versions)
        print(f"对照版模式：使用paracol输出所有版本对照，发现 {variant_count} 处异文")
    
    # 格式化diben环境（仅对非paracol模式）
    if mode != 'paracol':
        final_content = re.sub(r'\\begin{diben}', r'\\begin{diben}\n', final_content)
        final_content = re.sub(r'\\end{diben}', r'\n\\end{diben}', final_content)

    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print(f"处理完成！输出文件: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='处理TeX文件中的异文')
    parser.add_argument('input_file', nargs='?', default='input.tex', help='输入TeX文件路径')
    parser.add_argument('output_file', nargs='?', default='main.tex', help='输出TeX文件路径')
    parser.add_argument('-t', '--table', action='store_true', help='对照表模式：使用底本文字，生成异文对照表')
    parser.add_argument('-e', '--endnote', action='store_true', help='校勘记模式：只输出校勘记')
    parser.add_argument('-r', '--replace', action='store_true', help='替换模式：将底本文字替换为指定版本文字')
    parser.add_argument('-p', '--paracol', action='store_true', help='对照版模式：使用paracol输出所有版本对照')
    
    args = parser.parse_args()
    
    # 确定处理模式
    if args.endnote:
        mode = 'endnote'
    elif args.replace:
        mode = 'replace'
    elif args.paracol:
        mode = 'paracol'
    elif args.table:
        mode = 'table'
    else:
        mode = 'table'  # 默认模式改为对照表模式
    
    process_tex_file(args.input_file, args.output_file, mode)