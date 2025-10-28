# Variant-Text-Compositor
中文名：异文排版器。
一个能够自动处理古籍异文并生成多种排版格式（表格、校勘记、单版本、多版本对照）的TeX预处理工具。

# 背景

在整理古籍中，思考一种方式可以在底本文字中呈现其他版本异文。一开始想用LaTeX编程实现，但是用了ChatGPT编程命令总是各种问题。转变思路后，用Python语言实现了。下面说下这个脚本的使用方法。

# 项目结构

- `input.tex`——输入文件，相当于工作底本
- `main.tex`——经Python脚本处理的输出文件，编译使用
- `preprocess.py`——Python脚本，将input.tex中的版本异文替换成尾注（校勘记），并制作成长表格（可分页长表格）；同时支持替换底本文字和输出对照版
- 编译.bat——批处理命令

# input.tex

## 注册版本

版本注册命令（保留用于其他用途）

``\newcommand{\banbenzhuce}[1]{}``

用法：

``\banbenzhuce{许本,黄本,四库,孙本,沈本,详节}``

放在文档区。

## 正文环境

p参数下需要明确正文段落，才可以生成多列，因此需要将对照的段落放置到一个环境中。这里定义了diben环境，用于存放。

``
\begin{diben}

\banben{關關}[沈本={关关},孙本={官官}]雎鳩，在河之洲。窈窕淑女，君子好逑。
……
\printyiwenlist

\end{diben}
``

## 著录异文

定义banben命令（只输出底本文字）

``\newcommand{\banben}[2][]{#2}``

默认为底本文字添加颜色。

核心命令用法：

``\banben{關關}[沈本={关关},孙本={官官}]``

若使用了未注册的版本，会忽略异文。

## 显示位置

命令：

``\printyiwenlist``

脚本在遇到该命令时，会将此命令與上一个命令之间的版本异文收集起来，换成校勘记和长表格格式。

## 校勘记序号格式

默认使用阿拉伯数字。如想使用中文数字，可启用下面的命令：

``%\renewcommand{\theendnote}{\hskip -2pt〔\zhdigits{\arabic{endnote}}〕\hskip -2pt} % 中文编号带六角括号``

# preprocess.py

## 表格标题

`{chapter_title}`——卷
`{section_title}`——节
`{subsection_title}`——小节

``table_caption = f"异文对照表——{chapter_title}丨{subsection_title}"``

我在整理《广记》项目，它是三级结构。因此我的表格会显示卷和小节标题。

## 底本文字颜色

``result = f"{{\\textcolor{{blue}}{{{base_text}}}}}\\endnote{{{endnote_content}。}}"``

默认使用蓝色（须引入xcolor宏包）

## 长表格

使用tabularray宏包的longtblr环境，长表格自动分页，内容区交替着色。

## 显示/隐藏校勘记

``replacement_content = table_content + "\n\n\\theendnotes"``

默认显示。如不需要显示，可以注释掉：

``replacement_content = table_content + "\n\n%\\theendnotes"``

## 参数

不带参数时，仅输出长表格：

``python preprocess.py``

### -e

``python preprocess.py -e``

校勘记模式：只输出校勘记。没有长表格。

### -r

``python preprocess.py -r``

替换模式：将底本文字替换为指定版本文字，同时输出校勘记。需要在控制台选择要保留的版本。

### -p

``python preprocess.py -p``

对照版模式：使用paracol输出所有版本对照。这个模式会修改页面布局，默认是A4横向，可以在脚本中自定义布局。

``if r'\usepackage[a4paper,landscape]{geometry}' not in content:``
