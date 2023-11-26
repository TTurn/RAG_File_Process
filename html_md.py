# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import pandas as pd
import uuid
from langchain.schema import Document
from langchain.text_splitter import CharacterTextSplitter, MarkdownHeaderTextSplitter


def split_md(md_content):
    headers_to_split_on = [
                           ("#", "Header 1"),
                           ("##", "Header 2"),
                           ("###", "Header 3"),
                           ("####", "Header 4"),
                           ("#####", "Header 5"),
                           ("######", "Header 6"),
                       ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    text_split = CharacterTextSplitter(
                                       separator="\n",
                                       chunk_size=2000,
                                       chunk_overlap=100,
                                       length_function=len,
                                      )
    md_header_splits = markdown_splitter.split_text(md_content)
    return md_header_splits
    #splits = text_split.split_documents(md_header_splits)
    #return splits

def handle_table_data(table):
    #多个表的数据处理在一个列表里
    data = []
    for pd_data in table:
        kv_dict = {}
        rows, cols = pd_data.shape
        #print(rows, cols)
        for i in range(rows):
            for j in range(cols):
                pd_data.iloc[i,j] = str(pd_data.iloc[i,j]).replace("\t"," ")
        if rows >=1:
            kv_dict[pd_data.columns[0]] = " ".join(pd_data.iloc[:, 0])
            for i in range(rows):
                for j in range(1,cols):
                    kv_dict[pd_data.iloc[i,0]+" "+pd_data.columns[j]] = pd_data.iloc[i,j]
        else:
            data.append(" ".join(pd_data.columns))
        for k,v in kv_dict.items():
            data.append("问题："+k+"，答案:"+v)
    return data


def merge_table(table1, table2):
    # 将table2的表头作为新表格的第一行数据
    table2_header = table2.columns.values
    table2_values = table2.values
    table2_header_df = pd.DataFrame([table2_header], columns=table1.columns)
    table2_values_df = pd.DataFrame(table2_values, columns=table1.columns)
    # 将table2的数据添加到table1的下方
    table3 = pd.concat([table1, table2_header_df, table2_values_df], axis=0, ignore_index=True)
    return table3

def handle_table(table):
    #相邻表格处理
    pre_pd_data = pd.DataFrame()
    for i, t in enumerate(table):
        if pd.read_html(str(t), header=0)==[]:
            continue
        pre_pd_data = pd.read_html(str(t), header=0)[0]
        table = table[i:]
        break
    #pre_pd_data = pd.read_html(str(table[0]), header=0)[0]
    if pre_pd_data.empty:
        return []
    pre_cols = pre_pd_data.shape[1]
    table_data = [pre_pd_data]
    for i, item in enumerate(table):
        if i == 0:continue
        pd_data = pd.read_html(str(item), header=0)[0]
        if pd_data.shape[1] == pre_cols:
            tables = merge_table(pre_pd_data, pd_data)
            table_data[-1] = tables
            pre_pd_data = tables
            pre_cols = tables.shape[1]
        else:
            table_data.append(pd_data)
            pre_pd_data = pd_data
            pre_cols = pd_data.shape[1]
    return table_data


def extract_html(out_file, text_split):
    # 读取HTML文件
    with open(out_file, 'r') as file:
        html = file.read()

    # 创建BeautifulSoup对象
    # help(BeautifulSoup)
    soup = BeautifulSoup(html, 'html5lib')
    all_data = []
    pretag = None
    # 根据标签读取表格和string数据
    for tag in soup.find_all():
        # 排除所有不包含文本信息的tag
        if not tag.name in ['a', 'abbr', 'acronym', 'address', 'b', 'bdi', 'bdo', 'big', 'blockquote', 'body', 'button',
                            'caption', 'cite', 'code', 'data', 'dd', 'del', 'dfn', 'div', 'dl', 'dt', 'em',
                            'figcaption', 'figure', 'footer', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header', 'hgroup',
                            'i', 'ins', 'kbd', 'label', 'legend', 'li', 'main', 'mark', 'nav', 'noscript', 'ol',
                            'optgroup', 'option', 'p', 'pre', 'q', 'rp', 'rt', 'ruby', 's', 'samp', 'section', 'select',
                            'small', 'span', 'strong', 'sub', 'summary', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th',
                            'thead', 'time', 'title', 'tr', 'u', 'ul', 'var']:
            continue
        # 找出表格数据
        if tag.name == "table":
            all_data.append(["table", tag, tag.name])
            pretag = tag
        # 表格标签的子标签过滤
        elif tag.find_parents("table"):
            continue
        else:
            # 标签包含表格标签的过滤
            child_tag_names = [t.name for t in tag.descendants]
            if "table" in child_tag_names:
                continue
            else:
                # 如果当前标签是前标签的子标签，则不需再次添加文本。
                if pretag != None and pretag in tag.parents:
                    continue
                if len(tag.get_text().strip()) == 0:
                    continue
                if tag.name == "title":
                    continue
                all_data.append(["string", tag.get_text().strip(), tag.name])
                pretag = tag
    ###对表格数据和string数据分别处理，分别对相邻表格之间的合并，相邻string之间合并进行判断
    handle_data = []
    table_data = []
    string_data = ""
    for item in all_data:
        header = ["h1", "h2", "h3", "h4", "h5", "h6"]
        if item[2] in header:
            item[1] = (header.index(item[2])+1)*"#"+" "+item[1]
        if item[0] == "table":
            if len(string_data) != 0:
                handle_data.append(["string", string_data])
                string_data = ""
            table_data.append(item[1])
        else:
            if len(table_data) != 0:
                handle_data.append(["table", handle_table(table_data)])
                table_data = []
            string_data += item[1] + "\n"
    if len(string_data) != 0:
        handle_data.append(["string", string_data])
    if len(table_data) != 0:
        handle_data.append(["table", handle_table(table_data)])
    ###对合并的表格数据进行处理
    all_data = []
    for item in handle_data:
        if item[0] == "string":
            splits = split_md(item[1])
            all_data += splits
        else:
            for item in handle_table_data(item[1]):
                uid = uuid.uuid1()
                metadata = {"source": filename, "uuid": str(uid)}
                page_content = item
                document = Document(page_content=page_content, metadata=metadata)
                all_data.append(document)

    return all_data

filename = "香粉盒版蜜粉.html"
text_split = CharacterTextSplitter(
                        separator="\n",
                        chunk_size=2000,
                        chunk_overlap=100,
                        length_function=len,
                                      )

documents = extract_html(filename, text_split)
for item in documents:
    print(item)