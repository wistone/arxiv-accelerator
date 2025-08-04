"""
pip install pdfminer.six requests
"""
import re
import io
import requests
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from urllib.parse import urlparse

KEYWORDS = (
    r"University|Institute|Laboratory|College|Dept\.|Department|School|"
    r"Center|Centre|Academy|Research|Laboratoire|École|Technische|Universität"
)

def get_first_page_text(pdf_bytes: bytes) -> str:
    """
    只提取 PDF 首页文本
    """
    laparams = LAParams()
    output = io.StringIO()
    extract_text_to_fp(
        io.BytesIO(pdf_bytes),
        output,
        laparams=laparams,
        maxpages=1,    # 只看第一页
        page_numbers=[0],
        codec='utf-8'
    )
    return output.getvalue()

def extract_arxiv_id_from_url(url: str) -> str:
    """
    从arxiv abstract URL中提取arxiv_id
    例如: http://arxiv.org/abs/2507.23785v1 -> 2507.23785v1
    """
    # 清理URL，移除可能的空格
    url = url.strip()
    
    # 使用正则表达式提取arxiv_id
    pattern = r'/abs/([^/\s]+)/?$'
    match = re.search(pattern, url)
    
    if match:
        return match.group(1)
    else:
        raise ValueError(f"无法从URL中提取arxiv_id: {url}")

def guess_affiliations(text: str) -> list[str]:
    """
    粗暴地把含机构关键词的行挑出来。
    真实场景可以把这里换成更复杂的 NLP / LLM 清洗。
    """
    lines = [ln.strip() for ln in text.splitlines()]
    affil_lines = [
        ln for ln in lines
        if re.search(KEYWORDS, ln, flags=re.I)
        and len(ln) < 200             # 过滤掉太长的段落
    ]
    
    # 过滤掉明显不是机构的内容
    exclude_patterns = [
        r"intern\s+at",  # "Intern at ..."
        r"corresponding\s+author",  # "Corresponding authors"
        r"email",  # 包含email的行
        r"@",      # 包含@符号的行
        r"abstract",  # Abstract相关
        r"keywords",  # Keywords相关
    ]
    
    # 去重并简单清洗
    uniq = []
    for ln in affil_lines:
        # 检查是否包含要排除的模式
        should_exclude = any(re.search(pattern, ln, flags=re.I) for pattern in exclude_patterns)
        if should_exclude:
            continue
            
        ln = re.sub(r"\d+|[*†‡]", "", ln)   # 去掉上标号码或符号
        ln = re.sub(r"\s{2,}", " ", ln).strip(",;:- ")
        if len(ln) > 5 and ln not in uniq:
            uniq.append(ln)
    return uniq

def fetch_affiliation(abstract_url: str) -> list[str]:
    """
    从arxiv abstract URL获取论文的机构信息
    """
    # 从abstract URL提取arxiv_id
    arxiv_id = extract_arxiv_id_from_url(abstract_url)
    
    # 构造PDF URL
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    
    print(f"正在从 {pdf_url} 下载PDF...")
    resp = requests.get(pdf_url, timeout=20)
    resp.raise_for_status()
    
    print("正在解析PDF内容...")
    text = get_first_page_text(resp.content)
    
    print("正在提取机构信息...")
    affiliations = guess_affiliations(text)
    
    return affiliations

def test_single_url(url: str):
    """测试单个URL"""
    print(f"\n{'='*60}")
    print(f"测试URL: {url}")
    print(f"{'='*60}")
    
    try:
        affiliations = fetch_affiliation(url)
        arxiv_id = extract_arxiv_id_from_url(url)
        print(f"\n论文 {arxiv_id} 的机构信息:")
        if affiliations:
            for i, affiliation in enumerate(affiliations, 1):
                print(f"  {i}. {affiliation}")
        else:
            print("  未找到机构信息")
            
    except Exception as e:
        print(f"处理URL时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    # 如果有命令行参数，测试单个URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
        test_single_url(url)
    else:
        # 批量测试用例
        test_urls = [
            "https://arxiv.org/abs/2508.00748",
            "https://arxiv.org/abs/2508.00750", 
            "https://arxiv.org/abs/2508.00744"
        ]
        
        print("开始批量测试...")
        for url in test_urls:
            test_single_url(url)
