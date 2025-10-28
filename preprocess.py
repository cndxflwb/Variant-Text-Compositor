import re
import sys
import random
import string
import argparse

def generate_random_id(length=8):
    """生成指定长度的随机字母数字字符串"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def process_default_mode(content, versions, chapter_title, section_title, subsection_title):
    """默认模式：使用底本文字，输出长表格"""
    variants = []
    
    def replace_banben(match):
        base_text = match.group(1)
        optional_params = match.group(2) if match.group(2) else ""
        
        if optional_params:
            variant_dict = {}
            variant_dict['base'] = base_text
            
            variant_matches = re.findall(r'(\w+)=\{([^}]*)\}', optional_params)
            for version, variant_text in variant_matches:
                variant_dict[version] = variant_text
            
            variants.append(variant_dict)
            
            endnote_content = f"底本「{base_text}」："
            variant_list = []
            for version in versions:
                if version in variant_dict:
                    variant_list.append(f"{version}作「{variant_dict[version]}」")
            endnote_content += "，".join(variant_list)
            
            result = f"{{\\textcolor{{blue}}{{{base_text}}}}}\\endnote{{ {endnote_content}。}}"
            return result
        else:
            return base_text
    
    banben_pattern = r'\\banben\{([^}]*)\}(?:\[([^]]*)\])?'
    processed_content = re.sub(banben_pattern, replace_banben, content)
    
    # 生成异文表格
    if variants:
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
        table_content += f"  label = {{tblr:{table_caption}}},\n"
        table_content += "]{" + f"colspec = {{cX" + "X" * len(versions) + "}, width = 1\\linewidth, rowhead = 1, row{odd}={black!3},row{1}={black!10},row{1}={font=\\heiti},row{2-Z}={font=\\kaishu}" + "}\n"
        table_content += "\\hline\n"
        table_content += table_header + "\n"
        table_content += "\\hline\n"
        table_content += "\n".join(table_rows) + "\n"
        table_content += "\\hline\n"
        table_content += "\\end{longtblr}"
    else:
        table_content = ""
    
    replacement_content = table_content + "\n\n\\theendnotes"
    final_content = processed_content.replace('\\printyiwenlist', replacement_content)
    
    return final_content, len(variants)

def process_endnote_mode(content, versions):
    """校勘记模式：只输出endnotes"""
    variants = []
    
    def replace_banben(match):
        base_text = match.group(1)
        optional_params = match.group(2) if match.group(2) else ""
        
        if optional_params:
            variant_dict = {}
            variant_dict['base'] = base_text
            
            variant_matches = re.findall(r'(\w+)=\{([^}]*)\}', optional_params)
            for version, variant_text in variant_matches:
                variant_dict[version] = variant_text
            
            variants.append(variant_dict)
            
            endnote_content = f"底本「{base_text}」："
            variant_list = []
            for version in versions:
                if version in variant_dict:
                    variant_list.append(f"{version}作「{variant_dict[version]}」")
            endnote_content += "，".join(variant_list)
            
            result = f"{{\\textcolor{{blue}}{{{base_text}}}}}\\endnote{{ {endnote_content}。}}"
            return result
        else:
            return base_text
    
    banben_pattern = r'\\banben\{([^}]*)\}(?:\[([^]]*)\])?'
    processed_content = re.sub(banben_pattern, replace_banben, content)
    
    # 只保留endnotes，不生成表格
    final_content = processed_content.replace('\\printyiwenlist', '\\theendnotes')
    
    return final_content, len(variants)

def process_replace_mode(content, versions, selected_version):
    """替换模式：将底本文字替换为指定版本的文字"""
    variants = []
    
    def replace_banben(match):
        base_text = match.group(1)
        optional_params = match.group(2) if match.group(2) else ""
        
        if optional_params:
            variant_dict = {}
            variant_dict['base'] = base_text
            
            variant_matches = re.findall(r'(\w+)=\{([^}]*)\}', optional_params)
            for version, variant_text in variant_matches:
                variant_dict[version] = variant_text
            
            variants.append(variant_dict)
            
            # 使用指定版本的文字替换底本文字
            if selected_version in variant_dict:
                replacement_text = variant_dict[selected_version]
                # 用红色标注替换的文字
                result = f"\n{{\\textcolor{{red}}{{{replacement_text}}}}}\\endnote{{底本「{base_text}」，{selected_version}作「{replacement_text}」。}}"
                return result
            else:
                # 如果指定版本没有异文，使用底本文字
                return base_text
        else:
            return base_text
    
    banben_pattern = r'\\banben\{([^}]*)\}(?:\[([^]]*)\])?'
    processed_content = re.sub(banben_pattern, replace_banben, content)
    
    # 替换模式下不生成表格，只保留endnotes
    final_content = processed_content.replace('\\printyiwenlist', '\\theendnotes')
    
    return final_content, len(variants)

def process_parallel_mode(content, versions):
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
    
    # 查找diben环境
    diben_pattern = r'\\begin\{diben\}(.*?)\\end\{diben\}'
    diben_match = re.search(diben_pattern, content, re.DOTALL)
    
    if not diben_match:
        print("错误：未找到diben环境")
        return content, 0
    
    diben_content = diben_match.group(1)
    
    # 移除\printyiwenlist命令
    diben_content = re.sub(r'\\printyiwenlist', '', diben_content)
    
    # 为每个版本生成列内容
    all_versions = ['底本'] + versions
    column_contents = {}
    
    # 处理底本内容
    def process_base_text(match):
        base_text = match.group(1)
        optional_params = match.group(2) if match.group(2) else ""
        return base_text
    
    base_content = re.sub(r'\\banben\{([^}]*)\}(?:\[([^]]*)\])?', process_base_text, diben_content)
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
        
        version_content = re.sub(r'\\banben\{([^}]*)\}(?:\[([^]]*)\])?', process_version_text, diben_content)
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
    
    # 替换原内容中的diben环境为paracol环境
    final_content = content.replace(diben_match.group(0), paracol_content)
    
    # 统计异文数量
    variant_count = len(re.findall(r'\\banben\{[^}]*\}\[[^]]*\]', diben_content))
    
    return final_content, variant_count

def process_tex_file(input_file, output_file, mode='default', selected_version=None):
    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查并添加必要的包
    packages_to_add = []
    
    if r'\usepackage{endnotes}' not in content:
        packages_to_add.append(r'\usepackage{endnotes}')
    
    if mode == 'default' and r'\usepackage{tabularray}' not in content:
        packages_to_add.append(r'\usepackage{tabularray}')
    
    if packages_to_add:
        packages_str = '\n'.join(packages_to_add)
        content = re.sub(
            r'(\\documentclass\{ctexbook\})',
            r'\1\n' + packages_str,
            content
        )
    
    # 提取版本信息
    version_match = re.search(r'\\banbenzhuce\{([^}]+)\}', content)
    versions = []
    if version_match:
        version_text = version_match.group(1)
        versions = [v.strip() for v in version_text.split(',')]
    
    # 根据模式处理内容
    if mode == 'default':
        chapter_match = re.search(r'\\chapter\{([^}]+)\}', content)
        section_match = re.search(r'\\section\{([^}]+)\}', content)
        subsection_match = re.search(r'\\subsection\{([^}]+)\}', content)
        
        chapter_title = chapter_match.group(1) if chapter_match else "未知卷"
        section_title = section_match.group(1) if section_match else "未知节"
        subsection_title = subsection_match.group(1) if subsection_match else "未知小节"
        
        final_content, variant_count = process_default_mode(content, versions, chapter_title, section_title, subsection_title)
        print(f"默认模式：使用底本文字，生成异文对照表")
    elif mode == 'endnote':
        final_content, variant_count = process_endnote_mode(content, versions)
        print(f"校勘记模式：只输出校勘记")
    elif mode == 'replace':
        if selected_version is None:
            # 显示版本列表供用户选择
            print("请选择要使用的版本：")
            print("0. 底本")
            for i, version in enumerate(versions, 1):
                print(f"{i}. {version}")
            
            try:
                choice = int(input("请输入版本序号: "))
                if choice == 0:
                    selected_version = 'base'
                elif 1 <= choice <= len(versions):
                    selected_version = versions[choice-1]
                else:
                    print("无效选择，使用默认底本")
                    selected_version = 'base'
            except ValueError:
                print("输入无效，使用默认底本")
                selected_version = 'base'
        
        final_content, variant_count = process_replace_mode(content, versions, selected_version)
        print(f"替换模式：将底本文字替换为 {selected_version} 版本文字")
    elif mode == 'parallel':
        final_content, variant_count = process_parallel_mode(content, versions)
        print(f"对照版模式：使用paracol输出所有版本对照")
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print(f"处理完成！输出文件: {output_file}")
    print(f"发现 {variant_count} 处异文")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='处理TeX文件中的异文')
    parser.add_argument('input_file', nargs='?', default='input.tex', help='输入TeX文件路径')
    parser.add_argument('output_file', nargs='?', default='main.tex', help='输出TeX文件路径')
    parser.add_argument('-e', '--endnote', action='store_true', help='校勘记模式：只输出校勘记')
    parser.add_argument('-r', '--replace', action='store_true', help='替换模式：将底本文字替换为指定版本文字')
    parser.add_argument('-p', '--parallel', action='store_true', help='对照版模式：使用paracol输出所有版本对照')
    
    args = parser.parse_args()
    
    # 确定处理模式
    if args.endnote:
        mode = 'endnote'
    elif args.replace:
        mode = 'replace'
    elif args.parallel:
        mode = 'parallel'
    else:
        mode = 'default'
    
    process_tex_file(args.input_file, args.output_file, mode)