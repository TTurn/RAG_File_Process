import fitz
import os
from langchain.text_splitter import MarkdownHeaderTextSplitter, CharacterTextSplitter

def split_md(md_content, header):
    headers_to_split_on = [
                           ("#", "Header 1"),
                           ("##", "Header 2"),
                           ("###", "Header 3"),
                           ("####", "Header 4"),
                           ("#####", "Header 5"),
                           ("######", "Header 6"),
                       ]
    headers_to_split_on = headers_to_split_on[:len(header)]
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

def pdf_modify(filename):

    fw = open("output.md", "w")
    pdf_page = fitz.open(filename)
    output_path = ".".join(filename.split(".")[:-1])
    if not os.path.exists(output_path):
        os.mkdir(output_path)
    print(output_path)

    rest = []
    #记录字体大小及该大小字体框数量
    font_size_dict= {0: 0}
    for i, page in enumerate(pdf_page):
        page_rest = []
        print("第"+str(i+1)+"页=======")
        blocks = page.get_text("dict")["blocks"]
        j = 0
        for block in blocks:
            if "image" in block:
                #对小图片进行过滤
                if block["size"] < 500000:
                    continue
                #图片替换文字
                page_rest.append(["图片"+str(i+1)+"_"+str(j)+"."+block["ext"], block["bbox"], 0])
                image_path = output_path+"/"+str(i+1)+"_"+str(j)+"."+block["ext"]
                with open(image_path, "wb") as f:
                    f.write(block["image"])
                j += 1
                #图片转换后文字大小为0
                font_size_dict[0] += 1

            elif "lines" in block:
                text = ""
                for line in block["lines"]:
                    span_lst = []
                    for span in line["spans"]:
                        span_lst.append(span["text"])
                    text += "\t" + " ".join(span_lst)
                size = block["lines"][0]["spans"][0]["size"]
                if size not in font_size_dict:
                    font_size_dict[size] = 1
                else:
                    font_size_dict[size] += 1
                position = block["bbox"]
                page_rest.append([text, position, size])
            else:
                print(block)
        rest.append(page_rest)
    rest_sort = []
    for item in rest:
        sorted_lst = sorted(item, key=lambda x: x[1][1])
        rest_sort.append(sorted_lst)
    print(font_size_dict)
    #根据出现次数进行排序
    font_size_sort = dict(sorted(font_size_dict.items(), key=lambda x: x[0], reverse=True))
    print(font_size_sort)
    total = sum(font_size_sort.values())
    print(total)
    #定义文档多级标题
    header = []
    #从大到小进行比例计算，标题的比例小于10%
    for size, num in font_size_sort.items():
        if num/total > 0.1:
            break
        else:
            header.append(size)
        if len(header)==6:break
    print(header)

    for i, item in enumerate(rest_sort):
        for re in item:
            #根据header进行md标题定义
            if re[2] in header:
                tab = (header.index(re[2])+1)*"#"
            else:
                tab = ""
            fw.write(tab + " " + re[0].strip()+"\n")

    fw.close()

    with open("output.md", "r")as f:
        texts = f.readlines()
    content = "".join(texts)
    splits = split_md(content, header)
    with open("split.txt", "w")as fw:
        for item in splits:
            print(item)
            fw.write(item.page_content+"====================")


#pdf_modify("流光唇釉.pdf")
pdf_modify("智库FAQ.pdf")


